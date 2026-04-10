import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {"title": "🏦 Bank Automator", "upload": "Upload CSV", "dl": "📥 Download Excel", "drive": "☁️ Save to Google Drive"},
    "Latviešu": {"title": "🏦 Bankas automatizācija", "upload": "Augšupielādēt CSV", "dl": "📥 Lejupielādēt", "drive": "☁️ Saglabāt Google Drive"},
    "Русский": {"title": "🏦 Автоматизация", "upload": "Загрузить CSV", "dl": "📥 Скачать Excel", "drive": "☁️ Сохранить на Google Drive"}
}

# --- 2. GOOGLE DRIVE UPLOAD FUNCTION ---
def upload_to_drive(file_data, file_name):
    try:
        # Pulls from st.secrets (secrets.toml locally or Dashboard on web)
        creds_info = st.secrets["google_drive"]
        FOLDER_ID = creds_info["folder_id"]
        SCOPES = ['https://www.googleapis.com/auth/drive.file']

        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
        media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
    except Exception as e:
        st.error(f"Google Drive Error: {e}")
        return None

# --- 3. HELPER FUNCTIONS ---
def parse_partner(val):
    if pd.isna(val) or str(val).strip() == "":
        return {"Name": "", "P_Code": "", "Account": "", "SWIFT": ""}
    val = str(val).replace('|', ' ')
    iban = re.search(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', val)
    p_code = re.search(r'\d{6}-\d{5}', val)
    swift = re.search(r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b', val)
    
    clean_name = val
    if iban: clean_name = clean_name.replace(iban.group(), "")
    if p_code: clean_name = clean_name.replace(p_code.group(), "")
    if swift: clean_name = clean_name.replace(swift.group(), "")
    
    return {
        "Name": re.sub(r'\s+', ' ', clean_name).strip().strip(','),
        "P_Code": p_code.group() if p_code else "",
        "Account": iban.group() if iban else "",
        "SWIFT": swift.group() if swift else ""
    }

# --- 4. MAIN APP ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")
lang = st.sidebar.selectbox("🌍", options=list(LANGUAGES.keys()))
t = LANGUAGES[lang]

st.title(t["title"])
file = st.file_uploader(t["upload"], type="csv")

if file:
    try:
        df_raw = pd.read_csv(file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        
        # Clean data (remove turnovers)
        mask = df_raw.stack().str.contains('Turnover|balance|Apgrozījums', case=False, na=False).unstack().any(axis=1)
        df_filtered = df_raw[~mask].copy()
        df_filtered = df_filtered[df_filtered[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)]

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        
        partner_data = df_filtered[3].apply(parse_partner).apply(pd.Series).fillna("")
        df_proc['Name Surname'] = partner_data['Name']
        df_proc['Personal Code'] = partner_data['P_Code']
        df_proc['Konta numurs'] = partner_data['Account']
        df_proc['Bankas SWIFT'] = partner_data['SWIFT']
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        raw_amount = df_filtered[5].astype(str).str.replace(',', '.', regex=False)
        num_amount = pd.to_numeric(raw_amount, errors='coerce')
        sign_col = df_filtered[7]
        
        df_proc['K (KREDIT)'] = num_amount.where(sign_col == 'K')
        df_proc['D (DEBIT)'] = num_amount.where(sign_col == 'D')
        
        # Export logic
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'K (KREDIT)', 'D (DEBIT)']
            df_proc.sort_values(by='Date').to_excel(writer, index=False, sheet_name="Full Report")

        # --- DOWNLOAD & SAVE BUTTONS ---
        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.download_button(t["dl"], output.getvalue(), "Report.xlsx")
            
        with c2:
            if st.button(t["drive"]):
                output.seek(0) # Reset buffer for Google
                with st.spinner("Uploading..."):
                    file_id = upload_to_drive(output, "YoungFolks_Auto_Report.xlsx")
                    if file_id:
                        st.success(f"✅ Saved! ID: {file_id}")

    except Exception as e:
        st.error(f"Error: {e}")
