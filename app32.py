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
if "active_assignment" not in st.session_state: st.session_state.active_assignment = available_assignments[0]

# ==============================================================================
# [SECTION 04: TEACHER CONTROL PANEL & SIDEBAR ROOM BROADCAST]
# ==============================================================================
st.sidebar.title("⚙️ Teacher Control Panel")
period_input = st.sidebar.text_input("Enter Period Number", value="Period 1")
selected_assignment = st.sidebar.selectbox("Select Active Assignment Key", options=available_assignments)

if st.sidebar.button("🚀 Start New Session"):
    st.session_state.active_session_id = str(random.randint(1000, 9999))
    st.session_state.active_period = period_input
    st.session_state.active_assignment = selected_assignment
    add_log(f"🆕 Button Clicked: Starting brand new room session code {st.session_state.active_session_id}")
    
    # Send a comprehensive configuration packet so the student app can pull the active grading rules
    try:
        config_payload = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "period": str(st.session_state.active_assignment), # Sends the specific tracked assignment key name
            "session_id": str(st.session_state.active_session_id),
            "student_id": "SERVER",
            "question": "ROOM_SET",
            "answer": 0.0,
            "is_correct": True
        }
        requests.post(st.secrets["connections"]["gsheets"]["macro_url"], json=config_payload)
        add_log(f"📡 Broadcasted active session {st.session_state.active_session_id} and assignment tracker down to the cloud sheet.")
    except Exception as e:
        add_log(f"⚠️ Failed to broadcast active session room configuration: {e}")
        
    load_all_data_via_direct_bypass(clear_cache=True)

st.sidebar.info(f"**Room Status:** Active\n\n**Join Code:** {st.session_state.active_session_id}")

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

if not answers_data.empty and "QUESTION" in answers_data.columns:
    runtime_key = dict(zip(answers_data["QUESTION"], pd.to_numeric(answers_data[st.session_state.active_assignment], errors='coerce').fillna(0.0)))
    sorted_questions = sorted(list(runtime_key.keys()), key=lambda x: int(re.findall(r'\d+', x)[0])) if runtime_key else ["Q1"]
else:
    runtime_key = {"Q1": 2.0, "Q2": 7.5, "Q3": 100.0, "Q4": 0.25, "Q5": 13.0}
    sorted_questions = ["Q1", "Q2", "Q3", "Q4", "Q5"]
tot_q_count = len(sorted_questions)
# ==============================================================================
# [SECTION 05: SYSTEM LOGS ENGINE PANEL (EXPANDER)]
# ==============================================================================
if st.session_state.active_session_id == "None":
    st.title("🎯 Classroom Metrics Console")
    st.warning("⚠️ Dashboard Offline. Start a session in the sidebar control panel to begin.")
else:
    st.title("🎯 Classroom Metrics Console")
    
    with st.expander("📟 RUNTIME SYSTEM ENGINE TELEMETRY LOGS", expanded=True):
        if st.session_state.telemetry_logs:
            log_block = "\n".join(st.session_state.telemetry_logs[::-1])
            st.code(log_block, language="shell")
            if st.button("🗑️ Clear Log History"):
                st.session_state.telemetry_logs = []
                st.rerun()
        else:
            st.info("System idle. Telemetry engine listening...")

 # ==============================================================================
    # [SECTION 06: DATA PROCESSING & CALCULATION ENGINE]
    # ==============================================================================
    if all_data_df.empty:
        st.info("Waiting for incoming responses... Submit answers via the connected student remote.")
    else:
        # Standardize session strings to match flawlessly
        all_data_df["session_id"] = all_data_df["session_id"].astype(str).str.strip().apply(lambda x: x.split('.')[0])
        teacher_session_target = str(st.session_state.active_session_id).strip().split('.')[0]
        
        add_log(f"🔎 Filtering dataset. Target room search key is: '{teacher_session_target}'.")
        df = all_data_df[all_data_df["session_id"] == teacher_session_target].copy()
        
        if df.empty:
            st.info(f"Session initialized. Awaiting student logins... Join Code: **{st.session_state.active_session_id}**")
        else:
            # Clean up true/false strings into real booleans
            df["is_correct"] = df["is_correct"].astype(str).str.upper().str.strip() == "TRUE"
            df["student_id"] = df["student_id"].astype(str).str.strip().apply(lambda x: x.split('.')[0])
            
            # Map student names out of the roster sheet tab dynamically
            if "student_name" not in df.columns and not roster_data.empty:
                roster_lookup = roster_data.copy()
                roster_lookup.columns = [str(c).strip().lower() for c in roster_lookup.columns]
                r_id = [c for c in roster_lookup.columns if "id" in c or "code" in c]
                r_nm = [c for c in roster_lookup.columns if "name" in c or "student" in c and c != r_id]
                if r_id and r_nm:
                    roster_lookup[r_id[0]] = roster_lookup[r_id[0]].astype(str).str.strip().apply(lambda x: x.split('.')[0])
                    name_map = dict(zip(roster_lookup[r_id[0]], roster_lookup[r_nm[0]]))
                    df["student_name"] = df["student_id"].map(name_map).fillna(df["student_id"])
            elif "student_name" not in df.columns:
                df["student_name"] = df["student_id"]

            # Auto-build the question sequence anchors so the table doesn't break
            raw_questions = df["question"].unique().tolist()
            sorted_questions = sorted([q for q in raw_questions if q.startswith('Q')], key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
            if not sorted_questions: sorted_questions = [f"Q{i}" for i in range(1, 11)]

            # Drop duplicates to lock on the most recent submission per question
            clean_df = df.drop_duplicates(subset=["student_id", "question"], keep="last")
            
            student_aggregates = clean_df.groupby(["student_id", "student_name"]).agg(
                correct_count=("is_correct", "sum"),
                answered_count=("question", "nunique")
            ).reset_index()
            
            student_aggregates["accuracy_pct"] = (student_aggregates["correct_count"] / student_aggregates["answered_count"]).fillna(0.0)
            student_aggregates["display_pct"] = (student_aggregates["accuracy_pct"] * 100).astype(int)
            
            processed_records = []
            for _, r in student_aggregates.iterrows():
                is_perfect = (r["display_pct"] == 100)
                if is_perfect:
                    color_style = "rainbow-card"
                    bg_color = ""
                    font_color = "white"
                    prio = 2
                else:
                    prio = 1 if r["display_pct"] >= 90 else 0 if r["display_pct"] >= 70 else -1
                    font_color = "white" if r["display_pct"] >= 90 or r["display_pct"] < 70 else "black"
                    bg_color = "background:#2ecc71;" if r["display_pct"] >= 90 else "background:#f1c40f;" if r["display_pct"] >= 70 else "background:#e74c3c;"
                    color_style = ""

                processed_records.append({
                    "student_id": r["student_id"], "student_name": r["student_name"],
                    "correct_count": int(r["correct_count"]), "answered_count": int(r["answered_count"]),
                    "display_pct": r["display_pct"], "color_style": color_style, "bg_color": bg_color,
                    "font_color": font_color, "prio": prio, "perfect": is_perfect
                })
            
            final_students_df = pd.DataFrame(processed_records)
            st.markdown(f"## Classroom Track: {st.session_state.active_assignment} (Code: {st.session_state.active_session_id})")

            # ==============================================================================
            # [SECTION 07: MAIN CLASSROOM METRICS GRID VISUALIZATION]
            # ==============================================================================
            cols = st.columns(4)
            for idx, student in final_students_df.sort_values(by=["perfect", "prio", "student_name"], ascending=[False, False, True]).reset_index().iterrows():
                with cols[idx % 4]:
                    if student["color_style"] == "rainbow-card":
                        st.markdown(f"""
                        <div class="rainbow-card">
                            <div style="font-size:24px; font-weight:bold; margin-bottom:5px;">🥇 {student['student_name'].upper()}</div>
                            <div style="font-size:14px; opacity:0.9;">STUDENT ID: {student['student_id']}</div>
                            <hr style="margin:10px 0; border-color:rgba(255,255,255,0.3);">
                            <div style="font-size:36px; font-weight:bold; text-align:center; margin:10px 0;">{student['display_pct']}%</div>
                            <div style="font-size:14px; text-align:center; opacity:0.9;">🎯 {student['correct_count']} / {student['answered_count']} Solved</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="{student['bg_color']} color:{student['font_color']}; padding:20px; border-radius:12px; margin-bottom:20px; box-shadow:0 4px 6px rgba(0,0,0,0.1); border:1px solid rgba(255,255,255,0.1);">
                            <div style="font-size:20px; font-weight:bold; margin-bottom:5px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">👤 {student['student_name']}</div>
                            <div style="font-size:12px; opacity:0.8;">ID: {student['student_id']}</div>
                            <hr style="margin:10px 0; border-color:rgba(255,255,255,0.2);">
                            <div style="font-size:32px; font-weight:bold; text-align:center; margin:5px 0;">{student['display_pct']}%</div>
                            <div style="font-size:13px; text-align:center; opacity:0.8;">📈 {student['correct_count']} / {student['answered_count']} Correct</div>
                        </div>
                        """, unsafe_allow_html=True)

            # ==============================================================================
            # [SECTION 08: DETAILED CLASSROOM PACING DOT-MATRIX COMPONENT]
            # ==============================================================================
            st.markdown("---")
            st.markdown("### 📊 Live Student Question Progress Map")
            
            matrix_data = []
            for s_id in final_students_df["student_id"].unique():
                s_name = final_students_df[final_students_df["student_id"] == s_id]["student_name"].values[0]
                row_cells = {"Student": s_name}
                
                for q in sorted_questions:
                    match = clean_df[(clean_df["student_id"] == s_id) & (clean_df["question"] == q)]
                    if match.empty:
                        row_cells[q] = "⚫ Unanswered"
                    else:
                        row_cells[q] = "🟢 Correct" if match.iloc[0]["is_correct"] else "🔴 Incorrect"
                matrix_data.append(row_cells)
            
            matrix_df = pd.DataFrame(matrix_data)
            
            def color_pacing_cells(val):
                if val == "🟢 Correct": return "background-color: #2ecc71; color: white; font-weight: bold; text-align: center;"
                if val == "🔴 Incorrect": return "background-color: #e74c3c; color: white; font-weight: bold; text-align: center;"
                if val == "⚫ Unanswered": return "background-color: #34495e; color: #7f8c8d; text-align: center;"
                return "font-weight: bold; background-color: #2c3e50; color: #ecf0f1;"

            st.dataframe(
                matrix_df.style.applymap(color_pacing_cells),
                use_container_width=True,
                hide_index=True
            )
