import streamlit as st
import pandas as pd
import io
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

# --- 2. AUTHENTICATION ---
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
        st.error(f"Login error: {e}")
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Bank to Google Sheets")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 3. DATA LISTS ---
CAT_OPTIONS = ["Membership YF kids", "Membership YF teens", "Membership Youth", "Membership Forever Young", "Membership & Donations", "Salaries NVA", "Salaries YF Main", "Salaries projekti", "Salaries nodokļi", "YF Travel Japan", "YF Travel New York", "YF Travel Iceland", "Logistics & Travel", "Services Office Rent", "Operational Expenses", "Office supplies", "Rent & Admin"]
PROJ_OPTIONS = ["NVA / ESF", "DiscoverEU (200B)", "Youth Identity Hub (400B)", "Youth Podcast Station (300B)", "Youth Work Bus (500B)", "Young Business (KA210)", "Zemlya (101239301)", "SHIFT (KA210)", "Līderu Skola (GEAR UP!)", "Young Folks"]

# --- 4. DRIVE UPLOAD ---
def upload_and_convert(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. DATA PROCESSING ---
st.title("🏦 Bank to Sheets Automator")
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        # Load CSV
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip').fillna("")
        
        # Filter rows with transaction dates in column index 2
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        # UPDATED extraction logic for Column 3
        def parse_partner_details(val):
            if not val: return "", "", "", ""
            parts = [p.strip() for p in str(val).split('|')]
            name = parts[0]
            personal_code = ""
            iban = ""
            swift = ""
            
            for p in parts[1:]:
                clean = p.replace(" ", "").upper()
                # 1. Personal Code (Pattern: 123456-12345)
                if re.match(r'^\d{6}-\d{5}$', clean):
                    personal_code = clean
                # 2. IBAN (Starts with letters, usually 15-30 chars)
                elif len(clean) >= 15 and clean[0:2].isalpha():
                    iban = clean
                # 3. SWIFT (8 or 11 characters)
                elif len(clean) in [8, 11] and clean[0:4].isalpha():
                    swift = clean
            return name, personal_code, iban, swift

        # Apply parsing to column index 3
        parsed_data = df_filtered[3].apply(parse_partner_details)
        
        # Build Report DataFrame
        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = [x[0] for x in parsed_data]
        df_proc['Personal Code'] = [x[1] for x in parsed_data] # <--- PERSONAL CODE NOW INCLUDED
        df_proc['Konta numurs'] = [x[2] for x in parsed_data]
        df_proc['Bankas SWIFT'] = [x[3] for x in parsed_data]
        df_proc['Purpose'] = df_filtered[4]
        
        # Monetary data
        amounts = pd.to_numeric(df_filtered[5].astype(str).str.replace(',', '.'), errors='coerce')
        df_proc['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D').fillna(0.0)
        
        df_proc['Category'] = ""      
        df_proc['Project Name'] = ""  
        df_proc['Commentary'] = ""    

        if st.button("🚀 CREATE GOOGLE SHEET"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankReport')
                workbook  = writer.book
                worksheet = writer.sheets['BankReport']
                
                # Validation Lists
                options_sheet = workbook.add_worksheet('HiddenData')
                for i, cat in enumerate(CAT_OPTIONS): options_sheet.write(i, 0, cat)
                for i, proj in enumerate(PROJ_OPTIONS): options_sheet.write(i, 1, proj)
                options_sheet.hide()

                # Column I (index 8) and J (index 9) Dropdowns
                worksheet.data_validation('I2:I2000', {'validate': 'list', 'source': f'=HiddenData!$A$1:$A${len(CAT_OPTIONS)}'})
                worksheet.data_validation('J2:J2000', {'validate': 'list', 'source': f'=HiddenData!$B$1:$B${len(PROJ_OPTIONS)}'})
                
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(df_proc.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                
                # Column widths for visibility
                worksheet.set_column('A:B', 15) # Date & Name
                worksheet.set_column('C:E', 28) # Code, IBAN, SWIFT
                worksheet.set_column('F:F', 50) # Purpose
                worksheet.set_column('G:K', 20)

            output.seek(0)
            fname = f"Bank_Export_{datetime.now().strftime('%H%M')}"
            link = upload_and_convert(output, fname)
            
            if link:
                st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                    <div style="background-color:#0F9D58;color:white;padding:25px;border-radius:15px;text-align:center;font-size:22px;font-weight:bold;">
                    📊 OPEN GOOGLE SHEET
                    </div></a>''', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
