import streamlit as st
import pandas as pd
import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re

# --- 1. CONFIGURATION ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. LOAD MEMBERSHIP REFERENCE (CSV) ---
@st.cache_data
def get_membership_mapping():
    mapping = {}
    file_path = "membership.csv"
    
    if not os.path.exists(file_path):
        st.warning("⚠️ membership.csv not found in repository. Please check your GitHub files.")
        return {}

    try:
        ref_df = pd.read_csv(file_path)
        ref_df.columns = [str(c).strip() for c in ref_df.columns]
        
        for _, row in ref_df.iterrows():
            project = str(row['Club']).strip() if pd.notna(row['Club']) else "YF Main"
            if 'Participant' in ref_df.columns and pd.notna(row['Participant']):
                mapping[str(row['Participant']).lower().strip()] = project
            if 'Parent' in ref_df.columns and pd.notna(row['Parent']):
                mapping[str(row['Parent']).lower().strip()] = project
        return mapping
    except Exception as e:
        st.error(f"⚠️ Error reading membership.csv: {e}")
        return {}

MEMBERSHIP_MAP = get_membership_mapping()

# --- 3. ALL ORIGINAL FILTER SETTINGS ---
CAT_OPTIONS = [
    "Membership", "YF Logistics", "YF Travel", "Erasmus+",
    "Services", "Salaries", "Donations", "Operational Expenses",
    "Office supplies", "Rent & Admin", "Single payment"
]

PROJ_OPTIONS = [
    "projekti", "NVA / ESF", "Erasmus+ KA210 project \"Young Business\"",
    "Erasmus+ project Project 101239301 \"Zemlya\"", "Erasmus+ KA210 \"SHIFT\"",
    "projekts Lapas GEAR UP! \"Līderu Skola\"",
    "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)",
    "Valsts Kase projekts KA210 \"Youth Identity Hub\" (400B)",
    "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)",
    "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)",
    "Erasmus+ General", "Erasmus", "nodokļi", "YF Main", "YF kids", "YF teens",
    "Youth", "Forever Young", "New York", "Iceland", "Japan",
    "Say it Ring", "Sense (design)", "Latvian language", "English language",
    "Workshops", "Office Rent", "Animators"
]

# Filtering keywords for Categories
CAT_FILTER = {
    "dalības": "Membership", "biedru nauda": "Membership", "yf2026": "Membership",
    "ziedojums": "Donations", "alga": "Salaries", "lekcija": "Services",
    "sarunvalodas": "Services", "akademicheskiy risunok": "Services",
    "kartes mēneša maksa": "Operational Expenses", "noma": "Operational Expenses"
}

# Filtering keywords for Projects
PROJ_FILTER = {
    "erasmus": "Erasmus", "nva": "NVA / ESF", "kids": "YF kids", "bērnu": "YF kids",
    "meistarklase": "Workshops", "akademicheskiy": "Workshops"
}

# --- 4. CORE LOGIC ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"
    
    project = "YF Main"
    
    # 1. Check membership mapping (Child or Parent Name)
    if name_lower in MEMBERSHIP_MAP:
        project = MEMBERSHIP_MAP[name_lower]
    else:
        for ref_name, ref_project in MEMBERSHIP_MAP.items():
            if ref_name in purpose_lower:
                project = ref_project
                break

    # 2. Priority phrase/regex overrides
    if project == "YF Main":
        if "lv nodarbības" in full_text or re.search(r'\b(latv|val)\b', full_text):
            project = "Latvian language"
        elif re.search(r'\bnva\b', purpose_lower):
            project = "NVA / ESF"
        else:
            for key, val in PROJ_FILTER.items():
                if key in full_text:
                    project = val
                    break

    # 3. Determine Category
    category = ""
    # Auto-category for specific clubs
    is_membership_club = any(x in project for x in ["Forever Young", "YF kids", "YF teens", "Youth"])
    
    if "dalības" in full_text or "biedru nauda" in full_text or is_membership_club:
        category = "Membership"
    elif "noma" in full_text:
        category = "Operational Expenses"
    else:
        for kw, cat in CAT_FILTER.items():
            if kw in full_text:
                category = cat
                break
    
    # Default fallback if no category matched
    if not category:
        category = "Services"
                
    return category, project

# --- 5. GOOGLE AUTH ---
if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None

if "code" in st.query_params:
    try:
        code = st.query_params.get("code")
        google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
        token = google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, code=code)
        st.session_state.auth_creds = token
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Login error: {e}")

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Bank Automator")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 6. MAIN APP ---
st.title("🏦 Bank Statement Automator")
uploaded_file = st.file_uploader("Upload Bank Statement (CSV)", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = df_filtered[3].apply(lambda x: str(x).split('|')[0].strip())
        df_proc['Purpose'] = df_filtered[4]
        
        amounts = pd.to_numeric(df_filtered[5].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        df_proc['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K', 0.0)
        df_proc['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D', 0.0)
        
        # Apply Logic
        results = df_proc.apply(process_row, axis=1)
        df_proc['Category'] = [r[0] for r in results]
        df_proc['Project Name'] = [r[1] for r in results]
        df_proc['Commentary'] = ""

        st.dataframe(df_proc.head(10))

        if st.button("🚀 CREATE GOOGLE SHEET"):
            from google.oauth2.credentials import Credentials
            creds = Credentials(token=st.session_state.auth_creds['access_token'])
            service = build('drive', 'v3', credentials=creds)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankReport')
                workbook = writer.book
                worksheet = writer.sheets['BankReport']

                # Dropdown data
                options_sheet = workbook.add_worksheet('HiddenData')
                for i, cat in enumerate(CAT_OPTIONS): options_sheet.write(i, 0, cat)
                for i, proj in enumerate(PROJ_OPTIONS): options_sheet.write(i, 1, proj)
                options_sheet.hide()

                last_row = len(df_proc) + 1
                worksheet.data_validation(f'F2:F{last_row}', {'validate': 'list', 'source': '=HiddenData!$A$1:$A$11'})
                worksheet.data_validation(f'G2:G{last_row}', {'validate': 'list', 'source': '=HiddenData!$B$1:$B$30'})

            output.seek(0)
            file_metadata = {'name': f"Bank_Export_{datetime.now().strftime('%Y-%m-%d')}", 'mimeType': 'application/vnd.google-apps.spreadsheet'}
            media = MediaIoBaseUpload(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            
            st.success(f"File created! [Open Google Sheet]({file.get('webViewLink')})")

    except Exception as e:
        st.error(f"Error: {e}")
