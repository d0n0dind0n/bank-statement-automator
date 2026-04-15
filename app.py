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

# --- 2. AUTHENTICATION LOGIC ---
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

# --- 3. DROPDOWN LISTS ---
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

# --- 4. THE UPLOAD & CONVERT FUNCTION ---
def upload_and_convert_to_sheet(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    
    # CRITICAL: This 'mimeType' converts the Excel file into a Google Sheet automatically
    file_metadata = {
        'name': file_name,
        'mimeType': 'application/vnd.google-apps.spreadsheet' 
    }
    
    media = MediaIoBaseUpload(
        file_data, 
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        resumable=True
    )
    
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. MAIN APP INTERFACE ---
st.title("🏦 CSV to Google Sheets Automator")
st.write("Upload your bank CSV. I will convert it and add dropdown menus for you.")

uploaded_file = st.file_uploader("Choose Bank CSV", type="csv")

if uploaded_file:
    try:
        # 1. Read and Clean CSV
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Partner'] = df_filtered[3].str.split('|').str[0].str.strip()
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        amounts = pd.to_numeric(df_filtered[5].str.replace(',', '.'), errors='coerce')
        df_proc['Income'] = amounts.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['Expense'] = amounts.where(df_filtered[7] == 'D').fillna(0.0)
        
        # Add the target columns for dropdowns
        df_proc['Category'] = ""
        df_proc['Project'] = ""
        df_proc['Commentary'] = ""

        st.success(f"Processed {len(df_proc)} transactions.")

        if st.button("🚀 CONVERT & OPEN IN GOOGLE SHEETS"):
            output = io.BytesIO()
            
            # Create Excel in memory with Data Validation (Dropdowns)
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankData')
                workbook  = writer.book
                worksheet = writer.sheets['BankData']
                
                # Apply dropdowns to Category (Column F) and Project (Column G)
                # Setting range to 2000 rows to ensure all data is covered
                worksheet.data_validation('F2:F2000', {'validate': 'list', 'source': CAT_OPTIONS})
                worksheet.data_validation('G2:G2000', {'validate': 'list', 'source': PROJ_OPTIONS})
                
                # Auto-adjust column widths for better readability
                worksheet.set_column('A:B', 15)
                worksheet.set_column('C:C', 40)
                worksheet.set_column('D:E', 12)
                worksheet.set_column('F:G', 25)

            output.seek(0)
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
            final_name = f"Bank_Report_{timestamp}"
            
            with st.spinner("Converting to Google Sheet..."):
                link = upload_and_convert_to_sheet(output, final_name)
            
            if link:
                st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                    <div style="background-color:#0F9D58;color:white;padding:25px;border-radius:12px;text-align:center;font-size:22px;font-weight:bold;">
                    📊 CLICK HERE TO OPEN YOUR SHEET
                    </div></a>''', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Something went wrong: {e}")
