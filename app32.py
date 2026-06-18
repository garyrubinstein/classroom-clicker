import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import random

# App Setup
st.set_page_config(page_title="Clicker Teacher Dashboard", layout="wide")

# Safe log initializer
if "app_logs" not in st.session_state:
    st.session_state.app_logs = []

def add_log(msg):
    st.session_state.app_logs.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

# Fetch Cloud Data
@st.cache_data(ttl=3)
def fetch_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        workbook = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        
        return (pd.DataFrame(workbook.worksheet("responses").get_all_records()), 
                pd.DataFrame(workbook.worksheet("roster").get_all_records()), 
                workbook)
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), None

all_data_df, roster_data, raw_workbook = fetch_data()

# Sidebar Room Controls
st.sidebar.title("🎮 Room Controls")
if st.sidebar.button("🚀 Start New Session", use_container_width=True):
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_session_id = new_code
    if raw_workbook is not None:
        try:
            raw_workbook.worksheet("active_session").clear()
            raw_workbook.worksheet("active_session").append_row(["session_id", "active_assignment"])
            raw_workbook.worksheet("active_session").append_row([new_code, "quiz_1"])
            
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            raw_workbook.worksheet("responses").append_row([timestamp, "quiz_1", new_code, "SERVER", "ROOM_SET", "0", "TRUE"])
            st.cache_data.clear()
            st.rerun()
        except:
            pass

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = "3665" # Default backup code

st.sidebar.metric("🔑 Join Code:", st.session_state.active_session_id)

# Main Dashboard Engine
st.title("🍎 Classroom Response Dashboard")

if all_data_df.empty:
    st.info("Awaiting cloud data connection...")
else:
    # Ensure standard positional columns to prevent data swapping
    if all_data_df.shape[1] >= 7:
        all_data_df.columns = ['date', 'period', 'session_id', 'student_id', 'question', 'answer', 'is_correct'] + list(all_data_df.columns[7:])
    
    # Filter for target session rows only
    target_session = str(st.session_state.active_session_id).strip()
    df = all_data_df[all_data_df["session_id"].astype(str).str.contains(target_session, na=False)].copy()
    df = df[df["question"].astype(str).str.upper() != "ROOM_SET"]

    if df.empty:
        st.info(f"Join Code: {st.session_state.active_session_id} is active. Waiting for student clicks...")
    else:
        # Standardize true/false tracking indicators
        df["is_correct"] = df["is_correct"].astype(str).str.upper().str.strip() == "TRUE"
        df["student_id"] = df["student_id"].astype(str).str.strip()
        
        # Pull most recent clicks
        clean_df = df.drop_duplicates(subset=["student_id", "question"], keep="last")
        
        # Calculate summary metrics per student
        summary = clean_df.groupby("student_id").agg(
            correct=("is_correct", "sum"),
            total=("question", "nunique")
        ).reset_index()
        
        # Display cosmetic layout cards
        st.write("### 👥 Active Student Summaries")
        cols = st.columns(4)
        for idx, row in summary.iterrows():
            with cols[idx % 4]:
                pct = int((row["correct"] / row["total"]) * 100) if row["total"] > 0 else 0
                bg = "#2ecc71" if pct >= 80 else "#f1c40f" if pct >= 60 else "#e74c3c"
                
                st.markdown(f"""
                <div style="background:{bg}; color:white; padding:15px; border-radius:10px; margin-bottom:15px; text-align:center;">
                    <div style="font-size:18px; font-weight:bold;">Student {row['student_id']}</div>
                    <div style="font-size:28px; font-weight:bold; margin:5px 0;">{pct}%</div>
                    <div style="font-size:12px;">🎯 {row['correct']} / {row['total']} Correct</div>
                </div>
                """, unsafe_allow_html=True)
