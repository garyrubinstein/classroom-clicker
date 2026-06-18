import streamlit as st
import pandas as pd
import requests
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Simplified Session Broadcaster - Precision Pathing")

# 🎯 Direct Laser-Target Extraction based on your real secrets layout
try:
    found_macro_url = st.secrets["connections"]["gsheets"]["macro_url"]
    found_sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    try:
        # Fallback just in case "connections" gets bypassed
        found_macro_url = st.secrets["gsheets"]["macro_url"]
        found_sheet_url = st.secrets["gsheets"]["spreadsheet"]
    except Exception:
        found_macro_url = None
        found_sheet_url = None

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
            # Strip any trailing whitespace or hidden string formatting artifacts
            clean_url = str(found_macro_url).strip()
            
            response = requests.post(clean_url, json=payload, timeout=5)
            st.success(f"Broadcast sent! Code {new_code} is live on your sheet.")
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
# 🛠️ SYSTEM CONFIGURATION & DATA DEBUG CONSOLE
# ==============================================================================
st.markdown("---")
st.markdown("### 📋 Live Diagnostics & Secrets Inspector")

if st.button("🔄 Refresh Debug Console", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.write("**Isolated Macro URL Target Link:**")
st.code(str(found_macro_url))

st.write("**Isolated Spreadsheet Target Link:**")
st.code(str(found_sheet_url))

if found_sheet_url:
    try:
        base_url = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        csv_url = f"{base_url.strip()}/gviz/tq?tqx=out:csv"
        
        raw_df = pd.read_csv(csv_url)
        st.metric("Total Rows Processed in Spreadsheet Log", len(raw_df))
        
        st.write("**Most Recent 5 Rows sitting in your Sheet right now:**")
        st.dataframe(raw_df.tail(5), use_container_width=True)
    except Exception as e:
        st.caption(f"Awaiting response log streams... ({e})")
