import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {"title": "🏦 Bank Automator", "upload": "Upload CSV", "cat": "📁 CATEGORY", "proj": "📁 PROJECT", "add_rule": "➕ Add Rule", "dl": "📥 Download", "drive": "☁️ Save to Google Drive"},
    "Latviešu": {"title": "🏦 Bankas automatizācija", "upload": "Augšupielādēt CSV", "cat": "📁 KATEGORIJA", "proj": "📁 PROJEKTS", "add_rule": "➕ Pievienot noteikumu", "dl": "📥 Lejupielādēt", "drive": "☁️ Saglabāt Drive"},
    "Русский": {"title": "🏦 Автоматизация", "upload": "Загрузить CSV", "cat": "📁 КАТЕГОРИЯ", "proj": "📁 ПРОЕКТ", "add_rule": "➕ Добавить правило", "dl": "📥 Скачать", "drive": "☁️ Сохранить на Drive"}
}

# --- 2. SESSION STATE (Rules) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE, RENFE', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas', 'active': True}
    ]
if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA', 'keywords': 'NVA', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
    ]

# --- 3. GOOGLE DRIVE FUNCTION ---
def upload_to_drive(file_data, file_name):
    try:
        creds_info = dict(st.secrets["google_drive"])
        # Fix for the PEM error:
        if "private_key" in creds_info:
            creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
            
        FOLDER_ID = creds_info["folder_id"]
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
        media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
        service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True
    except Exception as e:
        st.error(f"Google Drive Error: {e}")
        return False

# --- 4. CLASSIFICATION & PARSING ---
def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            for k in [x.strip().lower() for x in r['keywords'].split(',')]:
                if k and re.search(rf"\b{re.escape(k)}\b", text):
                    return r['name']
    return ""

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

# --- 5. UI SIDEBAR ---
st.set_page_config(page_title="Bank Automator", layout="wide")
lang = st.sidebar.selectbox("🌍", options=list(LANGUAGES.keys()))
t = LANGUAGES[lang]

with st.sidebar:
    st.header("Rules")
    for section, state_key in [(t["cat"], 'cat_rules'), (t["proj"], 'proj_rules')]:
        with st.expander(section):
            for i, rule in enumerate(st.session_state[state_key]):
                rule['active'] = st.checkbox("Active", value=rule['active'], key=f"{state_key}_on_{i}")
                rule['name'] = st.text_input("Name", value=rule['name'], key=f"{state_key}_n_{i}")
                rule['keywords'] = st.text_area("Keywords (comma separated)", value=rule['keywords'], key=f"{state_key}_k_{i}")
                st.divider()

# --- 6. MAIN LOGIC ---
st.title(t["title"])
uploaded_file = st.file_uploader(t["upload"], type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        mask = df_raw.stack().str.contains('Turnover|balance|Apgrozījums|Atlikums', case=False, na=False).unstack().any(axis=1)
        df_filtered = df_raw[~mask].copy()
        df_filtered = df_filtered[df_filtered[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)]

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        partner = df_filtered[3].apply(parse_partner).apply(pd.Series).fillna("")
        df_proc['Name Surname'] = partner['Name']
        df_proc['Personal Code'] = partner['P_Code']
        df_proc['Konta numurs'] = partner['Account']
        df_proc['Bankas SWIFT'] = partner['SWIFT']
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        raw_amt = df_filtered[5].astype(str).str.replace(',', '.', regex=False)
        num_amt = pd.to_numeric(raw_amt, errors='coerce')
        sign = df_filtered[7]
        df_proc['K (KREDIT)'] = num_amt.where(sign == 'K')
        df_proc['D (DEBIT)'] = num_amt.where(sign == 'D')
        
        text_for_search = df_filtered[3].fillna('') + " " + df_filtered[4].fillna('')
        df_proc['Category'] = text_for_search.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project'] = text_for_search.apply(lambda x: classify(x, st.session_state.proj_rules))

        # EXPORT
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_proc.to_excel(writer, index=False, sheet_name="Report")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(t["dl"], output.getvalue(), "Bank_Report.xlsx")
        with col2:
            if st.button(t["drive"]):
                output.seek(0)
                if upload_to_drive(output, "YoungFolks_Auto_Report.xlsx"):
                    st.success("✅ Saved to Drive!")
    except Exception as e:
        st.error(f"Error: {e}")
