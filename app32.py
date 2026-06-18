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
# 👥 SECTION 3: CLEAN TEXT SCOREBOARD ENGINE (DECIMAL & VALUE FIX)
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
        
        processing_logs = []
        processing_logs.append("⚙️ Starting Scoreboard Engine calculations...")

        # 🤝 ROSTER LOOKUP SYSTEM: Explicitly strip decimals from keys
        roster_dict = {}
        try:
            roster_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv&sheet=roster"
            roster_df = pd.read_csv(roster_url)
            for _, r in roster_df.iterrows():
                # Force ID to float, then integer, then string to drop trailing decimals safely
                raw_id = str(r.iloc[0]).strip()
                if raw_id.endswith('.0'):
                    raw_id = raw_id[:-2]
                roster_dict[raw_id] = str(r.iloc[1]).strip()
        except Exception as re:
            processing_logs.append(f"⚠️ Could not pull 'roster' tab directly ({re})")
            try:
                fallback_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv&sheet=answers"
                fb_df = pd.read_csv(fallback_url)
                for _, r in fb_df.iterrows():
                    raw_id = str(r.iloc[0]).strip()
                    if raw_id.endswith('.0'):
                        raw_id = raw_id[:-2]
                    roster_dict[raw_id] = str(r.iloc[1]).strip()
            except Exception as ae:
                processing_logs.append(f"⚠️ Could not pull fallback 'answers' tab names ({ae})")

        processing_logs.append(f"🔑 Cleaned Roster Map inside Memory: {str(roster_dict)}")

        if raw_df.empty:
            st.info("No data found in the spreadsheet yet.")
        else:
            session_col = raw_df.iloc[:, 2].astype(str).str.strip()
            # Handle case where session code comes in as float decimal from sheets
            if session_col.str.endswith('.0').any():
                session_col = session_col.apply(lambda x: x[:-2] if x.endswith('.0') else x)
                
            target_code = str(st.session_state.active_code).strip()
            
            filtered_df = raw_df[session_col == target_code].copy()
            
            if not filtered_df.empty:
                room_set_mask = filtered_df.iloc[:, 4].astype(str).str.upper() == "ROOM_SET"
                filtered_df = filtered_df[~room_set_mask]
            
            if filtered_df.empty:
                st.info(f"No student clicks recorded yet for Session Code **{target_code}**.")
            else:
                # Target columns safely by position and strip any trailing floating decimals
                filtered_df['s_id'] = filtered_df.iloc[:, 3].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith('.0') else x)
                filtered_df['q_id'] = filtered_df.iloc[:, 4].astype(str).str.strip().apply(lambda x: x[:-2] if x.endswith('.0') else x)
                
                raw_correct_strings = filtered_df.iloc[:, 6].astype(str).unique().tolist()
                processing_logs.append(f"👀 Logged strings inside row cells: {raw_correct_strings}")
                
                # Check for absolute truth values in data row cells
                filtered_df['is_true'] = filtered_df.iloc[:, 6].astype(str).str.upper().str.strip().isin(["TRUE", "1", "1.0"])
                
                clean_df = filtered_df.drop_duplicates(subset=["s_id", "q_id"], keep="last")
                
                summary = clean_df.groupby("s_id").agg(
                    correct=("is_true", "sum"),
                    total=("q_id", "nunique")
                ).reset_index()
                
                for _, row in summary.iterrows():
                    student_key = str(row['s_id'])
                    student_display_name = roster_dict.get(student_key, student_key)
                    
                    if student_key not in roster_dict:
                        processing_logs.append(f"❌ Map miss: Looked for Cleaned ID '{student_key}' but failed.")
                    else:
                        processing_logs.append(f"✅ Map hit: Cleaned ID '{student_key}' -> Name '{student_display_name}'")
                        
                    total_answered = int(row["total"])
                    correct_answers = int(row["correct"])
                    
                    pct = int((correct_answers / total_answered) * 100) if total_answered > 0 else 0
                    st.markdown(f"👤 **{student_display_name}** — Accuracy: `{pct}%` ({correct_answers}/{total_answered} correct)")
            
        with st.expander("📝 View Scoreboard Processing Engine Log", expanded=True):
            for log in processing_logs:
                st.text(log)
                    
    except Exception as e:
        st.error(f"Scoreboard Engine hit an execution fault: {e}")


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
