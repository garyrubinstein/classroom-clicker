import os
import sys

# 1. RUN AUTO-INSTALLER FIRST (Before standard imports look for them)
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ModuleNotFoundError:
    os.system(f"{sys.executable} -m pip install gspread oauth2client")
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

# 2. STANDARD APP IMPORTS
import streamlit as st
import pandas as pd
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Minimalist Session Broadcaster & Live Data Preview")

# 📡 Cloud Workbook Storage Connection
@st.cache_data(ttl=3)
def get_workbook_data():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        workbook = client.open_by_key(st.secrets["google_sheets"]["sheet_id"])
        
        # Pull raw rows to display safely in the debug console
        raw_rows = workbook.worksheet("responses").get_all_values()
        df = pd.DataFrame(raw_rows) if raw_rows else pd.DataFrame()
        return df, workbook
    except Exception as e:
        st.error(f"Cloud Connection Paused: {e}")
        return pd.DataFrame(), None

raw_data_df, workbook = get_workbook_data()

# Pull layout assignment options safely from the answers tab headers
assignment_options = ["quiz_1", "quiz_2", "practice_set"]
if workbook:
    try:
        answers_sheet = workbook.worksheet("answers").get_all_values()
        if answers_sheet:
            headers = [str(h).strip() for h in answers_sheet[0]]
            filtered_options = [h for h in headers if h.lower() not in ["question", "answer", "id", ""]]
            if filtered_options:
                assignment_options = filtered_options
    except:
        pass

# 🛒 Control Interface Selection
selected_key = st.selectbox("📖 Select Assignment Tracker Key:", assignment_options)

if "active_code" not in st.session_state:
    st.session_state.active_code = "----"

if st.button("🚀 Broadcast New Session Code", use_container_width=True):
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_code = new_code
    
    if workbook:
        try:
            # Update the active_session spreadsheet loop
            session_ws = workbook.worksheet("active_session")
            session_ws.clear()
            session_ws.append_row(["session_id", "active_assignment"])
            session_ws.append_row([new_code, selected_key])
            
            # Append network handshake marker to incoming rows
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            responses_ws = workbook.worksheet("responses")
            responses_ws.append_row([timestamp, selected_key, new_code, "SERVER", "ROOM_SET", "0", "TRUE"])
            
            st.success(f"Broadcast successful! Code {new_code} is live.")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Failed to write to Google Sheets: {e}")

# Broadcast Status Dashboard
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    st.metric("Broadcasted Join Code", st.session_state.active_code)
with c2:
    st.metric("Target Assignment Key", selected_key)

# ==============================================================================
# 🛠️ REAL-TIME DATA PREVIEW CONSOLE
# ==============================================================================
st.markdown("---")
st.markdown("### 📋 Live Spreadsheet Console")
st.caption("Verifies raw rows currently recorded in your Google Sheet.")

if st.button("🔄 Refresh Console View", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

if raw_data_df.empty:
    st.warning("No rows found or spreadsheet data is unreadable.")
else:
    st.metric("Total Rows in Spreadsheet Data Log", len(raw_data_df) - 1 if len(raw_data_df) > 0 else 0)
    
    st.write("**Most Recent 10 Rows Appended to Google Sheets:**")
    header_row = raw_data_df.iloc[0]
    last_rows = raw_data_df.tail(10)
    
    preview_df = pd.concat([pd.DataFrame([header_row]), last_rows]).drop_duplicates(keep='last')
    st.dataframe(preview_df, use_container_width=True, hide_index=True)
