import streamlit as tf
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import random
import time

# ==============================================================================
# [SECTION 01: APP CONFIGURATION & STYLING]
# ==============================================================================
st.set_page_config(page_title="Clicker Teacher Dashboard", layout="wide", initial_sidebar_state="expanded")

# Inject responsive custom CSS for the dashboard interface cards
st.markdown("""
<style>
    .reportview-container { background: #1e272e; color: #ffffff; }
    .rainbow-card {
        background: linear-gradient(135deg, #ff007f, #7f00ff, #00bfff, #00ff7f);
        background-size: 300% 300%;
        animation: rainbow-animation 6s ease infinite;
        padding: 22px; border-radius: 12px; margin-bottom: 20px; color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3); border: none;
    }
    @keyframes rainbow-animation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [SECTION 02: CORE SYSTEM STATE INITIALIZATION]
# ==============================================================================
if "app_logs" not in st.session_state:
    st.session_state.app_logs = []

def add_log(msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.app_logs.append(f"[{timestamp}] {msg}")

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = "0000"
if "active_assignment" not in st.session_state:
    st.session_state.active_assignment = "default_assignment"

# ==============================================================================
# [SECTION 03: GOOGLE SHEETS CLOUD STORAGE CONNECTOR API]
# ==============================================================================
@st.cache_data(ttl=3)
def fetch_cloud_workbook_data():
    try:
        add_log("📡 Requesting raw binary workbook stream from Google API...")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Load your cloud secrets mapping safely
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Connect to your main sheet
        sheet_id = st.secrets["google_sheets"]["sheet_id"]
        workbook = client.open_by_key(sheet_id)
        
        # Pull raw sheets down to processing frames
        add_log("🔄 Executing data extraction pipeline...")
        responses_sheet = workbook.worksheet("responses").get_all_records()
        roster_sheet = workbook.worksheet("roster").get_all_records()
        answers_sheet = workbook.worksheet("answers").get_all_records()
        
        add_log(f"✅ Download successful! Discovered worksheets: {workbook.worksheets()}")
        return pd.DataFrame(responses_sheet), pd.DataFrame(roster_sheet), pd.DataFrame(answers_sheet), workbook
    except Exception as e:
        add_log(f"❌ Cloud Connection Error: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# Execute safe pipeline read
all_data_df, roster_data, answers_data, raw_workbook = fetch_cloud_workbook_data()

# ==============================================================================
# [SECTION 04: TEACHER INTERFACE SIDEBAR CONTROLS]
# ==============================================================================
st.sidebar.title("🎮 Teacher Mission Control")
st.sidebar.markdown("---")

# Build target tracking layout keys from the answers spreadsheet headers
if not answers_data.empty:
    assignment_options = [col for col in answers_data.columns if col.lower() not in ["question", "answer", "id"]]
else:
    assignment_options = ["default_assignment"]

selected_assignment = st.sidebar.selectbox("📖 Target Tracking Assignment Layout:", assignment_options)
st.session_state.active_assignment = selected_assignment

if st.sidebar.button("🚀 Start New Session", use_container_width=True):
    # Generate a unique 4-digit numeric access string code
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_session_id = new_code
    
    if raw_workbook is not None:
        try:
            # Sync active settings down to the active_session sheet loop channel
            active_ws = raw_workbook.worksheet("active_session")
            active_ws.clear()
            active_ws.append_row(["session_id", "active_assignment"])
            active_ws.append_row([new_code, selected_assignment])
            
            # Write a clean HANDSHAKE ROW directly into responses to anchor the network
            resp_ws = raw_workbook.worksheet("responses")
            timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            resp_ws.append_row([timestamp_str, selected_assignment, new_code, "SERVER", "ROOM_SET", "0", "TRUE"])
            
            add_log(f"🆕 Button Clicked: Starting brand new room session code {new_code}")
            add_log("📡 Broadcasted active session and assignment tracker down to the cloud sheet.")
            st.cache_data.clear()
            time.sleep(0.5)
            st.rerun()
        except Exception as ex:
            add_log(f"❌ Failed to broadcast new room layout variables: {str(ex)}")

st.sidebar.markdown("---")
st.sidebar.metric(label="🔑 Current Classroom Join Code:", value=st.session_state.active_session_id)
st.sidebar.metric(label="📚 Monitored Assessment:", value=st.session_state.active_assignment)

if st.sidebar.button("🔄 Hard Clear Dashboard Cache", use_container_width=True):
    st.cache_data.clear()
    add_log("🧹 Cache wiped manually by instructor dashboard button override.")
    st.rerun()

# ==============================================================================
# [SECTION 05: LIVE HEADCOUNT TRACKING SUMMARY]
# ==============================================================================
st.title("🍎 Classroom Response Matrix Dashboard")

# Determine active question index keys to evaluate classroom scale
if not answers_data.empty and selected_assignment in answers_data.columns:
    active_layout_map = answers_data.set_index("question")[selected_assignment]
    valid_qs = active_layout_map[active_layout_map.astype(str).str.strip() != ""].index.tolist()
    total_expected_questions = len(valid_qs)
else:
    total_expected_questions = 10

# ==============================================================================
# [SECTION 06: DATA PROCESSING & CALCULATION ENGINE]
# ==============================================================================
if all_data_df.empty:
    st.info("Waiting for incoming responses... Submit answers via the connected student remote.")
else:
    # Create a completely reliable working copy with explicit column tracking
    working_df = all_data_df.copy()
    
    # Enforce exact column names based on position to guarantee no mixing up of data fields
    if working_df.shape[1] >= 7:
        working_df.columns = ['date', 'period', 'session_id', 'student_id', 'question', 'answer', 'is_correct'] + list(working_df.columns[7:])
    else:
        working_df.columns = [str(c).strip().lower().replace(" ", "_") for c in working_df.columns]
    
    # Standardize session strings to match flawlessly
    working_df["session_id"] = working_df["session_id"].astype(str).str.strip().apply(lambda x: x.split('.')[0])
    teacher_session_target = str(st.session_state.active_session_id).strip().split('.')[0]
    
    add_log(f"🔎 Filtering dataset. Target room search key is: '{teacher_session_target}'.")
    df = working_df[working_df["session_id"] == teacher_session_target].copy()
    
    # Filter out the server setup rows so they don't look like actual students
    df = df[df["question"].astype(str).str.upper() != "ROOM_SET"]
    
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
                        <div style="font-size:24px; font-weight:bold; margin-bottom:5px;">🥇 {str(student['student_name']).upper()}</div>
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
            matrix_df.style.map(color_pacing_cells),
            use_container_width=True,
            hide_index=True
        )

# ==============================================================================
# [SECTION 09: BACKSTAGE SYSTEM SIMULATION AND TESTING PLATFORM]
# ==============================================================================
st.markdown("---")
with st.expander("🛠️ Teacher Backstage Dev Logs", expanded=False):
    st.caption("Active event monitoring stream:")
    logs_to_show = st.session_state.get("app_logs", [])
    for log_item in reversed(logs_to_show[-15:]):
        st.text(log_item)
