import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re
import os

# --- 1. KONFIGURĀCIJA ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. LOAD MEMBERSHIP FROM TXT FILES ---
membership_files = {
    "YF Youth.txt": "YF Youth",
    "Forever Young.txt": "Forever Young",
    "YF kids.txt": "YF kids",
    "YF teens.txt": "YF Teens"
}

membership_lookup = {}
for file_name, div_label in membership_files.items():
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                for line in f:
                    name_clean = line.strip().lower()
                    if name_clean and name_clean != "participant":
                        membership_lookup[name_clean] = div_label
        except Exception as e:
            st.error(f"Could not load {file_name}: {e}")

# --- 3. AUTENTIFIKĀCIJA ---
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
        st.error(f"Pieteikšanās kļūda: {e}")
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Bank to Sheets")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 4. OPTIONS & FILTERS (Updated Lists) ---
CAT_OPTIONS = ["Donations", "Erasmus+", "Help Ukraine", "Membership", "Operational Expenses", "Projects", "Salaries", "Services", "YE Travel"]

DIV_OPTIONS = [
    "Academic drawing", "BNI Artmen", "Comission", "E+ YE Voices in action", "English language", "Erasmus", "Erasmus Adult", 
    "Forever Young", "German", "Internetbank", "JEF Europe", "Latvian language", "Madeira", "NVA / ESF", "Office Rent", 
    "Office supplies", "Reimbursement", "Say it Ring", "Sense (design)", "Taxes", 'Valsts Kase projekts ESC30 "Youth', 
    "Workshops", "YE GREEN REALITIES", "YF kids", "YF logistics", "YF Main", "YF Teens", "YF Youth"
]

SUB_OPTIONS = ["APV GREEN REALITIES", "Brainring", "Christmas party", "Cinema production", "Coaching", "Creative jam event", "Italy?", "Reimbursement", "Sarunvalodas", "Speed Friending", "Umniy dom", "Winter camp"]

# Filters for keyword detection
CAT_FILTER = {
    "dalības": "Membership", "biedru nauda": "Membership", "dalībmaksa": "Membership", "abonements": "Membership",
    "ziedojums": "Donations", "ziedojumu": "Donations", "stipendija": "Salaries", "alga": "Salaries", "nodokli": "Salaries",
    "bolt": "Operational Expenses", "wolt": "Operational Expenses", "citybee": "Operational Expenses", "noma": "Operational Expenses",
    "lekcija": "Services", "valoda": "Services", "sarunvalodas": "Services", "akademicheskiy": "Services", "gleznieciba": "Services"
}

# --- 5. DATA LOGIC ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"

    category = "Services" # Default
    division = "YF Main"  # Default
    sub = ""              # Default empty

    # Priority 1: Check the 4 Text Files for Name Match
    if name_lower in membership_lookup:
        division = membership_lookup[name_lower]
        category = "Membership"
    
    # Priority 2: Keyword detection for Category
    for kw, cat in CAT_FILTER.items():
        if kw in full_text:
            category = cat
            break

    # Priority 3: Specific Division Overrides
    if "nva" in full_text:
        division = "NVA / ESF"
        category = "Salaries"
    elif "taxes" in full_text or "nodokli" in full_text:
        division = "Taxes"
        category = "Salaries"
    elif "internetbank" in full_text or "komisija" in full_text:
        division = "Internetbank"
        category = "Operational Expenses"
    elif "bolt" in full_text or "citybee" in full_text:
        division = "YF logistics"

    return category, division, sub

# --- 6. DRIVE & APP FLOW ---
def upload_and_convert(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

st.title("🏦 Bank Automator")

uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        def parse_partner_details(val):
            if not val: return "", "", "", ""
            parts = [p.strip() for p in str(val).split('|')]
            name = parts[0]
            p_code, iban, swift = "", "", ""
            for p in parts[1:]:
                clean = p.replace(" ", "").upper()
                if re.match(r'^\d{6}-\d{5}$', clean): p_code = clean
                elif len(clean) >= 15 and clean[0:2].isalpha(): iban = clean
                elif len(clean) in [8, 11] and clean[0:4].isalpha(): swift = clean
            return name, p_code, iban, swift

        parsed_data = df_filtered[3].apply(parse_partner_details)
        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = [x[0] for x in parsed_data]
        df_proc['Personal Code'] = [x[1] for x in parsed_data]
        df_proc['Konta numurs'] = [x[2] for x in parsed_data]
        df_proc['Bankas SWIFT'] = [x[3] for x in parsed_data]
        df_proc['Purpose'] = df_filtered[4]
        
        amounts_raw = pd.to_numeric(df_filtered[5].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        df_proc['K (KREDITS)'] = amounts_raw.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['D (DEBETS)'] = amounts_raw.where(df_filtered[7] == 'D').fillna(0.0)
        
        # Apply the new 3-column logic
        results = df_proc.apply(process_row, axis=1)
        df_proc['Category'] = [r[0] for r in results]
        df_proc['Division'] = [r[1] for r in results]
        df_proc['Sub'] = [r[2] for r in results]
        df_proc['Commentary'] = ""

        if st.button(f"🚀 CREATE BANK REPORT"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankReport')
                workbook, worksheet = writer.book, writer.sheets['BankReport']
                
                # Hidden Data for Dropdowns
                options_sheet = workbook.add_worksheet('HiddenData')
                for i, val in enumerate(CAT_OPTIONS): options_sheet.write(i, 0, val)
                for i, val in enumerate(DIV_OPTIONS): options_sheet.write(i, 1, val)
                for i, val in enumerate(SUB_OPTIONS): options_sheet.write(i, 2, val)
                options_sheet.hide()

                last_row = len(df_proc) + 1
                # Category Dropdown (Column I)
                worksheet.data_validation(f'I2:I{last_row}', {'validate': 'list', 'source': f'=HiddenData!$A$1:$A${len(CAT_OPTIONS)}'})
                # Division Dropdown (Column J)
                worksheet.data_validation(f'J2:J{last_row}', {'validate': 'list', 'source': f'=HiddenData!$B$1:$B${len(DIV_OPTIONS)}'})
                # Sub Dropdown (Column K)
                worksheet.data_validation(f'K2:K{last_row}', {'validate': 'list', 'source': f'=HiddenData!$C$1:$C${len(SUB_OPTIONS)}'})
                
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(df_proc.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                
                worksheet.set_column('A:B', 15); worksheet.set_column('C:E', 28); worksheet.set_column('F:F', 50); worksheet.set_column('G:L', 25)

            output.seek(0)
            link = upload_and_convert(output, f"Bank_Export_{datetime.now().strftime('%Y-%m-%d')}")
            if link:
                st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#0F9D58;color:white;padding:25px;border-radius:15px;text-align:center;font-size:22px;font-weight:bold;">📊 OPEN GOOGLE SHEET</div></a>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
