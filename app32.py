import streamlit as st
import pandas as pd
import requests
import datetime
import random

st.set_page_config(page_title="Clicker Mission Control", layout="centered")
st.title("🎮 Clicker Mission Control")
st.caption("Simplified Session Broadcaster with Dictionary Parsing")

# 🔍 Safely extract the strings from the nested secrets block
found_macro_url = None
found_sheet_url = None

# First check if the structured "gsheets" dictionary block exists
if "gsheets" in st.secrets:
    try:
        found_macro_url = st.secrets["gsheets"].get("macro_url")
        found_sheet_url = st.secrets["gsheets"].get("spreadsheet") or st.secrets["gsheets"].get("public_url")
    except Exception:
        pass

# Fallback: Scan top-level secrets if the block structure is flattened
if not found_macro_url or not found_sheet_url:
    for key in st.secrets.keys():
        val = str(st.secrets[key])
        if "script.google.com" in val:
            found_macro_url = val
        elif "docs.google.com/spreadsheets" in val:
            found_sheet_url = val

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
            # Fire standard POST request using the isolated string link
            response = requests.post(str(found_macro_url).strip(), json=payload, timeout=5)
            st.success(f"Broadcast sent! Code {new_code} is live on your sheet.")
        except Exception as e:
            st.error(f"Could not broadcast row via API: {e}")
    else:
        st.warning(f"Code updated locally to {new_code}, but your macro_url could not be isolated.")

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
        base_url = found_sheet_url.split('/edit')[0] if '/edit' in found_sheet_url else found_sheet_url
        csv_url = f"{base_url}/gviz/tq?tqx=out:csv"
        
        raw_df = pd.read_csv(csv_url)
        st.metric("Total Rows Processed in Spreadsheet Log", len(raw_df))
        
        st.write("**Most Recent 5 Rows sitting in your Sheet right now:**")
        st.dataframe(raw_df.tail(5), use_container_width=True)
    except Exception as e:
        st.caption(f"Awaiting response log streams... ({e})")
