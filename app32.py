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
# Requested Version Name: app32.py (Unified Core Blueprint - Telemetry Tracking Edition)
# Features: Dynamic QR Code scanning pass + explicit cache clear eviction logic.
# Layout Fix: Pinned QR Code generation directly into the sidebar panel.
# Telemetry Upgrade: Embedded an active 'Activity Log' that prints timestamps,
#                    row counts, sheet names, and structural parsing checkpoints.
# ==============================================================================

st.set_page_config(page_title="Classroom Clicker Analytics Engine (app32)", layout="wide")

# Initialize persistent debug log array into session state if it doesn't exist
if "telemetry_logs" not in st.session_state:
    st.session_state.telemetry_logs = []

def add_log(message):
    """Appends a timestamped string to the on-screen telemetry engine."""
    t_stamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.telemetry_logs.append(f"[{t_stamp}] {message}")

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
            add_log(f"📊 Reading responses from target tab: '{target_tab}'")
            raw_resp = xl.parse(sheet_name=target_tab)
            add_log(f"📥 Loaded {len(raw_resp)} records from raw sheets row index.")
            
            if not raw_resp.empty:
                orig_cols = list(raw_resp.columns)
                raw_resp.columns = [str(c).strip().lower().replace(" ", "_") for c in raw_resp.columns]
                add_log(f"🏷️ Normalized columns: {orig_cols} -> {list(raw_resp.columns)}")
                
                working_df = pd.DataFrame()
                working_df["date"] = raw_resp["date"] if "date" in raw_resp.columns else raw_resp.iloc[:, 0]
                working_df["period"] = raw_resp["period"] if "period" in raw_resp.columns else raw_resp.iloc[:, 1]
                working_df["session_id"] = raw_resp["session_id"] if "session_id" in raw_resp.columns else raw_resp.iloc[:, 2]
                
                id_col = [c for c in raw_resp.columns if "student" in c or "id" in c]
                id_col = id_col[0] if id_col else raw_resp.columns[3]
                add_log(f"🪪 Identity matching picked column name: '{id_col}'")
                
                raw_ids = raw_resp[id_col]
                processed_ids = [str(v).strip().replace(".0", "") if str(v).strip() != "" and str(v).lower() != "nan" else f"Sim_{i+1}" for i, v in enumerate(raw_ids)]
                
                working_df["student_id"] = processed_ids
                working_df["question"] = raw_resp["question"] if "question" in raw_resp.columns else raw_resp.iloc[:, 4]
                working_df["answer"] = raw_resp["answer"] if "answer" in raw_resp.columns else raw_resp.iloc[:, 5]
                working_df["is_correct"] = raw_resp["is_correct"] if "is_correct" in raw_resp.columns else raw_resp.iloc[:, 6]
                
                responses_df = working_df.copy()
                responses_df["question"] = responses_df["question"].apply(clean_question_to_string)
                add_log("⚙️ Responses structural mapping complete.")
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
                add_log(f"👥 Roster processed successfully. Found {len(roster_df)} active student names.")
            except Exception as roster_err:
                add_log(f"⚠️ Roster parse warning: {roster_err}")

        # --- PARSING ANSWERS TAB ---
        if "answers" in xl.sheet_names:
            try:
                answers_df = xl.parse(sheet_name="answers")
                answers_df.columns = [str(c).strip() for c in answers_df.columns]
                answers_df["QUESTION"] = [f"Q{i+1}" for i in range(len(answers_df))]
                add_log(f"🔑 Answer key map parsed. Detected tracking keys: {list(answers_df.columns)}")
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
    add_log(f"🆕 Button Clicked: Starting brand new room session code {st.session_state.active_session_id}")
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

# --- CORE VISUAL DASHBOARD MATRIX ---
if st.session_state.active_session_id == "None":
    st.title("🎯 Classroom Metrics Console")
    st.warning("⚠️ Dashboard Offline. Start a session in the sidebar control panel to begin.")
else:
    st.title("🎯 Classroom Metrics Console")
    
    # --- 🚨 LIVE TELEMETRY LOG DISPLAY WINDOW 🚨 ---
    with st.expander("📟 RUNTIME SYSTEM ENGINE TELEMETRY LOGS", expanded=True):
        if st.session_state.telemetry_logs:
            # Render logs in a scrollable, terminal-style block
            log_block = "\n".join(st.session_state.telemetry_logs[::-1]) # Show newest on top
            st.code(log_block, language="shell")
            if st.button("🗑️ Clear Log History"):
                st.session_state.telemetry_logs = []
                st.rerun()
        else:
            st.info("System idle. Telemetry engine listening...")

    st.markdown("### 🔍 Live Cloud Data Stream Preview")
    if not all_data_df.empty:
        st.dataframe(all_data_df.head(10))
    else:
        st.info("The spreadsheet object returned from the cloud is currently empty.")

    if all_data_df.empty:
        st.info("Waiting for incoming responses... Submit answers via the bottom-docked simulator tool.")
    else:
        all_data_df["session_id"] = all_data_df["session_id"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        teacher_session_target = str(st.session_state.active_session_id).strip()
        
        # Log out matching arrays
        distinct_sessions = all_data_df["session_id"].unique()
        add_log(f"🔎 Filtering dataset. Active room target is '{teacher_session_target}'. Discovered room IDs present inside sheet data: {list(distinct_sessions)}")
        
        df = all_data_df[all_data_df["session_id"] == teacher_session_target].copy()
        add_log(f"🎯 Row isolation query complete. Extracted rows matching active room target: {len(df)}")
        
        if df.empty:
            st.info(f"Session initialized. Join Code: **{st.session_state.active_session_id}**")
        else:
            df["is_correct"] = df["is_correct"].astype(str).str.upper().str.strip() == "TRUE"
            df["student_id"] = df["student_id"].astype(str).str.strip()
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
            st.markdown(f"## Classroom Track: {st.session_state.active_period} (Code: {st.session_state.active_session_id})")
            
            tab_teacher, tab_student = st.tabs(["👨‍🏫 Teacher View", "👨‍🎓 Student View"])

            with tab_teacher:
                st.header("Teacher Command Center Panels")
                med_progress = int(final_students_df['answered_count'].median())
                
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Class Median Milestone", f"Q{med_progress}")
                col_m2.metric("Target Answer Key", str(st.session_state.active_assignment))
                col_m3.metric("Total Active Responders", len(final_students_df))
                
                st.subheader("📉 1. Student Accuracy Breakdown")
                df_acc_sorted = final_students_df.sort_values(by=["display_pct", "answered_count"], ascending=[True, True])
                records_acc = df_acc_sorted.to_dict('records')
                for i in range(0, len(records_acc), 6):
                    row_cols = st.columns(6)
                    for j, s in enumerate(records_acc[i:i+6]):
                        card_class = s["color_style"]
                        style_inline = s["bg_color"] if card_class == "" else ""
                        border_inline = "border: 4px solid gold;" if s["perfect"] else "border: 1px solid #ddd;"
                        
                        html_tile = f"<div class='{card_class}' style='{style_inline} color:{s['font_color']}; padding:10px; border-radius:6px; text-align:center; {border_inline} margin-bottom:12px;'>"
                        html_tile += f"<div style='font-size:14px; font-weight:bold; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>{s['student_name']}</div>"
                        html_tile += f"<div style='font-size:22px; font-weight:black; margin:4px 0;'>{s['display_pct']}%</div>"
                        html_tile += f"<div style='font-size:11px; opacity:0.9;'>Score: {s['correct_count']}/{s['answered_count']}</div>"
                        html_tile += "</div>"
                        row_cols[j].markdown(html_tile, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("⏱️ 2. Student Pacing Milestone Checklist")
                df_pace_sorted = final_students_df.sort_values(by=["answered_count", "display_pct"], ascending=[True, True])
                records_pace = df_pace_sorted.to_dict('records')
                for i in range(0, len(records_pace), 6):
                    row_cols = st.columns(6)
                    for j, s in enumerate(records_pace[i:i+6]):
                        pace_bg = "background:#2b2d42;" if (s['answered_count'] / tot_q_count) < 0.5 else "background:#5c677d;"
                        border_inline = "border: 4px solid gold;" if s["perfect"] else "border: 1px solid #ddd;"
                        
                        html_tile = f"<div style='{pace_bg} color:white; padding:10px; border-radius:6px; text-align:center; {border_inline} margin-bottom:12px;'>"
                        html_tile += f"<div style='font-size:14px; font-weight:bold; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;'>{s['student_name']}</div>"
                        html_tile += f"<div style='font-size:20px; font-weight:bold; margin:4px 0;'>Q{s['answered_count']} / {tot_q_count}</div>"
                        html_tile += f"<div style='font-size:12px; font-weight:bold; color:gold;'>{s['display_pct']}% Right</div>"
                        html_tile += "</div>"
                        row_cols[j].markdown(html_tile, unsafe_allow_html=True)

            with tab_student:
                st.subheader("Student Progress Display Map")
                grid_style_injection = f"grid-template-columns: repeat({tot_q_count}, 1fr);"
                grid_html = f"<div class='matrix-grid-master' style='{grid_style_injection}'>"
                
                for q_num in range(1, tot_q_count + 1):
                    students_here = [row for _, row in final_students_df.iterrows() if row["answered_count"] == q_num]
                    col_html = "<div class='matrix-grid-column'><div class='dot-stack-vertical'>"
                    
                    if students_here:
                        df_here = pd.DataFrame(students_here).sort_values(by="prio", ascending=True)
                        for _, s in df_here.iterrows():
                            dot_class = "rainbow-dot" if s['perfect'] else ""
                            bg_style = f"background-color: {s['bg_color'].replace('background:', '').replace(';', '')};" if not s['perfect'] else ""
                            col_html += f"<div class='{dot_class}' style='width: 46px; height: 46px; {bg_style} border-radius: 50%; border: 2.5px solid #2b2d42; box-shadow: 2px 3px 6px rgba(0,0,0,0.16);' title='{s['student_name']}'></div>"
                    
                    col_html += "</div>"
                    col_html += f"<div style='border-top: 4px solid #2b2d42; width: 100%; text-align: center; padding-top: 8px; font-weight: black; font-family: sans-serif; font-size: 22px; color: #2b2d42;'>{q_num}</div>"
                    col_html += "</div>"
                    grid_html += col_html
                    
                grid_html += "</div>"
                st.markdown(grid_html, unsafe_allow_html=True)

# --- UNCONDITIONAL EXPANDER OUTSIDE BLOCK ---
st.markdown("<br><br><br><hr>", unsafe_allow_html=True)
with st.expander("📱 BOTTOM DOCK: RUNTIME STUDENT PHONE SIMULATOR", expanded=True):
    col_sim1, col_sim2, col_sim3, col_sim4 = st.columns(4)
    
    with col_sim1:
        student_code_input = st.text_input("Session Code Verification", value="")
    with col_sim2:
        sim_id_input = st.text_input("Simulator Student ID", value="4000", max_chars=4)
    with col_sim3:
        sim_q = st.selectbox("Select Active Question Target", options=sorted_questions)
    with col_sim4:
        sim_ans = st.number_input("Input Raw Answer Value", value=0.0, step=0.1)
        
    if st.button("🚀 Emit Webhook Submission to Google Sheet", use_container_width=True):
        if st.session_state.active_session_id == "None":
            st.error("Submission blocked: No active session running.")
        elif str(student_code_input).strip() != str(st.session_state.active_session_id).strip():
            st.error("Submission blocked: Verification Room Code Mismatch.")
        else:
            target_correct_answer = runtime_key.get(sim_q, None) if 'runtime_key' in locals() else None
            
            if target_correct_answer is not None:
                is_correct = np.isclose(sim_ans, target_correct_answer)
            else:
                backup_key = {"Q1": 2.0, "Q2": 7.5, "Q3": 100.0, "Q4": 0.25, "Q5": 13.0}
                is_correct = np.isclose(sim_ans, backup_key.get(sim_q, 99999.9))
            
            timestamp_payload = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                "period": str(st.session_state.active_assignment), 
                "session_id": str(st.session_state.active_session_id).strip(), 
                "student_id": str(sim_id_input).strip(),
                "question": str(sim_q), 
                "answer": float(sim_ans), 
                "is_correct": bool(is_correct)
            }
            
            add_log(f"📡 Sending Webhook payload out to Google Macro URL...")
            try:
                response = requests.post(st.secrets["connections"]["gsheets"]["macro_url"], json=timestamp_payload)
                add_log(f"📡 HTTP Response code received from Google Web App: {response.status_code}")
                if response.status_code == 200:
                    st.success("Submission sent! Updating live data...")
                    load_all_data_via_direct_bypass(clear_cache=True)
                    time.sleep(0.5)
                    st.rerun()
            except Exception as e:
                add_log(f"❌ WEBHOOK CRASH: Hook post failed. Details: {e}")
                st.error(f"Routing Pipeline Failure: {e}")
