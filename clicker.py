# ==============================================================================
# 🧩 SECTION 1: CORE CONFIGURATION & DECODER LOGIC
# ==============================================================================
import streamlit as st
import pandas as pd
import requests
import datetime
import random
import time

st.set_page_config(page_title="Clicker Response Terminal", layout="centered")
st.title("📟 Student Clicker Terminal")
st.caption("Active Input Portal with Free Response & Custom Session Join")

# Laser-target extraction paths matching the dashboard infrastructure
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

# Roster Mapping Engine
roster_dict = {}
if found_sheet_url:
    try:
        base_url_clk = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        roster_url_clk = f"{base_url_clk.strip()}/gviz/tq?tqx=out:csv&sheet=roster&cb={int(time.time())}"
        roster_df_clk = pd.read_csv(roster_url_clk)
        
        for _, r in roster_df_clk.iterrows():
            raw_id = str(r.iloc[0]).strip()
            if raw_id.endswith('.0'):
                raw_id = raw_id[:-2]
            student_name = str(r.iloc[1]).strip()
            roster_dict[raw_id] = student_name
    except Exception as e:
        st.warning(f"Roster translation offline (Using raw Remote IDs instead). Log: {e}")


# ==============================================================================
# 📡 SECTION 2: LIVE BROADCAST RECEIVER & CUSTOM ROOM JOIN
# ==============================================================================
detected_live_session = ""
if found_sheet_url:
    try:
        base_url_s2 = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        csv_url_s2 = f"{base_url_s2.strip()}/gviz/tq?tqx=out:csv&tq_hi={int(time.time())}"
        sync_df = pd.read_csv(csv_url_s2)
        if not sync_df.empty:
            last_row_code = str(sync_df.iloc[-1, 2]).strip()
            if last_row_code.endswith('.0'):
                last_row_code = last_row_code[:-2]
            if last_row_code and last_row_code != "nan" and last_row_code != "session_id":
                detected_live_session = last_row_code
    except:
        pass

st.markdown("### 🔑 Session Connection")
# Allows student to see the sheet's active code, or override it by typing a fresh one
custom_session_input = st.text_input(
    "Enter Session Room Code to Join:", 
    value=detected_live_session if detected_live_session else "", 
    placeholder="e.g. 3665"
).strip()

final_session_code = custom_session_input[:-2] if custom_session_input.endswith('.0') else custom_session_input
st.caption(f"📡 *Connected Target Session:* **{final_session_code if final_session_code else 'None Assigned'}**")
st.markdown("---")


# ==============================================================================
# 👤 SECTION 3: STUDENT ENTRY FORMS & INPUT VALIDATION
# ==============================================================================
st.markdown("### 📇 Submit Response")

input_id = st.text_input("👤 Enter Remote Clicker ID Number:", placeholder="e.g. 4000").strip()
clean_student_id = input_id[:-2] if input_id.endswith('.0') else input_id

if clean_student_id:
    if clean_student_id in roster_dict:
        st.success(f"👋 Verified Student Account: **{roster_dict[clean_student_id]}**")
    else:
        st.caption(f"ℹ️ Tracking ID parsed as: `{clean_student_id}` (Guest ID)")


# ==============================================================================
# 🎮 SECTION 4: FREE-RESPONSE TEXT INPUT
# ==============================================================================
target_question = st.text_input("❓ Target Question Identifier:", value="Q1").strip()

# Replaced the multiple-choice radio buttons with a free-response text entry line
student_text_response = st.text_input("✏️ Type Your Answer Here:", placeholder="Enter numeric value or short answer text").strip()


# ==============================================================================
# 🚀 SECTION 5: PAYLOAD API DISPATCHER & LOGS
# ==============================================================================
if st.button("📤 Submit Clicker Action", use_container_width=True):
    if not clean_student_id or not target_question or not student_text_response:
        st.error("Please ensure you provide your Clicker ID, Question marker, and your Answer text before transmitting.")
    elif not final_session_code:
        st.error("Cannot dispatch clicker row: You must input or choose a valid Session Room Code to join.")
    elif not found_macro_url:
        st.error("Application configuration missing targeted Google App Script links.")
    else:
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "date": timestamp,
                "period": "student_input",
                "session_id": final_session_code,
                "student_id": clean_student_id,
                "question": target_question,
                "answer": student_text_response,
                "is_correct": "PENDING"  # Setting grading status to PENDING since it is a free response input
            }
            
            clean_url = str(found_macro_url).strip()
            response = requests.post(clean_url, json=payload, timeout=5)
            st.success(f"Response successfully broadcast! Sent answer '{student_text_response}' for student '{roster_dict.get(clean_student_id, clean_student_id)}'.")
        except Exception as e:
            st.error(f"Network error encountered transmitting data packet: {e}")
