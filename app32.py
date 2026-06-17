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
# 📋 PROJECT VERSION LOG
# ==============================================================================
# Requested Version Name: app32.py (Unified Core Blueprint - Final Fixed)
# Features: Dynamic QR Code scanning pass + explicit cache clear eviction logic.
# Layout Fix 1: Pinned QR Code generation directly into the sidebar panel.
# Layout Fix 2: Unconditional Phone Simulator layout placement at the bottom
#               so it never disappears or crashes on zero-state initial loads.
# Engine Fix: Explicit robust text-header column mapping to bypass strict positional array bugs.
# Syntax Fix: Standardized button container argument parameters.
# ==============================================================================

st.set_page_config(page_title="Classroom Clicker Analytics Engine (app32)", layout="wide")

# --- CSS FOR HIGH-VISIBILITY TILES, DYNAMIC GRID SPACING & RAINBOW EFFECTS ---
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

@st.cache_data(ttl=1)
def load_all_data_via_direct_bypass(clear_cache=False):
    if clear_cache:
        st.cache_data.clear()
        
    roster_df = pd.DataFrame(columns=["student_id", "student_name"])
    answers_df = pd.DataFrame(columns=["default_assignment"])
    responses_df = pd.DataFrame(columns=["date", "period", "session_id", "student_id", "question", "answer", "is_correct"])

    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not sheet_id_match:
            return roster_df, answers_df, responses_df
            
        sheet_id = sheet_id_match.group(1)
        xl_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        xl = pd.ExcelFile(xl_url)
        
        try:
            raw_resp = xl.parse(sheet_name="responses")
            
            if not raw_resp.empty:
                # Force all column headers to be clean, lowercase strings with no spaces
                raw_resp.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_resp.columns]
                
                working_df = pd.DataFrame()
                working_df["date"] = raw_resp["date"] if "date" in raw_resp.columns else raw_resp.iloc[:, 0]
                working_df["period"] = raw_resp["period"] if "period" in raw_resp.columns else raw_resp.iloc[:, 1]
                working_df["session_id"] = raw_resp["session_id"] if "session_id" in raw_resp.columns else raw_resp.iloc[:, 2]
                
                # Dynamic matching for Student ID text header name variations
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
        except:
            pass

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
            except:
                pass

        if "answers" in xl.sheet_names:
            try:
                answers_df = xl.parse(sheet_name="answers")
                answers_df.columns = [str(c).strip() for c in answers_df.columns]
                answers_df["QUESTION"] = [f"Q{i+1}" for i in range(len(answers_df))]
            except:
                pass

    except Exception as e:
        pass

    if not responses_df.empty and not roster_df.empty:
        responses_df = responses_df.merge(roster_df[["student_id", "student_name"]], on="student_id", how="left")
        responses_df["student_name"] = responses_df["student_name"].fillna(responses_df["student_id"].apply(lambda x: f"Student ({x})" if "Sim" not in x else f"Clicker {x.split('_')[1]}"))
    elif not responses_df.empty:
        responses_df["student_name"] = responses_df["student_id"].apply(lambda x: f"Student ({x})" if "Sim" not in x else f"Clicker {x.split('_')[1]}")

    return roster_df, answers_df, responses_df

roster_data, answers_data, all_data_df = load_all_data_via_direct_bypass()
raw_assignment_cols = [col for col in answers_data.columns if col.upper() != "QUESTION"]
available_assignments = raw_assignment_cols if raw_assignment_cols else ["default_assignment"]

if "active_session_id" not in st.session_state: st.session_state.active_session_id = "None"
if "active_period" not in st.session_state: st.session_state.active_period = "None"
if "active_assignment" not in st.session_state: st.session_state.active_assignment = available_assignments[0]

# --- TEACHER SIDEBAR INTERFACE ---
st.sidebar.title("⚙️ Teacher Control Panel")
period_input = st.sidebar.text_input("Enter Period Number", value="Period 1")
selected_assignment = st.sidebar.selectbox("Select Active Assignment Key", options=available_assignments)

if st.sidebar.button("🚀 Start New Session"):
    st.session_state.active_session_id = str(random.randint(1000, 9999))
    st.session_state.active_period = period_input
    st.session_state.active_assignment = selected_assignment
    load_all_data_via_direct_bypass(clear_cache=True)

st.sidebar.info(f"**Room Status:** Active\n\n**Join Code:** {st.session_state.active_session_id}")

# --- PINNED SIDEBAR QR CODE GENERATION ENGINE ---
if st.session_state.active_session_id != "None":
    st.sidebar.markdown("---")
    st.sidebar.markdown("<div style='text-align: center; font-weight: bold;'>📱 Scan to Join Room</div>", unsafe_allow_html=True)
    
    qr_data = f"Code: {st.session_state.active_session_id}"
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), width=280)

# Generate fallback system tracking parameters
if not answers_data.empty and "QUESTION" in answers_data.columns:
    runtime_key = dict(zip(answers_data["QUESTION"], pd.to_numeric(answers_data[st.session_state.active_assignment], errors='coerce').fillna(0.0)))
    sorted_questions = sorted(list(runtime_key.keys()), key=lambda x: int(re.findall(r'\d+', x)[0])) if runtime_key else ["Q1"]
else:
    runtime_key = {"Q1": 2.0, "Q2": 7.5, "Q3": 100.0, "Q4": 0.25, "Q5": 13.0}
    sorted_questions = ["Q1", "Q2", "Q3", "Q4", "Q5"]
tot_q_count = len(sorted_questions)

# --- CORE VISUAL DASHBOARD MATRIX ---
if st.session_state.active_session_id == "None":
    st.title("🎯 Classroom Metrics Console")
    st.warning("⚠️ Dashboard Offline. Start a session in the sidebar control panel to begin.")
else:
    if all_data_df.empty:
        st.title("🎯 Classroom Metrics Console")
        st.info("Waiting for incoming responses... Submit answers via the bottom-docked simulator tool.")
    else:
        # Robust string normalization block to instantly align data types
        all_data_df["session_id"] = all_data_df["session_id"].astype(str)
        all_data_df["session_id"] = all_data_df["session_id"].str.replace(r'\.0$', '', regex=True).str.strip()
        
        teacher_session_target = str(st.session_state.active_session_id).strip()
        df = all_data_df[all_data_df["session_id"] == teacher_session_target].copy()
        
        if df.empty:
            st.title("🎯 Classroom Metrics Console")
            st.info(f"Session initialized. Join Code: **{st.session_state.active_session_id}**")
        else:
            df["is_correct"] = df["is_correct"].astype(str).str.upper().str.strip() == "TRUE"
            df["student_id"] = df["student_id"].astype(str).str.strip()
            clean_df = df.drop_duplicates(subset=
