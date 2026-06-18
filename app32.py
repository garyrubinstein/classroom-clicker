import streamlit as st
import pandas as pd
import requests
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Simplified Session Broadcaster (Web-Safe)")

# 🔑 Fetch your configuration secrets safely
try:
    # Most original setups use an Apps Script macro URL to append rows without gspread
    macro_url = st.secrets["google_sheets"].get("macro_url") or st.secrets.get("macro_url")
    sheet_url = st.secrets["google_sheets"].get("public_url")
except:
    macro_url = None
    sheet_url = None

# 🛒 Control Interface Selection
selected_key = st.selectbox("📖 Select Assignment Tracker Key:", ["quiz_1", "quiz_2", "practice_set"])

if "active_code" not in st.session_state:
    st.session_state.active_code = "3665"

if st.button("🚀 Broadcast New Session Code", use_container_width=True):
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_code = new_code
    
    # If your setup uses a Web App Macro URL to write rows, we trigger it here:
    if macro_url:
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Package the exact data row your clicker app expects to find
            payload = {
                "date": timestamp,
                "period": selected_key,
                "session_id": new_code,
                "student_id": "SERVER",
                "question": "ROOM_SET",
                "answer": "0",
                "is_correct": "TRUE"
            }
            # Fire the network request directly to the Google Sheet backend
            response = requests.post(macro_url, json=payload, timeout=5)
            st.success(f"Broadcast sent! Code {new_code} is live.")
        except Exception as e:
            st.error(f"Could not broadcast row via API: {e}")
    else:
        # Local fallback if macro_url isn't configured in secrets yet
        st.warning(f"Code updated locally to {new_code}, but 'macro_url' was not found in your Streamlit secrets to write it to the sheet.")

# Broadcast Status Dashboard
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.metric("Active Join Code", st.session_state.active_code)
with c2:
    st.metric("Target Assignment Key", selected_key)

# ==============================================================================
# 📋 RAW DATA PREVIEW (CRASH-PROOF)
# ==============================================================================
st.markdown("---")
st.markdown("### 📋 Live Data Preview")

if not sheet_url:
    st.caption("Add your Google Sheets public CSV URL to secrets to preview incoming clicks.")
else:
    if st.button("🔄 Refresh Data Table", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    try:
        csv_url = sheet_url.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv")
        raw_df = pd.read_csv(csv_url)
        st.metric("Total Rows Found in Sheet", len(raw_df))
        st.dataframe(raw_df.tail(5), use_container_width=True)
    except Exception as e:
        st.caption(f"Awaiting new responses... ({e})")
