import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from datetime import datetime

# --- 1. VALODU IESTATĪJUMI ---
LANGUAGES = {
    "Latviešu": {
        "title": "🏦 Bankas datu apstrāde", 
        "upload": "Augšupielādēt CSV failu", 
        "cat": "📁 KATEGORIJAS", 
        "proj": "📁 PROJEKTI", 
        "dl": "📥 Lejupielādēt datorā", 
        "sheets": "🚀 Atvērt Google Sheets (Online)"
    },
    "English": {
        "title": "🏦 Bank Automator", 
        "upload": "Upload CSV", 
        "cat": "📁 CATEGORY", 
        "proj": "📁 PROJECT", 
        "dl": "📥 Download to PC", 
        "sheets": "🚀 Open in Google Sheets (Online)"
    }
}

# --- 2. KATEGORIJAS UN PROJEKTI ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Membership YF kids', 'keywords': 'YF kids, Biedra nauda kids', 'active': True},
        {'name': 'Membership YF teens', 'keywords': 'YF teens, Biedra nauda teens', 'active': True},
        {'name': 'Membership Youth', 'keywords': 'Youth membership, Jauniešu biedra nauda', 'active': True},
        {'name': 'Membership Forever Young', 'keywords': 'Forever Young membership', 'active': True},
        {'name': 'Membership & Donations', 'keywords': 'Biedru maksa, Dalības maksa, Ziedojums', 'active': True},
        {'name': 'Salaries NVA', 'keywords': 'Alga NVA, NVA alga', 'active': True},
        {'name': 'Salaries YF Main', 'keywords': 'Alga YF, YF alga', 'active': True},
        {'name': 'Salaries projekti', 'keywords': 'Alga projekts, Projekta alga', 'active': True},
        {'name': 'Salaries nodokļi', 'keywords': 'VSAOI, IIN, Nodokļi alga', 'active': True},
        {'name': 'YF Travel Japan', 'keywords': 'Japan, Japāna, Tokija', 'active': True},
        {'name': 'YF Travel New York', 'keywords': 'New York, Ņujorka, NYC', 'active': True},
        {'name': 'YF Travel Iceland', 'keywords': 'Iceland, Islande, Reikjavika', 'active': True},
        {'name': 'Logistics & Travel', 'keywords': 'PIRKUMS, Citybee, Bolt, Bolt.eu, Insularcar, Tallinn, Funchal', 'active': True},
        {'name': 'Services Office Rent', 'keywords': 'Office Rent, Biroja noma', 'active': True},
        {'name': 'Operational Expenses', 'keywords': 'Komisija, Internetbankas apkalpošanas maksa', 'active': True},
        {'name': 'Office supplies', 'keywords': 'IKEA, Latvia, Kanceleja', 'active': True},
        {'name': 'Rent & Admin', 'keywords': 'Telpu noma, Līgums, Admin', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA / ESF', 'keywords': 'NVA, ESF, 4.3.3.2/1/24/I/002, 8.3-8.1/130-2025', 'active': True},
        {'name': 'DiscoverEU (200B)', 'keywords': 'DiscoverEU, My Europ too, 200B', 'active': True},
        {'name': 'Youth Identity Hub (400B)', 'keywords': 'Youth Identity Hub, 400B', 'active': True},
        {'name': 'Youth Podcast Station (300B)', 'keywords': 'Youth Podcast Station, 300B', 'active': True},
        {'name': 'Youth Work Bus (500B)', 'keywords': 'Youth Work Bus, 500B', 'active': True},
        {'name': 'Young Business (KA210)', 'keywords': 'Young Business, KA210', 'active': True},
        {'name': 'Zemlya (101239301)', 'keywords': 'Zemlya, 101239301', 'active': True},
        {'name': 'SHIFT (KA210)', 'keywords': 'SHIFT, KA210', 'active': True},
        {'name': 'Līderu Skola (GEAR UP!)', 'keywords': 'Lapas, GEAR UP, Līderu Skola', 'active': True}
    ]

# --- 3. HELPER FUNCTIONS ---
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
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Google Drive Error: {e}")
        return None

def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            keys = [k.strip().lower() for k in r['keywords'].split(',')]
            for k in keys:
                if k and k in text:
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

# --- 4. MAIN UI ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")
lang = st.sidebar.selectbox("🌍", options=list(LANGUAGES.keys()))
t = LANGUAGES[lang]

with st.sidebar:
    st.header("Rules")
    with st.expander(t["cat"]):
        for i, rule in enumerate(st.session_state.cat_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"c_on_{i}")
            rule['keywords'] = st.text_area(f"Keys ({rule['name']})", value=rule['keywords'], key=f"c_k_{i}", height=60)
    with st.expander(t["proj"]):
        for i, rule in enumerate(st.session_state.proj_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"p_on_{i}")
            rule['keywords'] = st.text_area(f"Keys ({rule['name']})", value=rule['keywords'], key=f"p_k_{i}", height=60)

# --- 5. PROCESSING LOGIC ---
st.title(t["title"])
file_upload = st.file_uploader(t["upload"], type="csv")

if file_upload:
    try:
        df_raw = pd.read_csv(file_upload, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        mask = df_raw.stack().str.contains('Turnover|balance|Apgrozījums|Atlikums', case=False, na=False).unstack().any(axis=1)
        df_filtered = df_raw[~mask].copy()
        df_filtered = df_filtered[df_filtered[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)]

        # --- THIS DEFINES df_proc ---
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
        df_proc['K (KREDITS)'] = num_amt.where(sign == 'K')
        df_proc['D (DEBETS)'] = num_amt.where(sign == 'D')
        
        search_txt = df_filtered[3].fillna('') + " " + df_filtered[4].fillna('')
        df_proc['Category'] = search_txt.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project Name'] = search_txt.apply(lambda x: classify(x, st.session_state.proj_rules))
        df_proc['Commentary'] = ""
        
        df_final = df_proc.sort_values(by='Date')

        # Create Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'K (KREDITS)', 'D (DEBETS)', 'Category', 'Project Name', 'Commentary']
            df_final[cols].to_excel(writer, index=False, sheet_name="Report")
        excel_data = output.getvalue()

        # --- DISPLAY BUTTONS ---
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(t["dl"], excel_data, f"YF_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")
        with c2:
            if st.button(t["sheets"]):
                output.seek(0)
                web_link = upload_to_drive(output, f"Report_{datetime.now().strftime('%d-%m_%H-%M')}.xlsx")
                if web_link:
                    st.markdown(f'<a href="{web_link}" target="_blank" style="text-decoration:none;"><div style="background-color:#0F9D58;color:white;padding:15px;border-radius:8px;text-align:center;font-weight:bold;">🔗 OPEN IN GOOGLE SHEETS</div></a>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
