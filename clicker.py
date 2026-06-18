import streamlit as st
import requests
from datetime import datetime

# ==============================================================================
# 📋 PROJECT VERSION LOG
# ==============================================================================
# Version Name: clicker.py (Student Qwizdom Clicker - Iteration 1)
# Features: Simplified entry bypass. No strict server-side authentication.
# Target: Validates the direct end-to-end webhook upload pipeline to Google Sheets.
# ==============================================================================

st.set_page_config(page_title="Student Qwizdom Remote", layout="centered")

# --- CUSTOM TACTILE QWIZDOM REMOTE CSS ---
st.markdown("""
<style>
.lcd-screen {
    background-color: #1a2332;
    color: #39ff14;
    font-family: 'Courier New', Courier, monospace;
    padding: 15px;
    border-radius: 8px;
    border: 4px solid #343a40;
    margin-bottom: 25px;
    box-shadow: inset 0px 0px 10px rgba(0,0,0,0.8);
}
</style>
""", unsafe_allow_html=True)

# --- PHYSICAL LCD CLICKER SCREEN ---
st.markdown('<div class="lcd-screen">📟 QWIZDOM REMOTE V1.0<br>STATUS: READY TO EMIT</div>', unsafe_allow_html=True)

st.title("📱 Student Clicker Remote")
st.write("Iteration 1: Direct Webhook Pass-Through")

# --- PASS-THROUGH INPUT FIELDS (No validation for Iteration 1) ---
sim_session = st.text_input("Active Session Code", value="1234")
sim_id = st.text_input("Your Student ID", value="4000")
sim_q = st.selectbox("Select Question Target", options=[f"Q{i}" for i in range(1, 11)])
sim_ans = st.number_input("Input Your Numeric Answer", value=0.0, step=0.1)

st.markdown("---")

# --- DISPATCH WEBHOOK BUTTON ---
if st.button("🚀 PRESS SEND", use_container_width=True):
    # Construct the payload format your Google Macro script expects
    timestamp_payload = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
        "period": "Period 1", # Hardcoded default placeholder for iteration 1
        "session_id": str(sim_session).strip(), 
        "student_id": str(sim_id).strip(),
        "question": str(sim_q), 
        "answer": float(sim_ans), 
        "is_correct": True # Default true bypass for connection testing
    }
    
    st.info("Firing transmission packet to Google Sheets...")
    
    try:
        # Pull your existing macro URL directly from the app secrets
        macro_link = st.secrets["connections"]["gsheets"]["macro_url"]
        response = requests.post(macro_link, json=timestamp_payload)
        
        if response.status_code == 200:
            st.success(f"🎯 SENT SUCCESSFULLY! Checked row in Google Sheet for {sim_q}.")
        else:
            st.error(f"⚠️ Server received payload but returned HTTP error code: {response.status_code}")
            
    except Exception as e:
        st.error(f"🚨 Pipeline routing error: {e}")
