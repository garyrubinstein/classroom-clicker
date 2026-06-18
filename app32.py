# ==============================================================================
# 🧩 SECTION 1: CORE SETUP & SECRETS PARSING
# ==============================================================================
import streamlit as st
import pandas as pd
import requests
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Session Broadcaster & Simple Scoreboard Panel")

# 🎯 Direct Laser-Target Extraction based on your real secrets layout
try:
    found_macro_url = st.secrets["connections"]["gsheets"]["macro_url"]
    found_sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    try:
        found_macro_url = st.secrets["gsheets"]["macro_url"]
        found_sheet_url = st.secrets["gsheets"]["spreadsheet"]
    except Exception:
        found_macro_url = None
        found_sheet_url = None


# ==============================================================================
# 🚀 SECTION 2: SESSION BROADCASTER CONTROLS
# ==============================================================================
# 🛒 Control Interface Selection
selected_key = st.selectbox("📖 Select Assignment Tracker Key:", ["quiz_1", "quiz_2", "practice_set"])

if "active_code" not in st.session_state:
    st.session_state.active_code = "3665"

if st.button("🚀 Broadcast New Session Code", use_container_width=True):
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_code = new_code
    
    if found_macro_url:
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "date": timestamp,
                "period": selected_key,
                "session_id": new_code,
                "student_id": "SERVER",
                "question": "ROOM_SET",
                "answer": "0",
                "is_correct": "TRUE"
            }
            clean_url = str(found_macro_url).strip()
            response = requests.post(clean_url, json=payload, timeout=5)
            st.success(f"Broadcast sent! Code {new_code} is live on your sheet.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Could not broadcast row via API: {e}")
    else:
        st.warning(f"Code updated locally to {new_code}, but your macro_url path could not be found.")

# Broadcast Status Dashboard
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.metric("Active Join Code", st.session_state.active_code)
with c2:
    st.metric("Target Assignment Key", selected_key)


# ==============================================================================
# 👥 SECTION 3: CLEAN TEXT SCOREBOARD ENGINE
# ==============================================================================
st.markdown("---")
st.markdown("### 👥 Active Student Scoreboard")

if not found_sheet_url:
    st.warning("Spreadsheet URL missing from secrets.")
else:
    try:
        base_url = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        csv_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv"
        
        raw_df = pd.read_csv(csv_url)
        
        if raw_df.empty:
            st.info("No data found in the spreadsheet yet.")
        else:
            # Filter rows matching the active session code (Column index 2)
            session_col = raw_df.iloc[:, 2].astype(str).str.strip()
            target_code = str(st.session_state.active_code).strip()
            
            filtered_df = raw_df[session_col == target_code].copy()
            
            # CRITICAL: Strip out the initial server session id line to clean student stats
            filtered_df = filtered_df[filtered_df.iloc[:, 4].astype(str).str.upper() != "ROOM_SET"]
            
            if filtered_df.empty:
                st.info(f"No student clicks recorded yet for Session Code **{target_code}**.")
            else:
                # Target columns by absolute positional indexing
                filtered_df['s_id'] = filtered_df.iloc[:, 3].astype(str).str.strip() # student_id
                filtered_df['q_id'] = filtered_df.iloc[:, 4].astype(str).str.strip() # question
                filtered_df['is_true'] = filtered_df.iloc[:, 6].astype(str).str.upper().str.strip() == "TRUE" # is_correct
                
                # Deduplicate to evaluate only the final remote press submitted per question
                clean_df = filtered_df.drop_duplicates(subset=["s_id", "q_id"], keep="last")
                
                # Math Processing
                summary = clean_df.groupby("s_id").agg(
                    correct=("is_true", "sum"),
                    total=("q_id", "nunique")
                ).reset_index()
                
                # Render Clean Text Displays
                for _, row in summary.iterrows():
                    pct = int((row["correct"] / row["total"]) * 100) if row["total"] > 0 else 0
                    st.markdown(f"👤 **Student {row['s_id']}** — Accuracy: `{pct}%` ({row['correct']}/{row['total']} correct)")
                    
    except Exception as e:
        st.caption(f"Waiting for incoming student click inputs... ({e})")


# ==============================================================================
# 🛠️ SECTION 4: DIAGNOSTICS LOG PANEL
# ==============================================================================
st.markdown("---")
st.markdown("### 📋 Raw Sheet Logger")
if st.button("🔄 Refresh Data Tables", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if found_sheet_url:
    try:
        base_url = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        csv_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv"
        debug_df = pd.read_csv(csv_url)
        st.dataframe(debug_df.tail(5), use_container_width=True)
    except:
        pass
