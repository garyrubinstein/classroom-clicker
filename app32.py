import os
import sys

# 🛡️ Force-install required libraries right at startup to prevent environment crashes
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ModuleNotFoundError:
    os.system(f"{sys.executable} -m pip install gspread oauth2client")
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

import streamlit as st
import pandas as pd
import datetime
import random

# Core App Layout Setup
st.set_page_config(page_title="Clicker Dashboard", layout="wide")
st.title("🍎 Classroom Response Dashboard")

# 📡 Robust Cloud Data Grabber
@st.cache_data(ttl=2)
def fetch_cloud_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        workbook = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        
        raw_rows = workbook.worksheet("responses").get_all_values()
        if not raw_rows:
            return pd.DataFrame(), workbook
            
        headers = [str(h).strip().lower() for h in raw_rows[0]]
        data_rows = raw_rows[1:]
        df = pd.DataFrame(data_rows)
        
        if df.shape[1] < len(headers):
            headers = headers[:df.shape[1]]
        elif df.shape[1] > len(headers):
            for i in range(df.shape[1] - len(headers)):
                headers.append(f"col_{i}")
                
        df.columns = headers
        return df, workbook
    except Exception as e:
        st.sidebar.error(f"Cloud syncing paused: {str(e)}")
        return pd.DataFrame(), None

all_data_df, raw_workbook = fetch_cloud_data()

# 🎮 Sidebar Controls
st.sidebar.title("🎮 Room Controls")
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = "3665"

user_code = st.sidebar.text_input("Active Session Join Code:", value=st.session_state.active_session_id)
st.session_state.active_session_id = user_code.strip()

if st.sidebar.button("🧹 Force Refresh Sheet Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Global variables for the debugging panel
debug_total_rows = len(all_data_df) if not all_data_df.empty else 0
debug_matched_rows = 0
debug_columns = list(all_data_df.columns) if not all_data_df.empty else []
debug_unique_sessions = []

# 📊 Render Summary Engine
if all_data_df.empty:
    st.info("Awaiting structural connection to Google Sheets...")
else:
    working_df = all_data_df.copy()
    
    if working_df.shape[1] >= 7:
        # Standardize fallback headers internally just to run math securely
        working_df.columns = ['date', 'period', 'session_id', 'student_id', 'question', 'answer', 'is_correct'] + list(working_df.columns[7:])
        
        # Populate debug list with unique sessions found in raw data
        debug_unique_sessions = working_df['session_id'].astype(str).str.strip().unique().tolist()
        
        target_session = str(st.session_state.active_session_id).strip()
        session_col = working_df['session_id'].astype(str).str.strip()
        
        filtered_df = working_df[session_col.str.contains(target_session, na=False)].copy()
        debug_matched_rows = len(filtered_df)
        
        filtered_df = filtered_df[filtered_df['question'].astype(str).str.upper() != "ROOM_SET"]
        
        if filtered_df.empty:
            st.info(f"Join Code **{st.session_state.active_session_id}** is active. Send a click response from a student remote to display data.")
        else:
            filtered_df['s_id'] = filtered_df['student_id'].astype(str).str.strip()
            filtered_df['q_id'] = filtered_df['question'].astype(str).str.strip()
            filtered_df['correct_bool'] = filtered_df['is_correct'].astype(str).str.upper().str.strip() == "TRUE"
            
            clean_df = filtered_df.drop_duplicates(subset=["s_id", "q_id"], keep="last")
            
            summary = clean_df.groupby("s_id").agg(
                correct_count=("correct_bool", "sum"),
                total_answered=("q_id", "nunique")
            ).reset_index()
            
            st.write(f"### 👥 Active Performance Layout (Session: {st.session_state.active_session_id})")
            
            cols = st.columns(4)
            for idx, row in summary.iterrows():
                with cols[idx % 4]:
                    total = row["total_answered"]
                    correct = row["correct_count"]
                    pct = int((correct / total) * 100) if total > 0 else 0
                    bg_color = "#2ecc71" if pct >= 80 else "#f1c40f" if pct >= 60 else "#e74c3c"
                    
                    st.markdown(f"""
                    <div style="background:{bg_color}; color:white; padding:18px; border-radius:10px; margin-bottom:15px; text-align:center; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                        <div style="font-size:16px; opacity:0.9; font-weight:bold;">STUDENT</div>
                        <div style="font-size:22px; font-weight:bold; margin-bottom:5px;">👤 {row['s_id']}</div>
                        <div style="font-size:36px; font-weight:bold; margin:5px 0;">{pct}%</div>
                        <div style="font-size:13px; opacity:0.9;">🎯 {correct} / {total} Solved</div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.error("The linked Google Sheet does not contain enough data columns.")

# ==============================================================================
# 🛠️ LIVE ON-PAGE DIAGNOSTIC INSPECTOR (UNCOLLAPSED FOR EASY SHOWING)
# ==============================================================================
st.markdown("---")
st.markdown("### 🛠️ Real-Time System Diagnostic Log")
st.caption("Use this area to verify exactly how data is routing from student clickers into the server memory container.")

d_col1, d_col2, d_col3 = st.columns(3)
with d_col1:
    st.metric("Total Rows in Sheets Tab", debug_total_rows)
with d_col2:
    st.metric(f"Rows Matching Code '{st.session_state.active_session_id}'", debug_matched_rows)
with d_col3:
    st.metric("Detected Sheet Columns", len(debug_columns))

st.write("**Raw Detected Spreadsheet Column Layout Headers:**")
st.code(str(debug_columns))

st.write("**All Unique Session Identifiers Active inside Google Sheets right now:**")
st.code(", ".join([f"'{s}'" for s in debug_unique_sessions]) if debug_unique_sessions else "None Found")

if debug_matched_rows > 0:
    st.write("**Preview of Raw Rows Filtered for Current Room:**")
    st.dataframe(filtered_df.head(5), use_container_width=True)
