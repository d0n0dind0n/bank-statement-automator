import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# --- 1. VALODU IESTATĪJUMI ---
LANGUAGES = {
    "Latviešu": {
        "title": "🏦 Bankas datu apstrāde", 
        "upload": "Augšupielādēt CSV failu", 
        "cat": "📁 KATEGORIJAS", 
        "proj": "📁 PROJEKTI", 
        "add_rule": "➕ Pievienot noteikumu", 
        "dl": "📥 Lejupielādēt Excel", 
        "drive": "☁️ Saglabāt Google Drive"
    },
    "English": {
        "title": "🏦 Bank Automator", 
        "upload": "Upload CSV", 
        "cat": "📁 CATEGORY", 
        "proj": "📁 PROJECT", 
        "add_rule": "➕ Add Rule", 
        "dl": "📥 Download Excel", 
        "drive": "☁️ Save to Google Drive"
    }
}

# --- 2. KATEGORIJAS UN PROJEKTI ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Membership & Donations', 'keywords': 'Biedru maksa, Dalības maksa, Dalībmaksa, Ziedojums, Dalībasmaksa par mēnesi', 'active': True},
        {'name': 'Operational Expenses', 'keywords': 'Komisija, Internetbankas apkalpošanas maksa, Maksājumu uzdevuma apkalpošana', 'active': True},
        {'name': 'Logistics & Travel', 'keywords': 'PIRKUMS, Citybee, Bolt, Bolt.eu, Insularcar, Tallinn, Funchal', 'active': True},
        {'name': 'Rent & Admin', 'keywords': 'Telpu noma, Līgums, Ligums, Līgums no 19.08.25', 'active': True},
        {'name': 'Income from Services', 'keywords': 'Rēķins, Oplata zanjatija, Nodarbība, Lekcija, Sarunvalodas nodarbība', 'active': True},
        {'name': 'Equipment & Supplies', 'keywords': 'IKEA, Latvia, Pirkums', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA / ESF', 'keywords': 'NVA, Nodarbinatibas valsts agentura, ESF PIN 4.3.3.2/1/24/I/002, VSAOI, Lig.Nr.8.3-8.1/130-2025', 'active': True},
        {'name': 'Young Business (KA210)', 'keywords': 'Young Business, KA210', 'active': True},
        {'name': 'Zemlya (101239301)', 'keywords': 'Zemlya, 101239301', 'active': True},
        {'name': 'SHIFT (KA210)', 'keywords': 'SHIFT, KA210-YOU-8BA0488F', 'active': True},
        {'name': 'Līderu Skola (GEAR UP!)', 'keywords': 'Lapas, GEAR UP, Līderu Skola', 'active': True},
        {'name': 'DiscoverEU (200B)', 'keywords': 'DiscoverEU, My Europ too, 200B', 'active': True},
        {'name': 'Youth Identity Hub (400B)', 'keywords': 'Youth Identity Hub, 400B', 'active': True},
        {'name': 'Youth Podcast Station (300B)', 'keywords': 'Youth Podcast Station, ESC30, 300B', 'active': True},
        {'name': 'Youth Work Bus (500B)', 'keywords': 'Youth Work Bus, ESC30, 500B', 'active': True},
        {'name': 'Erasmus+ General', 'keywords': 'Erasmus+, Erasmus plus', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
    ]

# --- 3. GOOGLE DRIVE FUNKCIJA ---
def upload_to_drive(file_data, file_name):
    try:
        creds_info = dict(st.secrets["google_drive"])
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

# --- 4. DATU APSTRĀDE ---
def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            keys = [k.strip().lower() for k in r['keywords'].split(',')]
            for k in keys:
                if k and k in text: # Izmantojam vienkāršāku meklēšanu projektu kodiem
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

# --- 5. UI ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")
lang = st.sidebar.selectbox("Valoda / Language", options=list(LANGUAGES.keys()))
t = LANGUAGES[lang]

with st.sidebar:
    st.header("Noteikumi / Rules")
    with st.expander(t["cat"]):
        for i, rule in enumerate(st.session_state.cat_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"c_on_{i}")
            rule['keywords'] = st.text_area(f"Atslēgvārdi ({rule['name']})", value=rule['keywords'], key=f"c_k_{i}")
    with st.expander(t["proj"]):
        for i, rule in enumerate(st.session_state.proj_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"p_on_{i}")
            rule['keywords'] = st.text_area(f"Atslēgvārdi ({rule['name']})", value=rule['keywords'], key=f"p_k_{i}")

# --- 6. APSTRĀDE ---
st.title(t["title"])
file = st.file_uploader(t["upload"], type="csv")

if file:
    try:
        df_raw = pd.read_csv(file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        mask = df_raw.stack().str.contains('Turnover|balance|Apgrozījums|Atlikums', case=False, na=False).unstack().any(axis=1)
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
        
        df_proc['K (KREDITS)'] = num_amount.where(sign_col == 'K')
        df_proc['D (DEBETS)'] = num_amount.where(sign_col == 'D')
        
        search_txt = df_filtered[3].fillna('') + " " + df_filtered[4].fillna('')
        df_proc['Category'] = search_txt.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project Name'] = search_txt.apply(lambda x: classify(x, st.session_state.proj_rules))
        df_proc['Commentary'] = ""

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'K (KREDITS)', 'D (DEBETS)', 'Category', 'Project Name', 'Commentary']
            df_proc.sort_values(by='Date')[cols].to_excel(writer, index=False, sheet_name="Atskaite")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(t["dl"], output.getvalue(), "YoungFolks_Atskaite.xlsx")
        with col2:
            if st.button(t["drive"]):
                output.seek(0)
                if upload_to_drive(output, "Automatiska_Bankas_Atskaite.xlsx"):
                    st.success("✅ Saglabāts Google Drive!")
    except Exception as e:
        st.error(f"Kļūda: {e}")
