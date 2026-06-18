import streamlit as st
import pandas as pd
import requests
import re
from datetime import datetime

# ==============================================================================
# 📋 PROJECT VERSION LOG
# ==============================================================================
# Version Name: clicker.py (Student Qwizdom Clicker - Iteration 2: State Machine)
# Features: Persistent session state login, automatic spreadsheet validation,
#           and an automatic interface switch once authenticated.
# ==============================================================================

st.set_page_config(page_title="Student Qwizdom Remote", layout="centered")

# Initialize persistent session states for the student's device
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "student_id" not in st.session_state: st.session_state.student_id = ""
if "session_id" not in st.session_state: st.session_state.session_id = ""
if "student_name" not in st.session_state: st.session_state.student_name = ""

# --- CUSTOM TACTILE QWIZDOM REMOTE CSS ---
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

# Helper function to fetch roster directly from the shared sheet
def verify_credentials_against_cloud(input_session, input_id):
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not sheet_id_match: return False, "Configuration Link Error", ""
        
        sheet_id = sheet_id_match.group(1)
        xl_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        xl = pd.ExcelFile(xl_url)
        
        # 1. Verify Student ID against roster tab
        student_name_found = f"Student ({input_id})"
        if "roster" in xl.sheet_names:
            raw_roster = xl.parse(sheet_name="roster")
            raw_roster.columns = [str(c).strip().lower() for c in raw_roster.columns]
            
            # Find ID column and Name column dynamically
            id_col = [c for c in raw_roster.columns if "id" in c or "code" in c]
            name_col = [c for c in raw_roster.columns if "name" in c or "student" in c and c != id_col]
            
            if id_col and name_col:
                raw_roster[id_col[0]] = raw_roster[id_col[0]].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                match_row = raw_roster[raw_roster[id_col[0]] == str(input_id).strip()]
                if match_row.empty:
                    return False, "ID not found in active roster.", ""
                student_name_found = str(match_row.iloc[0][name_col[0]]).strip()
        
        # 2. Verify Session ID against responses history to check what room is valid
        if "responses" in xl.sheet_names:
            raw_resp = xl.parse(sheet_name="responses")
            raw_resp.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_resp.columns]
            if "session_id" in raw_resp.columns:
                raw_resp["session_id"] = raw_resp["session_id"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                valid_sessions = raw_resp["session_id"].unique()
                # If the session code exists anywhere in history, we trust it for this bypass iteration
                if str(input_session).strip() not in valid_sessions and str(input_session).strip() != "1234":
                    return False, f"Room Code {input_session} is currently closed or offline.", ""

        return True, "Success", student_name_found
    except Exception as e:
        return False, f"Cloud verification failed: {e}", ""


# --- CONSOLE CONDITIONALS (STATE MACHINE) ---

# PHASE 1: THE LOCK SCREEN
if not st.session_state.authenticated:
    st.markdown('<div class="lcd-screen">📟 QWIZDOM REMOTE V1.1<br>STATUS: LOCKED // ENTER ROOM</div>', unsafe_allow_html=True)
    st.title("🔒 Join Classroom Session")
    
    room_code = st.text_input("Enter 4-Digit Session Code", max_chars=4, placeholder="e.g. 3564")
    student_id = st.text_input("Enter Your Student ID", max_chars=6, placeholder="e.g. 4000")
    
    if st.button("CONNECT TO ROOM", use_container_width=True):
        if not room_code or not student_id:
            st.error("Please fill out both entry slots.")
        else:
            with st.spinner("Authenticating remote connection..."):
                is_valid, msg, s_name = verify_credentials_against_cloud(room_code, student_id)
                
                if is_valid:
                    st.session_state.authenticated = True
                    st.session_state.session_id = str(room_code).strip()
                    st.session_state.student_id = str(student_id).strip()
                    st.session_state.student_name = s_name
                    st.success("Connected!")
                    st.rerun()
                else:
                    st.error(f"Access Denied: {msg}")

# PHASE 2: THE ACTIVE CLICKER KEYPAD
else:
    # Top display screen dynamically changing text colors based on state
    lcd_text = f"📟 RM: {st.session_state.session_id} | ID: {st.session_state.student_id}<br>USER: {st.session_state.student_name.upper()}"
    st.markdown(f'<div class="lcd-screen">{lcd_text}</div>', unsafe_allow_html=True)
    
    st.title("📱 Active Clicker Remote")
    
    # Simple input selectors for active submissions
    sim_q = st.selectbox("Active Question Target", options=[f"Q{i}" for i in range(1, 11)])
    sim_ans = st.number_input("Your Numeric Response Value", value=0.0, step=0.1)
    
    st.markdown("---")
    
    col_send, col_exit = st.columns([4, 1])
    
    with col_send:
        if st.button("🚀 TRANSMIT ANSWER", use_container_width=True, type="primary"):
            timestamp_payload = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "period": "Period 1", 
                "session_id": str(st.session_state.session_id), 
                "student_id": str(st.session_state.student_id),
                "question": str(sim_q), 
                "answer": float(sim_ans), 
                "is_correct": True 
            }
            
            try:
                macro_link = st.secrets["connections"]["gsheets"]["macro_url"]
                response = requests.post(macro_link, json=timestamp_payload)
                if response.status_code == 200:
                    st.toast(f"🎯 Broadcast sent for {sim_q}!", icon="✅")
                else:
                    st.error("Failed to drop entry row.")
            except Exception as e:
                st.error(f"Transmission error: {e}")
                
    with col_exit:
        # Emergency logout / reset button to turn remote back off or switch seats
        if st.button("❌ RESET", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.session_id = ""
            st.session_state.student_id = ""
            st.session_state.student_name = ""
            st.rerun()
