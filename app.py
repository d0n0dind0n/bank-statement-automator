import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime

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
CAT_OPTIONS = [
    "Membership YF kids", "Membership YF teens", "Membership Youth", 
    "Membership Forever Young", "Membership & Donations", "Salaries NVA", 
    "Salaries YF Main", "Salaries projekti", "Salaries nodokļi", 
    "YF Travel Japan", "YF Travel New York", "YF Travel Iceland", 
    "Logistics & Travel", "Services Office Rent", "Operational Expenses", 
    "Office supplies", "Rent & Admin"
]

PROJ_OPTIONS = [
    "NVA / ESF", "DiscoverEU (200B)", "Youth Identity Hub (400B)", 
    "Youth Podcast Station (300B)", "Youth Work Bus (500B)", 
    "Young Business (KA210)", "Zemlya (101239301)", "SHIFT (KA210)", 
    "Līderu Skola (GEAR UP!)", "Young Folks"
]

# --- 4. UPLOAD FUNCTION ---
def upload_and_convert(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. PROCESSING ---
st.title("🏦 Bank to Sheets Automator")
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        # Load CSV
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        
        # Filter rows that actually contain a date in column index 2
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        # Build DataFrame based on your image structure
        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        
        # Extract Name and Personal Code from column index 3
        # We use expand=True to safely turn the split into a DataFrame
        split_details = df_filtered[3].str.split('|', expand=True)
        
        df_proc['Name Surname'] = split_details[0].str.strip()
        # If there is no second part after '|', it fills with empty string
        df_proc['Personal Code'] = split_details[1].str.strip() if 1 in split_details.columns else ""
        
        # Konta numurs is usually column index 6
        df_proc['Konta numurs'] = df_filtered[6].fillna("")
        df_proc['Bankas SWIFT'] = "" # Leave empty for manual entry or future mapping
        
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        # Handle Money
        amounts = pd.to_numeric(df_filtered[5].str.replace(',', '.'), errors='coerce')
        df_proc['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D').fillna(0.0)
        
        # Target Dropdown Columns
        df_proc['Category'] = ""      # Col I (Index 8)
        df_proc['Project Name'] = ""  # Col J (Index 9)
        df_proc['Commentary'] = ""    # Col K (Index 10)

        st.info(f"Transactions found: {len(df_proc)}")

        if st.button("🚀 CREATE GOOGLE SHEET"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankReport')
                workbook  = writer.book
                worksheet = writer.sheets['BankReport']
                
                # Hidden sheet for dropdown lists
                options_sheet = workbook.add_worksheet('HiddenData')
                for i, cat in enumerate(CAT_OPTIONS): options_sheet.write(i, 0, cat)
                for i, proj in enumerate(PROJ_OPTIONS): options_sheet.write(i, 1, proj)
                options_sheet.hide()

                # Dropdowns: Column I (Index 8) and J (Index 9)
                worksheet.data_validation('I2:I2000', {'validate': 'list', 'source': f'=HiddenData!$A$1:$A${len(CAT_OPTIONS)}'})
                worksheet.data_validation('J2:J2000', {'validate': 'list', 'source': f'=HiddenData!$B$1:$B${len(PROJ_OPTIONS)}'})
                
                # Format Header
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(df_proc.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                
                # Column widths
                worksheet.set_column('A:B', 15)
                worksheet.set_column('C:E', 22)
                worksheet.set_column('F:F', 45)
                worksheet.set_column('G:K', 18)

            output.seek(0)
            fname = f"Bank_Atskaite_{datetime.now().strftime('%Y%m%d_%H%M')}"
            link = upload_and_convert(output, fname)
            
            if link:
                st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                    <div style="background-color:#0F9D58;color:white;padding:25px;border-radius:15px;text-align:center;font-size:22px;font-weight:bold;">
                    📊 OPEN GOOGLE SHEET
                    </div></a>''', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
