import streamlit as st
import pandas as pd
import numpy as np
import random
import requests
import re
import time
import io
import qrcode
from datetime import datetime

# ==============================================================================
# [SECTION 01: PROJECT CORE INITIALIZATION & LOGS]
# ==============================================================================
# Requested Version Name: app32.py (Sectioned Telemetry Edition)
# Features: Dynamic QR Code sidebar pass + active logging console window.
# Architecture: Segmented into distinct numbered blocks for easy future replacements.
# ==============================================================================

st.set_page_config(page_title="Classroom Clicker Analytics Engine (app32)", layout="wide")

if "telemetry_logs" not in st.session_state:
    st.session_state.telemetry_logs = []

def add_log(message):
    t_stamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.telemetry_logs.append(f"[{t_stamp}] {message}")

# ==============================================================================
# [SECTION 02: CUSTOM STYLE SHEETS & ANIMATIONS]
# ==============================================================================
st.markdown("""
<style>
@keyframes rainbow {
  0% { background-color: #ef233c; }
  14% { background-color: #f77f00; }
  28% { background-color: #fcbf49; }
  42% { background-color: #d62828; }
  57% { background-color: #003049; }
  71% { background-color: #7209b7; }
  85% { background-color: #4cc9f0; }
  100% { background-color: #ef233c; }
}
@keyframes blink {
  0% { opacity: 1; }
  50% { opacity: 0.75; }
  100% { opacity: 1; }
}
.rainbow-card {
    animation: rainbow 3s infinite, blink 1.5s infinite !important;
    border: 3px solid #ffd700 !important;
}
.rainbow-dot {
    animation: rainbow 2s infinite, blink 1.2s infinite !important;
    border: 3px solid gold !important;
}
.matrix-grid-master {
    display: grid; 
    gap: 20px; 
    padding: 30px 20px; 
    background-color: #f0f2f6; 
    border-radius: 12px; 
    min-height: 320px;
    width: 100%;
}
.matrix-grid-column {
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    justify-content: flex-end;
    width: 100%;
}
.dot-stack-vertical {
    display: flex; 
    flex-direction: column-reverse; 
    gap: 8px; 
    align-items: center; 
    margin-bottom: 14px;
}
</style>
""", unsafe_allow_html=True)

def clean_question_to_string(q_val):
    q_str = str(q_val).strip().upper().replace(" ", "")
    numeric_digits = re.findall(r'\d+', q_str)
    if numeric_digits:
        return f"Q{numeric_digits[0]}"
    return q_str if q_str != "NAN" else "Q0"

# ==============================================================================
# [SECTION 03: CLOUD INGESTION PIPELINE (DATA RETRIEVAL)]
# ==============================================================================
@st.cache_data(ttl=1)
def load_all_data_via_direct_bypass(clear_cache=False):
    if clear_cache:
        st.cache_data.clear()
        
    roster_df = pd.DataFrame(columns=["student_id", "student_name"])
    answers_df = pd.DataFrame(columns=["default_assignment"])
    responses_df = pd.DataFrame(columns=["date", "period", "session_id", "student_id", "question", "answer", "is_correct"])

    add_log("🔄 Executing data extraction pipeline...")

    try:
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            add_log("❌ ERROR: Streamlit secrets structure missing 'connections.gsheets' keys.")
            return roster_df, answers_df, responses_df
            
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not sheet_id_match:
            add_log("❌ ERROR: Could not parse regex file ID from spreadsheet URL.")
            return roster_df, answers_df, responses_df
            
        sheet_id = sheet_id_match.group(1)
        xl_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        add_log(f"📡 Requesting raw binary workbook stream from Google API...")
        
        try:
            xl = pd.ExcelFile(xl_url)
            add_log(f"✅ Download successful! Discovered worksheets: {xl.sheet_names}")
        except Exception as sheet_err:
            add_log(f"❌ FETCH CRASH: Download stream broke. Reason: {sheet_err}")
            return roster_df, answers_df, responses_df
        
        # --- PARSING RESPONSES TAB ---
        try:
            target_tab = "responses" if "responses" in xl.sheet_names else xl.sheet_names[0]
            raw_resp = xl.parse(sheet_name=target_tab)
            
            if not raw_resp.empty:
                raw_resp.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_resp.columns]
                
                working_df = pd.DataFrame()
                working_df["date"] = raw_resp["date"] if "date" in raw_resp.columns else raw_resp.iloc[:, 0]
                working_df["period"] = raw_resp["period"] if "period" in raw_resp.columns else raw_resp.iloc[:, 1]
                working_df["session_id"] = raw_resp["session_id"] if "session_id" in raw_resp.columns else raw_resp.iloc[:, 2]
                
                id_col = [c for c in raw_resp.columns if "student" in c or "id" in c]
                id_col = id_col[0] if id_col else raw_resp.columns[3]
                
                raw_ids = raw_resp[id_col]
                processed_ids = [str(v).strip().replace(".0", "") if str(v).strip() != "" and str(v).lower() != "nan" else f"Sim_{i+1}" for i, v in enumerate(raw_ids)]
                
                working_df["student_id"] = processed_ids
                working_df["question"] = raw_resp["question"] if "question" in raw_resp.columns else raw_resp.iloc[:, 4]
                working_df["answer"] = raw_resp["answer"] if "answer" in raw_resp.columns else raw_resp.iloc[:, 5]
                working_df["is_correct"] = raw_resp["is_correct"] if "is_correct" in raw_resp.columns else raw_resp.iloc[:, 6]
                
                responses_df = working_df.copy()
                responses_df["question"] = responses_df["question"].apply(clean_question_to_string)
        except Exception as parse_err:
            add_log(f"⚠️ PARSING ERROR inside responses matrix: {parse_err}")

        # --- PARSING ROSTER TAB ---
        if "roster" in xl.sheet_names:
            try:
                raw_roster = xl.parse(sheet_name="roster")
                id_col, name_col = None, None
                for c in raw_roster.columns:
                    c_clean = str(c).strip().lower().replace("_", "").replace(" ", "")
                    if "id" in c_clean or "code" in c_clean: id_col = c
                    if "first" in c_clean or "name" in c_clean or "student" in c_clean:
                        if c != id_col: name_col = c
                
                if id_col is None: id_col = raw_roster.columns[0]
                if name_col is None: name_col = raw_roster.columns[1] if len(raw_roster.columns) > 1 else raw_roster.columns[0]
                
                roster_df = pd.DataFrame({
                    "student_id": raw_roster[id_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip(),
                    "student_name": raw_roster[name_col].astype(str).str.strip()
                })
            except Exception as roster_err:
                add_log(f"⚠️ Roster parse warning: {roster_err}")

        # --- PARSING ANSWERS TAB ---
        if "answers" in xl.sheet_names:
            try:
                answers_df = xl.parse(sheet_name="answers")
                answers_df.columns = [str(c).strip() for c in answers_df.columns]
                answers_df["QUESTION"] = [f"Q{i+1}" for i in range(len(answers_df))]
            except Exception as ans_err:
                add_log(f"⚠️ Answers parsing warning: {ans_err}")

    except Exception as general_err:
        add_log(f"🚨 FATAL DOWNSTREAM PIPELINE CRASH: {general_err}")

    if not responses_df.empty and not roster_df.empty:
        responses_df = responses_df.merge(roster_df[["student_id", "student_name"]], on="student_id", how="left")
        responses_df["student_name"] = responses_df["student_name"].fillna(responses_df["student_id"].apply(lambda x: f"Student ({x})" if "Sim" not in x else f"Clicker {x.split('_')[1]}"))
    elif not responses_df.empty:
        responses_df["student_name"] = responses_df["student_id"].apply(lambda x: f"Student ({x})" if "Sim" not in x else f"Clicker {x.split('_')[1]}")

    return roster_df, answers_df, responses_df

# Run initial pipeline execution
roster_data, answers_data, all_data_df = load_all_data_via_direct_bypass()
raw_assignment_cols = [col for col in answers_data.columns if col.upper() != "QUESTION"]
available_assignments = raw_assignment_cols if raw_assignment_cols else ["default_assignment"]

if "active_session_id" not in st.session_state: st.session_state.active_session_id = "None"
if "active_period" not in st.session_state: st.session_state.active_period = "None"
if "active_assignment" not
