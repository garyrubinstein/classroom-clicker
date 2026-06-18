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
# 🚀 SECTION 2: SESSION BROADCASTER CONTROLS (SYNCHRONIZED DISPLAY)
# ==============================================================================
# 🛒 Control Interface Selection
selected_key = st.selectbox("📖 Select Assignment Tracker Key:", ["quiz_1", "quiz_2", "practice_set"])

if "active_code" not in st.session_state:
    st.session_state.active_code = "3665"

# 🎯 Sync Display Check: Read what code is physically recorded at the bottom of the sheet right now
live_display_code = st.session_state.active_code
if found_sheet_url:
    try:
        import time
        base_url_s2 = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        csv_url_s2 = f"{base_url_s2.strip()}/gviz/tq?tqx=out:csv&tq_hi={int(time.time())}"
        sync_df = pd.read_csv(csv_url_s2)
        if not sync_df.empty:
            last_row_code = str(sync_df.iloc[-1, 2]).strip()
            if last_row_code.endswith('.0'):
                last_row_code = last_row_code[:-2]
            if last_row_code and last_row_code != "nan" and last_row_code != "session_id":
                live_display_code = last_row_code
    except:
        pass

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

# Broadcast Status Dashboard (Now reading directly from the Sheet's active line)
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.metric("Active Join Code", live_display_code)
with c2:
    st.metric("Target Assignment Key", selected_key)




# ==============================================================================
# 👥 SECTION 3: CLEAN TEXT SCOREBOARD ENGINE (STABLE LAYOUT VERSION)
# ==============================================================================
st.markdown("---")
st.markdown("### 👥 Active Student Scoreboard")

# Create stable UI placeholders that stay on screen even when the background is idle
status_placeholder = st.empty()
info_placeholder = st.empty()
matrix_placeholder = st.empty()
scoreboard_placeholder = st.empty()
log_placeholder = st.empty()

# Initialize persistent memory storage for tracking data changes across loops
if "last_processed_row_count" not in st.session_state:
    st.session_state.last_processed_row_count = 0
if "cached_summary_data" not in st.session_state:
    st.session_state.cached_summary_data = None
if "cached_matrix_data" not in st.session_state:
    st.session_state.cached_matrix_data = None
if "cached_target_code" not in st.session_state:
    st.session_state.cached_target_code = "None"
if "cached_logs" not in st.session_state:
    st.session_state.cached_logs = []

# 🔄 Stable Background Fragment: Keeps running, updates memory, and maintains layout
@st.fragment(run_every=5)
def refresh_scoreboard_panel():
    if not found_sheet_url:
        st.warning("Spreadsheet URL missing from secrets.")
        return
        
    try:
        base_url = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        
        import time
        cache_buster = int(time.time())
        csv_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv&tq_hi={cache_buster}"
        
        raw_df = pd.read_csv(csv_url)
        current_row_count = len(raw_df)
        current_time_str = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Checking if data has actually changed
        if current_row_count == st.session_state.last_processed_row_count and st.session_state.last_processed_row_count > 0:
            status_placeholder.caption(f"💤 **Dashboard Idling:** Checked at `{current_time_str}` — No new clicker rows detected in database.")
        else:
            # New data found! Update state tracking variables
            st.session_state.last_processed_row_count = current_row_count
            
            forensics_logs = []
            forensics_logs.append("🔍 --- SHEET CHANGE DETECTED: PROCESSING RUN ---")
            forensics_logs.append(f"📊 New Database Row Count: {current_row_count}")

            # Roster Name Mapping Engine
            roster_dict = {}
            try:
                roster_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv&sheet=roster&cb={cache_buster}"
                roster_df = pd.read_csv(roster_url)
                for _, r in roster_df.iterrows():
                    raw_id = str(r.iloc[0]).strip()
                    if raw_id.endswith('.0'): raw_id = raw_id[:-2]
                    roster_dict[raw_id] = str(r.iloc[1]).strip()
            except:
                try:
                    fallback_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv&sheet=answers&cb={cache_buster}"
                    fb_df = pd.read_csv(fallback_url)
                    for _, r in fb_df.iterrows():
                        raw_id = str(r.iloc[0]).strip()
                        if raw_id.endswith('.0'): raw_id = raw_id[:-2]
                        roster_dict[raw_id] = str(r.iloc[1]).strip()
                except:
                    pass

            if raw_df.empty:
                st.session_state.cached_target_code = "None"
                st.session_state.cached_matrix_data = None
                st.session_state.cached_summary_data = None
            else:
                # Auto-Detect Active Session Code
                last_row_session = str(raw_df.iloc[-1, 2]).strip()
                if last_row_session.endswith('.0'):
                    last_row_session = last_row_session[:-2]
                    
                if last_row_session and last_row_session != "nan" and last_row_session != "session_id":
                    target_code = last_row_session
                else:
                    target_code = str(st.session_state.active_code).strip()
                
                st.session_state.cached_target_code = target_code
                status_placeholder.caption(f"⚡ **Live Dashboard Status:** Table recalculated at `{current_time_str}` (New data loaded!)")

                # Data Filtering
                session_col = raw_df.iloc[:, 2].astype(str).str.strip()
                if session_col.str.endswith('.0').any():
                    session_col = session_col.apply(lambda x: x[:-2] if x.endswith('.0') else x)
                    
                filtered_df = raw_df[session_col == target_code].copy()
                
                if not filtered_df.empty:
                    room_set_mask = filtered_df.iloc[:, 4].astype(str).str.upper() == "ROOM_SET"
                    filtered_df = filtered_df[~room_set_mask]
                
                if filtered_df.empty:
                    st.session_state.cached_matrix_data = "EMPTY"
                    st.session_state.cached_summary_data = None
                else:
                    filtered_df['s_id'] = filtered_df.iloc[:, 3].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith('.0') else x)
                    filtered_df['q_id'] = filtered_df.iloc[:, 4].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith('.0') else x)
                    filtered_df['is_true'] = filtered_df.iloc[:, 6].astype(str).str.upper().str.strip().isin(["TRUE", "1", "1.0"])
                    
                    clean_df = filtered_df.drop_duplicates(subset=["s_id", "q_id"], keep="last")
                    
                    # Store diagnostic grid data frame in cache memory
                    st.session_state.cached_matrix_data = pd.DataFrame({
                        "Student ID": clean_df['s_id'],
                        "Name": clean_df['s_id'].map(roster_dict),
                        "Question": clean_df['q_id'],
                        "Answer Code": clean_df.iloc[:, 5].astype(str),
                        "Sheet Status": clean_df.iloc[:, 6].astype(str),
                        "Dashboard Calculation": clean_df['is_true'].map({True: "✅ CORRECT", False: "❌ WRONG"})
                    })

                    # Calculate and store aggregated student metric summaries
                    summary = clean_df.groupby("s_id").agg(correct=("is_true", "sum"), total=("q_id", "nunique")).reset_index()
                    summary_list = []
                    for _, row in summary.iterrows():
                        student_key = str(row['s_id'])
                        student_display_name = roster_dict.get(student_key, student_key)
                        total_answered = int(row["total"])
                        correct_answers = int(row["correct"])
                        pct = int((correct_answers / total_answered) * 100) if total_answered > 0 else 0
                        summary_list.append((student_display_name, pct, correct_answers, total_answered))
                    
                    st.session_state.cached_summary_data = summary_list
            
            st.session_state.cached_logs = forensics_logs

        # ==============================================================================
        # 🏛️ RENDERING ENGINE (Runs EVERY pass using values safely kept in memory)
        # ==============================================================================
        info_placeholder.info(f"📊 Displaying Live Statistics for Session Code: **{st.session_state.cached_target_code}**")
        
        # Redraw Response Matrix Window
        if isinstance(st.session_state.cached_matrix_data, pd.DataFrame):
            with matrix_placeholder.container():
                st.write("#### 🔍 Live Response Matrix")
                st.dataframe(st.session_state.cached_matrix_data, use_container_width=True)
                st.markdown("---")
        elif st.session_state.cached_matrix_data == "EMPTY":
            matrix_placeholder.warning(f"No student clicks recorded yet for Session Code **{st.session_state.cached_target_code}**.")
        else:
            matrix_placeholder.info("Awaiting structural incoming database streaming elements...")

        # Redraw Student


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
