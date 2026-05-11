import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re
import os

# --- 1. CONFIGURATION ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. AUTOMATIC CLUB LOOKUP GENERATION ---
# This part replaces the old CSV lookup with your 4 text files [cite: 1, 5, 6, 8]
membership_files = {
    "YF Youth.txt": "YF Youth",
    "Forever Young.txt": "Forever Young",
    "YF kids.txt": "YF kids",
    "YF teens.txt": "YF teens"
}

membership_lookup = {}

for file_name, project_label in membership_files.items():
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                for line in f:
                    # Clean the name to ensure matching works regardless of case
                    name = line.strip().lower()
                    # Filter out source tags or empty lines
                    if name and "[source" not in name and "participant" not in name:
                        membership_lookup[name] = project_label
        except Exception as e:
            st.error(f"Error reading {file_name}: {e}")

# --- 3. GOOGLE AUTHENTICATION ---
if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None

if "code" in st.query_params:
    try:
        code = st.query_params.get("code")
        google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
        token = google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, code=code, include_client_id=True)
        st.session_state.auth_creds = token
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Authentication Error: {e}")
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Bank to Sheets")
    st.markdown("Please log in to your Google account to enable Drive uploads.")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 4. CATEGORIES & OPTIONS ---
CAT_OPTIONS = ["Membership", "YF Logistics", "YF Travel", "Erasmus+", "Services", "Salaries", "Donations", "Operational Expenses", "Office supplies", "Rent & Admin", "Single payment"]
PROJ_OPTIONS = ["projekti", "NVA / ESF", "Erasmus+ KA210 project \"Young Business\"", "Erasmus+ project Project 101239301 \"Zemlya\"", "Erasmus+ KA210 \"SHIFT\"", "projekts Lapas GEAR UP! \"Līderu Skola\"", "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)", "Valsts Kase projekts KA210 \"Youth Identiy Hub\" (400B)", "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)", "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)", "Erasmus+ General", "Erasmus", "nodokļi", "YF Main", "YF kids", "YF teens", "YF Youth", "Forever Young", "New York", "Iceland", "Japan", "Say it Ring", "Sense (design)", "Latvian language", "English language", "Workshops", "Office Rent", "Animators"]

# --- 5. DATA PROCESSING LOGIC ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"

    # Default category/project
    category = "Single payment"
    project = "YF Main"

    # Step 1: Detect Category based on Keywords
    cat_keywords = {
        "dalīb": "Membership", "biedr": "Membership", "abonement": "Membership",
        "ziedojum": "Donations", "stipendija": "Salaries", "alga": "Salaries",
        "bolt": "YF Logistics", "wolt": "YF Logistics", "citybee": "YF Logistics",
        "noma": "Rent & Admin", "komisija": "Operational Expenses"
    }
    for kw, cat in cat_keywords.items():
        if kw in full_text:
            category = cat
            break

    # Step 2: Assign Project based on the Text Files (Highest Priority)
    # This checks if the name (e.g., Dmitrijs Tarasovs) exists in your files [cite: 1, 5, 6, 8]
    if name_lower in membership_lookup:
        project = membership_lookup[name_lower]
        # If they are in a club file, it's likely a Membership or Service fee
        if category == "Single payment":
            category = "Membership"
    
    # Step 3: Specific Project Overrides (NVA, Projects, etc.)
    if "nva" in purpose_lower:
        project = "NVA / ESF"
        category = "Salaries"
    elif "200b" in purpose_lower:
        project = "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)"

    return category, project

# --- 6. DRIVE INTEGRATION ---
def upload_and_convert(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 7. STREAMLIT INTERFACE ---
st.title("🚀 Bank Automator v2")
st.info(f"Loaded {len(membership_lookup)} members from internal lists.")

uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        # Load and filter data
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}')].copy()

        # Parse Name, IBAN, etc.
        def parse_details(val):
            parts = [p.strip() for p in str(val).split('|')]
            return parts[0] if parts else ""

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = df_filtered[3].apply(parse_details)
        df_proc['Purpose'] = df_filtered[4]
        
        amounts = pd.to_numeric(df_filtered[5].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        df_proc['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D').fillna(0.0)

        # Apply the new logic
        results = df_proc.apply(process_row, axis=1)
        df_proc['Category'] = [r[0] for r in results]
        df_proc['Project Name'] = [r[1] for r in results]

        st.dataframe(df_proc)

        if st.button("📤 Export to Google Sheets"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='Report')
            output.seek(0)
            
            link = upload_and_convert(output, f"Bank_Report_{datetime.now().strftime('%Y%m%d')}")
            st.success("File uploaded successfully!")
            st.link_button("📊 Open Google Sheet", link)

    except Exception as e:
        st.error(f"Error processing file: {e}")
