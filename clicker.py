# ==============================================================================
# 🧩 SECTION 1: CORE CONFIGURATION & DECODER LOGIC
# ==============================================================================
import streamlit as st
import pandas as pd
import requests
import datetime
import time

st.set_page_config(page_title="Clicker Response Terminal", layout="centered")
st.title("📟 Student Clicker Terminal")

# Initialize login states in persistent browser memory
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "student_id" not in st.session_state:
    st.session_state.student_id = ""
if "session_code" not in st.session_state:
    st.session_state.session_code = ""

# Secrets parsing
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

# Roster Mapping Engine
roster_dict = {}
if found_sheet_url:
    try:
        base_url_clk = str(found_sheet_url).split('/edit')[0] if '/edit' in str(found_sheet_url) else str(found_sheet_url)
        roster_url_clk = f"{base_url_clk.strip()}/gviz/tq?tqx=out:csv&sheet=roster&cb={int(time.time())}"
        roster_df_clk = pd.read_csv(roster_url_clk)
        for _, r in roster_df_clk.iterrows():
            raw_id = str(r.iloc[0]).strip()
            if raw_id.endswith('.0'): raw_id = raw_id[:-2]
            roster_dict[raw_id] = str(r.iloc[1]).strip()
    except:
        pass


# ==============================================================================
# 📡 SECTION 2: SCREEN SWITCHER & STAGE 1 (LOGIN SCREEN)
# ==============================================================================
if not st.session_state.logged_in:
    st.subheader("🔑 Step 1: Connect to Class")
    
    # 1. Manual Session Code Entry
    session_input = st.text_input("Enter Active Session Room Code:", placeholder="Type 4-digit code...").strip()
    clean_session = session_input[:-2] if session_input.endswith('.0') else session_input
    
    # 2. Student Remote ID Input
    id_input = st.text_input("Enter Your Remote Clicker ID Number:", placeholder="e.g. 4000").strip()
    clean_id = id_input[:-2] if id_input.endswith('.0') else id_input
    
    # Instant visual name mapping feedback right on the login gate
    if clean_id:
        if clean_id in roster_dict:
            st.success(f"👋 Recognised Name: **{roster_dict[clean_id]}**")
        else:
            st.caption(f"ℹ️ Logging in as Guest ID: `{clean_id}`")
            
    if st.button("🚪 Join Class Session", use_container_width=True):
        if not clean_session or not clean_id:
            st.error("Please fill in both fields to log into the room.")
        else:
            # Save entries to state and flip the screen lock switch
            st.session_state.session_code = clean_session
            st.session_state.student_id = clean_id
            st.session_state.logged_in = True
            st.cache_data.clear()
            st.rerun()
            
    st.stop() # Stops execution here so Stage 2 stays completely hidden


# ==============================================================================
# 👤 SECTION 3: STAGE 2 (CONNECTED HEADER PANEL)
# ==============================================================================
# Execution only reaches here if logged_in == True
student_display_name = roster_dict.get(st.session_state.student_id, f"Guest ({st.session_state.student_id})")

# Header showing current lock profiles
c1, c2 = st.columns(2)
with c1:
    st.caption(f"👤 Connected Student: **{student_display_name}**")
with c2:
    st.caption(f"📡 Active Session Room: **{st.session_state.session_code}**")

if st.button("⬅️ Disconnect / Change Room", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

st.markdown("---")


# ==============================================================================
# 🎮 SECTION 4: FREE-RESPONSE QUESTION STAGE
# ==============================================================================
st.subheader("📝 Answer Submission Panel")

target_question = st.text_input("❓ Target Question Identifier:", value="Q1").strip()
student_text_response = st.text_input("✏️ Type Your Answer Here:", placeholder="Enter numeric value or short answer text").strip()


# ==============================================================================
# 🚀 SECTION 5: PAYLOAD API DISPATCHER & TRANSMISSION
# ==============================================================================
if st.button("📤 Submit Clicker Action", use_container_width=True):
    if not target_question or not student_text_response:
        st.error("Submission Denied: Please provide a Question identifier and an Answer string.")
    elif not found_macro_url:
        st.error("Application configuration missing targeted Google App Script links.")
    else:
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "date": timestamp,
                "period": "student_input",
                "session_id": st.session_state.session_code,
                "student_id": st.session_state.student_id,
                "question": target_question,
                "answer": student_text_response,
                "is_correct": "PENDING"
            }
            
            clean_url = str(found_macro_url).strip()
            response = requests.post(clean_url, json=payload, timeout=5)
            
            st.success(f"🎉 Awesome, {student_display_name}! Your answer '{student_text_response}' was sent successfully.")
            st.balloons()
            
        except Exception as e:
            st.error(f"Network error encountered transmitting data packet: {e}")
