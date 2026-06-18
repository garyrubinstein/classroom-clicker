import streamlit as st
import pandas as pd
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Simplified Session Broadcaster")

# 📡 Read the sheet URL from your existing Secrets file
try:
    sheet_url = st.secrets["google_sheets"]["public_url"]
except:
    # Fallback if secrets are named differently
    sheet_url = None

# 🛒 Control Interface Selection
selected_key = st.selectbox("📖 Select Assignment Tracker Key:", ["quiz_1", "quiz_2", "practice_set"])

if "active_code" not in st.session_state:
    st.session_state.active_code = "3665"

if st.button("🚀 Set New Session Code", use_container_width=True):
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_code = new_code
    st.success(f"Session code updated locally to {new_code}!")

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
    st.warning("To view live data, ensure your public Google Sheets CSV URL is added to your Streamlit Secrets.")
else:
    if st.button("🔄 Refresh Data Table", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    try:
        # Pull data using basic Pandas just like your original app did
        csv_url = sheet_url.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv")
        raw_df = pd.read_csv(csv_url)
        
        st.metric("Total Rows Found in Sheet", len(raw_df))
        st.write("**Most Recent 5 Rows:**")
        st.dataframe(raw_df.tail(5), use_container_width=True)
    except Exception as e:
        st.caption(f"Note: Could not preview spreadsheet rows automatically ({e})")
