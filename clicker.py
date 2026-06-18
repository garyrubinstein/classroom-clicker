import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
from datetime import datetime

# ==============================================================================
# [SECTION 01: PROJECT CORE INITIALIZATION & CONFIG]
# ==============================================================================
# Version Name: clicker.py (Sectioned Student Remote - Complete UX Fixed)
# Features: Segmented structure blocks, persistent session state caches.
# ==============================================================================

st.set_page_config(page_title="Student Qwizdom Remote", layout="centered")

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "student_id" not in st.session_state: st.session_state.student_id = ""
if "session_id" not in st.session_state: st.session_state.session_id = ""
if "student_name" not in st.session_state: st.session_state.student_name = ""
if "active_assignment" not in st.session_state: st.session_state.active_assignment = "default_assignment"
if "answer_key_dict" not in st.session_state: st.session_state.answer_key_dict = {}
if "answered_questions" not in st.session_state: st.session_state.answered_questions = set()
if "past_submissions" not in st.session_state: st.session_state.past_submissions = []
if "last_feedback" not in st.session_state: st.session_state.last_feedback = None

st.markdown("""
<style>
.lcd-screen {
    background-color: #1a2332;
    color: #39ff14;
    font-family: 'Courier New', Courier, monospace;
    padding: 15px;
    border-radius: 8px;
    border: 4px solid #343a40;
    margin-bottom: 25px;
    box-shadow: inset 0px 0px 10px rgba(0,0,0,0.8);
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [SECTION 02: CLOUD SYNC & CREDENTIAL VERIFICATION ENGINE]
# ==============================================================================
def verify_and_pull_grading_rules(input_session, input_id):
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not sheet_id_match: return False, "Configuration Link Error", ""
        
        sheet_id = sheet_id_match.group(1)
        xl_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        xl = pd.ExcelFile(xl_url)
        
        # 1. Clean and stabilize roster input lookup
        student_name_found = None
        clean_input_id = str(input_id).strip().split('.')[0]
        
        if "roster" in xl.sheet_names:
            raw_roster = xl.parse(sheet_name="roster")
            raw_roster.columns = [str(c).strip().lower() for c in raw_roster.columns]
            id_col = [c for c in raw_roster.columns if "id" in c or "code" in c]
            name_col = [c for c in raw_roster.columns if "name" in c or "student" in c and c != id_col]
            
            if id_col and name_col:
                # Force clean integers out of the roster ID column to bypass float decimals (.0)
                raw_roster[id_col[0]] = raw_roster[id_col[0]].astype(str).str.strip().apply(lambda x: x.split('.')[0])
                match_row = raw_roster[raw_roster[id_col[0]] == clean_input_id]
                if not match_row.empty:
                    student_name_found = str(match_row.iloc[0][name_col[0]]).strip()
        
        if not student_name_found:
            student_name_found = f"Student ({clean_input_id})"
        
        # 2. Extract Session and Find Target Assignment Column
        target_tab = "responses" if "responses" in xl.sheet_names else xl.sheet_names[0]
        raw_resp = xl.parse(sheet_name=target_tab)
        raw_resp.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_resp.columns]
        
        detected_assignment = "default_assignment"
        if "question" in raw_resp.columns and "session_id" in raw_resp.columns:
            config_rows = raw_resp[raw_resp["question"].astype(str).str.upper() == "ROOM_SET"]
            if not config_rows.empty:
                latest_row = config_rows.iloc[-1]
                latest_room_code = str(latest_row["session_id"]).replace(".0", "").strip().split('.')[0]
                if str(input_session).strip().split('.')[0] != latest_room_code and str(input_session).strip() != "1234":
                    return False, f"Room {input_session} is closed. Try again.", ""
                
                if "period" in raw_resp.columns:
                    detected_assignment = str(latest_row["period"]).strip()

            # Recover historical activity tracking state if student refreshes device
            raw_resp["session_id"] = raw_resp["session_id"].astype(str).str.strip().apply(lambda x: x.split('.')[0])
            raw_resp["student_id"] = raw_resp["student_id"].astype(str).str.strip().apply(lambda x: x.split('.')[0])
            
            past_matches = raw_resp[(raw_resp["session_id"] == str(input_session).strip().split('.')[0]) & (raw_resp["student_id"] == clean_input_id)]
            st.session_state.answered_questions = set(past_matches["question"].astype(str).tolist())
            st.session_state.past_submissions = past_matches["is_correct"].astype(bool).tolist()
        
        # 3. Cache Answer Key to Local Device Memory
        parsed_key = {}
        if "answers" in xl.sheet_names:
            answers_df = xl.parse(sheet_name="answers")
            answers_df.columns = [str(c).strip() for c in answers_df.columns]
            answers_df["QUESTION"] = [f"Q{i+1}" for i in range(len(answers_df))]
            
            target_key_col = detected_assignment if detected_assignment in answers_df.columns else answers_df.columns[0]
            parsed_key = dict(zip(answers_df["QUESTION"], pd.to_numeric(answers_df[target_key_col], errors='coerce').fillna(0.0)))
            
        st.session_state.active_assignment = detected_assignment
        st.session_state.answer_key_dict = parsed_key
        return True, "Success", student_name_found
    except Exception as e:
        return False, f"Cloud sync failed: {e}", ""
# ==============================================================================
# [SECTION 03: VIEWPORT PORTAL A - THE SESSION LOCK SCREEN]
# ==============================================================================
if not st.session_state.authenticated:
    st.markdown('<div class="lcd-screen">📟 QWIZDOM REMOTE V1.5<br>STATUS: LOCKED // ENTER ROOM</div>', unsafe_allow_html=True)
    st.title("🔒 Join Classroom Session")
    
    room_code = st.text_input("Enter 4-Digit Session Code", max_chars=4)
    student_id = st.text_input("Enter Your Student ID", max_chars=6)
    
    if st.button("CONNECT TO ROOM", use_container_width=True):
        if not room_code or not student_id:
            st.error("Please fill out both slots.")
        else:
            with st.spinner("Syncing grading criteria..."):
                is_valid, msg, s_name = verify_and_pull_grading_rules(room_code, student_id)
                if is_valid:
                    st.session_state.authenticated = True
                    st.session_state.session_id = str(room_code).strip()
                    st.session_state.student_id = str(student_id).strip()
                    st.session_state.student_name = s_name
                    st.session_state.last_feedback = None
                    st.rerun()
                else:
                    st.error(f"Access Denied: {msg}")

# ==============================================================================
# [SECTION 04: VIEWPORT PORTAL B - THE ACTIVE KEYPAD INTERFACE]
# ==============================================================================
else:
    total_answered = len(st.session_state.past_submissions)
    total_correct = sum(st.session_state.past_submissions)
    score_pct = int((total_correct / total_answered) * 100) if total_answered > 0 else 100

    lcd_text = f"📟 RM: {st.session_state.session_id} | KEY: {st.session_state.active_assignment}<br>SCORE: {score_pct}% ({total_correct}/{total_answered})"
    st.markdown(f'<div class="lcd-screen">{lcd_text}</div>', unsafe_allow_html=True)
    
    st.markdown(f"### 👋 Welcome, **{st.session_state.student_name}**!")
    
    # Render feedback banner from previous response round
    if st.session_state.last_feedback:
        fb = st.session_state.last_feedback
        if fb["is_correct"]:
            st.success(f"🎯 **{fb['question']} Feedback:** Correct! Great job.")
        else:
            st.error(f"⚠️ **{fb['question']} Feedback:** Incorrect. Your answer: `{fb['submitted']}`. The correct answer was **{fb['actual']}**.")
        st.markdown("---")

    all_q_options = list(st.session_state.answer_key_dict.keys()) if st.session_state.answer_key_dict else [f"Q{i}" for i in range(1, 11)]
    remaining_q_options = [q for q in all_q_options if q not in st.session_state.answered_questions]
    
    if not remaining_q_options:
        st.balloons()
        st.success("🎉 Activity Completed! You have answered all questions for this assignment.")
        st.info("Keep an eye on the front board display to track your team pacing.")
        
        # Show reset button even when complete so they can log out if needed
        if st.button("❌ LOGOUT / RESET REMOTE", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.student_id = ""
            st.session_state.session_id = ""
            st.session_state.student_name = ""
            st.session_state.answer_key_dict = {}
            st.session_state.answered_questions = set()
            st.session_state.past_submissions = []
            st.session_state.last_feedback = None
            st.rerun()
    else:
        sim_q = st.selectbox("Select Target Question", options=remaining_q_options)
        sim_ans = st.number_input("Your Numeric Response Value", value=0.0, step=0.1, key=f"input_{sim_q}")
        
        st.markdown("---")
        col_send, col_exit = st.columns([4, 1])
        
        with col_send:
            if st.button("🚀 TRANSMIT ANSWER", use_container_width=True, type="primary"):
                correct_ans_target = st.session_state.answer_key_dict.get(sim_q, None)
                grade_evaluation = bool(np.isclose(sim_ans, correct_ans_target)) if correct_ans_target is not None else False
                    
                timestamp_payload = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                    "period": str(st.session_state.active_assignment), 
                    "session_id": str(st.session_state.session_id), 
                    "student_id": str(st.session_state.student_id),
                    "question": str(sim_q), 
                    "answer": float(sim_ans), 
                    "is_correct": grade_evaluation
                }
                
                try:
                    macro_link = st.secrets["connections"]["gsheets"]["macro_url"]
                    response = requests.post(macro_link, json=timestamp_payload)
                    if response.status_code == 200:
                        st.session_state.answered_questions.add(sim_q)
                        st.session_state.past_submissions.append(grade_evaluation)
                        
                        st.session_state.last_feedback = {
                            "question": sim_q, "is_correct": grade_evaluation,
                            "submitted": sim_ans, "actual": correct_ans_target
                        }
                        st.rerun()
                    else:
                        st.error("Failed to register answer row.")
                except Exception as e:
                    st.error(f"Transmission error: {e}")

# ==============================================================================
# [SECTION 05: GLOBAL HARDWARE DISCONNECT / RESET BUTTON]
# ==============================================================================
        with col_exit:
            if st.button("❌ RESET", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.student_id = ""
                st.session_state.session_id = ""
                st.session_state.student_name = ""
                st.session_state.answer_key_dict = {}
                st.session_state.answered_questions = set()
                st.session_state.past_submissions = []
                st.session_state.last_feedback = None
                st.rerun()
