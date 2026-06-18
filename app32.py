import streamlit as st
import pandas as pd
import requests
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Simplified Session Broadcaster with Configuration Debugger")

# 🔍 Look for keys inside secrets dynamically to prevent hardcoded naming mismatches
found_macro_url = None
found_sheet_url = None

# Scan top-level secrets
for key in st.secrets.keys():
    val = str(st.secrets[key])
    if "script.google.com" in val:
        found_macro_url = st.secrets[key]
    elif "docs.google.com/spreadsheets" in val:
        found_sheet_url = st.secrets[key]

# Scan nested google_sheets secrets block if it exists
if "google_sheets" in st.secrets:
    for key in st.secrets["google_sheets"].keys():
        val = str(st.secrets["google_sheets"][key])
        if "script.google.com" in val:
            found_macro_url = st.secrets["google_sheets"][key]
        elif "docs.google.com/spreadsheets" in val:
            found_sheet_url = st.secrets["google_sheets"][key]

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
            response = requests.post(found_macro_url, json=payload, timeout=5)
            st.success(f"Broadcast sent down the wire! Code {new_code} is live.")
        except Exception as e:
            st.error(f"Could not broadcast row via API: {e}")
    else:
        st.warning(f"Code updated locally to {new_code}, but your Google script URL could not be found in secrets.")

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
st.caption("Use this console to see exactly what keys are configured in your Streamlit Cloud account settings.")

if st.button("🔄 Refresh Debug Console", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# 1. Inspect Secret Keys
st.write("**Detected Configuration Keys inside your Secrets file:**")
all_secret_keys = list(st.secrets.keys())
if "google_sheets" in st.secrets:
    nested_keys = [f"google_sheets -> {k}" for k in st.secrets["google_sheets"].keys()]
    all_secret_keys.extend(nested_keys)
st.code(str(all_secret_keys))

# 2. Check Macro API Link Status
if found_macro_url:
    st.success("✅ Google Apps Script Broadcaster Link: **FOUND**")
else:
    st.error("❌ Google Apps Script Broadcaster Link: **MISSING** (Ensure your macro/script URL is added to your app secrets!)")

# 3. Inspect Spreadsheet Data
if not found_sheet_url:
    st.caption("Add your main Google Sheets URL to secrets to display raw rows.")
else:
    try:
        # Convert spreadsheet view link to raw CSV download stream cleanly
        base_url = found_sheet_url.split('/edit')[0] if '/edit' in found_sheet_url else found_sheet_url
        csv_url = f"{base_url}/gviz/tq?tqx=out:csv"
        
        raw_df = pd.read_csv(csv_url)
        st.metric("Total Rows Processed in Spreadsheet Log", len(raw_df))
        
        st.write("**Spreadsheet Headers detected:**")
        st.code(str(list(raw_df.columns)))
        
        st.write("**Most Recent 5 Rows sitting in the Google Sheet:**")
        st.dataframe(raw_df.tail(5), use_container_width=True)
    except Exception as e:
        st.caption(f"Awaiting response log streams... ({e})")
