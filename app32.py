import streamlit as tf
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import random
import time

# ==============================================================================
# [SECTION 01: APP CONFIGURATION & STYLING]
# ==============================================================================
st.set_page_config(page_title="Clicker Teacher Dashboard", layout="wide", initial_sidebar_state="expanded")

# Inject responsive custom CSS for the dashboard interface cards
st.markdown("""
<style>
    .reportview-container { background: #1e272e; color: #ffffff; }
    .rainbow-card {
        background: linear-gradient(135deg, #ff007f, #7f00ff, #00bfff, #00ff7f);
        background-size: 300% 300%;
        animation: rainbow-animation 6s ease infinite;
        padding: 22px; border-radius: 12px; margin-bottom: 20px; color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3); border: none;
    }
    @keyframes rainbow-animation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# [SECTION 02: CORE SYSTEM STATE INITIALIZATION]
# ==============================================================================
if "app_logs" not in st.session_state:
    st.session_state.app_logs = []

def add_log(msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.app_logs.append(f"[{timestamp}] {msg}")

if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = "0000"
if "active_assignment" not in st.session_state:
    st.session_state.active_assignment = "default_assignment"

# ==============================================================================
# [SECTION 03: GOOGLE SHEETS CLOUD STORAGE CONNECTOR API]
# ==============================================================================
@st.cache_data(ttl=3)
def fetch_cloud_workbook_data():
    try:
        add_log("📡 Requesting raw binary workbook stream from Google API...")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Load your cloud secrets mapping safely
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Connect to your main sheet
        sheet_id = st.secrets["google_sheets"]["sheet_id"]
        workbook = client.open_by_key(sheet_id)
        
        # Pull raw sheets down to processing frames
        add_log("🔄 Executing data extraction pipeline...")
        responses_sheet = workbook.worksheet("responses").get_all_records()
        roster_sheet = workbook.worksheet("roster").get_all_records()
        answers_sheet = workbook.worksheet("answers").get_all_records()
        
        add_log(f"✅ Download successful! Discovered worksheets: {workbook.worksheets()}")
        return pd.DataFrame(responses_sheet), pd.DataFrame(roster_sheet), pd.DataFrame(answers_sheet), workbook
    except Exception as e:
        add_log(f"❌ Cloud Connection Error: {str(e)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None

# Execute safe pipeline read
all_data_df, roster_data, answers_data, raw_workbook = fetch_cloud_workbook_data()

# ==============================================================================
# [SECTION 04: TEACHER INTERFACE SIDEBAR CONTROLS]
# ==============================================================================
st.sidebar.title("🎮 Teacher Mission Control")
st.sidebar.markdown("---")

# Build target tracking layout keys from the answers spreadsheet headers
if not answers_data.empty:
    assignment_options = [col for col in answers_data.columns if col.lower() not in ["question", "answer", "id"]]
else:
    assignment_options = ["default_assignment"]

selected_assignment = st.sidebar.selectbox("📖 Target Tracking Assignment Layout:", assignment_options)
st.session_state.active_assignment = selected_assignment

if st.sidebar.button("🚀 Start New Session", use_container_width=True):
    # Generate a unique 4-digit numeric access string code
    new_code = str(random.randint(1000, 9999))
    st.session_state.active_session_id = new_code
    
    if raw_workbook is not None:
        try:
            # Sync active settings down to the active_session sheet loop channel
            active_ws = raw_workbook.worksheet("active_session")
            active_ws.clear()
            active_ws.append_row(["session_id", "active_assignment"])
            active_ws.append_row([new_code, selected_assignment])
            
            # Write a clean HANDSHAKE ROW directly into responses to anchor the network
            resp_ws = raw_workbook.worksheet("responses")
            timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            resp_ws.append_row([timestamp_str, selected_assignment, new_code, "SERVER", "ROOM_SET", "0", "TRUE"])
            
            add_log(f"🆕 Button Clicked: Starting brand new room session code {new_code}")
            add_log("📡 Broadcasted active session and assignment tracker down to the cloud sheet.")
            st.cache_data.clear()
            time.sleep(0.5)
            st.rerun()
        except Exception as ex:
            add_log(f"❌ Failed to broadcast new room layout variables: {str(ex)}")

st.sidebar.markdown("---")
st.sidebar.metric(label="🔑 Current Classroom Join Code:", value=st.session_state.active_session_id)
st.sidebar.metric(label="📚 Monitored Assessment:", value=st.session_state.active_assignment)

if st.sidebar.button("🔄 Hard Clear Dashboard Cache", use_container_width=True):
    st.cache_data.clear()
    add_log("🧹 Cache wiped manually by instructor dashboard button override.")
    st.rerun()

# ==============================================================================
# [SECTION 05: LIVE HEADCOUNT TRACKING SUMMARY]
# ==============================================================================
st.title("🍎 Classroom Response Matrix Dashboard")

# Determine active question index keys to evaluate classroom scale
if not answers_data.empty and selected_assignment in answers_data.columns:
    active_layout_map = answers_data.set_index("question")[selected_assignment]
    valid_qs = active_layout_map[active_layout_map.astype(str).str.strip() != ""].index.tolist()
    total_expected_questions = len(valid_qs)
else:
    total_expected_questions = 10

# ==============================================================================
# [SECTION 06: DATA PROCESSING & CALCULATION ENGINE]
# ==============================================================================
if all_data_df.empty:
    st.info("Waiting for incoming responses... Submit answers via the connected student remote.")
else:
    # Create a completely reliable working copy with explicit column tracking
    working_df = all_data_df.copy()
    
    # Enforce exact column names based on position to guarantee no mixing up of data fields
    if working_df.shape[1] >= 7:
        working_df.columns =
