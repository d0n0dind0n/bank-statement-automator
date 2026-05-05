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

# --- 2. LOAD MEMBERSHIP REFERENCE ---
@st.cache_data
def get_membership_mapping():
    mapping = {}
    if os.path.exists("membership.csv"):
        try:
            ref_df = pd.read_csv("membership.csv")
            ref_df.columns = [str(c).strip() for c in ref_df.columns]
            for _, row in ref_df.iterrows():
                project = str(row['Club']).strip() if pd.notna(row['Club']) else "YF Main"
                if 'Participant' in ref_df.columns and pd.notna(row['Participant']):
                    mapping[str(row['Participant']).lower().strip()] = project
                if 'Parent' in ref_df.columns and pd.notna(row['Parent']):
                    mapping[str(row['Parent']).lower().strip()] = project
        except: pass
    return mapping

MEMBERSHIP_MAP = get_membership_mapping()

# --- 3. OPTIONS ---
CAT_OPTIONS = ["Membership", "YF Logistics", "YF Travel", "Erasmus+", "Services", "Salaries", "Donations", "Operational Expenses", "Office supplies", "Rent & Admin", "Single payment"]
PROJ_OPTIONS = ["projekti", "NVA / ESF", "Erasmus+ KA210 project \"Young Business\"", "Erasmus+ project Project 101239301 \"Zemlya\"", "Erasmus+ KA210 \"SHIFT\"", "projekts Lapas GEAR UP! \"Līderu Skola\"", "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)", "Valsts Kase projekts KA210 \"Youth Identity Hub\" (400B)", "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)", "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)", "Erasmus+ General", "Erasmus", "nodokļi", "YF Main", "YF kids", "YF teens", "Youth", "Forever Young", "New York", "Iceland", "Japan", "Say it Ring", "Sense (design)", "Latvian language", "English language", "Workshops", "Office Rent", "Animators"]

# --- 4. DATA PROCESSING LOGIC ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"
    
    # RULE: Card purchases (PIRKUMS) are always YF Main / Operational Expenses
    if "pirkums" in full_text:
        return "Operational Expenses", "YF Main"

    project = "YF Main"
    if name_lower in MEMBERSHIP_MAP:
        project = MEMBERSHIP_MAP[name_lower]
    else:
        for ref_name, ref_project in MEMBERSHIP_MAP.items():
            if ref_name in purpose_lower:
                project = ref_project
                break

    category = "Services"
    if any(x in full_text for x in ["dalības", "biedru nauda", "membership"]) or any(x in project for x in ["Forever Young", "YF kids", "YF teens", "Youth"]):
        category = "Membership"
    elif "noma" in full_text:
        category = "Operational Expenses"
    elif "alga" in full_text:
        category = "Salaries"
        
    return category, project

# --- 5. AUTHENTICATION ---
if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None

if "code" in st.query_params:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    st.session_state.auth_creds = google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, code=st.query_params.get("code"))
    st.query_params.clear()
    st.rerun()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline")
    st.title("🏦 Bank to Sheets")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 6. MAIN APP ---
st.title("🏦 Bank Automator")
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        df_final = pd.DataFrame()
        
        # 1. Date
        df_final['Date'] = df_filtered[2]
        
        # 2. Name Surname & 3. Personal Code
        df_final['Name Surname'] = df_filtered[3].apply(lambda x: str(x).split('|')[0].strip())
        df_final['Personal Code'] = df_filtered[3].apply(lambda x: str(x).split('|')[1].strip() if '|' in str(x) else "")
        
        # 4. Konta numurs (IBAN) - Only fill if it starts with LV, else BLANK
        def get_iban(row):
            c1, c3 = str(row[1]).strip(), str(row[3]).strip()
            if c1.startswith("LV"): return c1
            # Search for IBAN pattern in the partner info field
            match = re.search(r'LV\d{2}[A-Z]{4}[A-Z0-9]{13}', c3)
            return match.group(0) if match else "" # Blank if no LV account found

        df_final['Konta numurs'] = df_filtered.apply(get_iban, axis=1)
        
        # 5. Bankas SWIFT - Scanner for BIC patterns
        def get_swift(row):
            for i in range(1, len(row)):
                val = str(row[i]).strip()
                if re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', val):
                    # Exclude the IBAN itself if it matches (IBAN starts with letters too)
                    if not val.startswith("LV"):
                        return val
            return ""
        df_final['Bankas SWIFT'] = df_filtered.apply(get_swift, axis=1)
        
        # 6. Purpose
        df_final['Purpose'] = df_filtered[4]
        
        # 7. K (KREDITS) & 8. D (DEBETS)
        amounts = pd.to_numeric(df_filtered[5].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        df_final['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K', 0.0)
        df_final['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D', 0.0)
        
        # 9. Category & 10. Project Name
        results = df_final.apply(process_row, axis=1)
        df_final['Category'] = [r[0] for r in results]
        df_final['Project Name'] = [r[1] for r in results]
        
        # 11. Commentary
        df_final['Commentary'] = ""

        if st.button("🚀 PROCESS & OPEN IN GOOGLE SHEETS"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Report')
                workbook = writer.book
                worksheet = writer.sheets['Report']
                
                # Setup Dropdowns
                opt_sheet = workbook.add_worksheet('Lists')
                for i, c in enumerate(CAT_OPTIONS): opt_sheet.write(i, 0, c)
                for i, p in enumerate(PROJ_OPTIONS): opt_sheet.write(i, 1, p)
                opt_sheet.hide()
                
                last_row = len(df_final) + 1
                # G = Purpose, H = K, I = D, J = Category, K = Project Name
                # Based on the column count: A(0), B(1), C(2), D(3), E(4), F(5), G(6), H(7), I(8), J(9), K(10)
                # Category is Col 9 (J), Project is Col 10 (K)
                worksheet.data_validation(f'I2:I{last_row}', {'validate': 'list', 'source': '=Lists!$A$1:$A$11'})
                worksheet.data_validation(f'J2:J{last_row}', {'validate': 'list', 'source': '=Lists!$B$1:$B$26'})

            output.seek(0)
            
            from google.oauth2.credentials import Credentials
            creds = Credentials(token=st.session_state.auth_creds['access_token'])
            service = build('drive', 'v3', credentials=creds)
            
            file_metadata = {'name': f"Bank_Report_{datetime.now().strftime('%Y%m%d_%H%M')}", 'mimeType': 'application/vnd.google-apps.spreadsheet'}
            media = MediaIoBaseUpload(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            
            st.success("Success!")
            st.link_button("📂 Open Google Sheet", file.get('webViewLink'))

    except Exception as e:
        st.error(f"Error: {e}")
