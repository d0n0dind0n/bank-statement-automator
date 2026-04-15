import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import Flow
from datetime import datetime

# --- 1. KONFIGURĀCIJA ---
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
# ŠEIT ieraksti savas lietotnes adresi (beidzas ar .streamlit.app/)
REDIRECT_URI = "https://bank-automator.streamlit.app/"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. AUTENTIFIKĀCIJA ---
def get_flow():
    return Flow.from_client_config(
        {"web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None

# Atgriešanās no Google Login
params = st.query_params
if "code" in params and st.session_state.auth_creds is None:
    flow = get_flow()
    flow.fetch_token(code=params["code"])
    st.session_state.auth_creds = flow.credentials
    st.query_params.clear()

if st.session_state.auth_creds is None:
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    st.title("🏦 Young Folks Bank Automator")
    st.write("Lūdzu, ielogojieties, lai saglabātu atskaites Drive bez lejupielādes.")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 3. KATEGORIJAS UN PROJEKTI ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Membership & Donations', 'keywords': 'Biedru maksa, Dalības maksa, Ziedojums', 'active': True},
        {'name': 'Salaries & Taxes', 'keywords': 'Alga, VSAOI, IIN, Nodokļi', 'active': True},
        {'name': 'Logistics & Travel', 'keywords': 'Citybee, Bolt, airBaltic, Pirkums', 'active': True},
        {'name': 'Operational Expenses', 'keywords': 'Komisija, Apkalpošana', 'active': True},
        {'name': 'Rent & Admin', 'keywords': 'Telpu noma, Līgums', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA / ESF', 'keywords': 'NVA, ESF, 4.3.3.2/1/24/I/002, 8.3-8.1/130-2025', 'active': True},
        {'name': 'DiscoverEU (200B)', 'keywords': '200B, DiscoverEU', 'active': True},
        {'name': 'Youth Identity Hub (400B)', 'keywords': '400B, Identity Hub', 'active': True},
        {'name': 'SHIFT (KA210)', 'keywords': 'SHIFT, KA210', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
    ]

# --- 4. FUNKCIJAS ---
def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            for k in [x.strip().lower() for x in r['keywords'].split(',')]:
                if k and k in text: return r['name']
    return ""

def upload_to_drive(file_data, file_name):
    service = build('drive', 'v3', credentials=st.session_state.auth_creds)
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. LIETOTNES DARBĪBA ---
st.title("🏦 Apstrāde uzsākta")
st.sidebar.button("Log Out", on_click=lambda: st.session_state.update({"auth_creds": None}))

uploaded_file = st.file_uploader("Augšupielādēt Bankas CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8')
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name'] = df_filtered[3].str.split('|').str[0].str.strip()
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        amounts = pd.to_numeric(df_filtered[5].str.replace(',', '.'), errors='coerce')
        df_proc['Credit'] = amounts.where(df_filtered[7] == 'K')
        df_proc['Debit'] = amounts.where(df_filtered[7] == 'D')
        
        txt = df_filtered[3].fillna('') + " " + df_filtered[4].fillna('')
        df_proc['Category'] = txt.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project'] = txt.apply(lambda x: classify(x, st.session_state.proj_rules))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_proc.to_excel(writer, index=False, sheet_name="Atskaite")
        
        st.divider()
        if st.button("🚀 SAGLABĀT UN ATVĒRT GOOGLE SHEETS"):
            output.seek(0)
            fname = f"Atskaite_{datetime.now().strftime('%d-%m_%H-%M')}.xlsx"
            link = upload_to_drive(output, fname)
            if link:
                st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                    <div style="background-color:#0F9D58;color:white;padding:20px;border-radius:10px;text-align:center;font-size:20px;font-weight:bold;">
                    🔗 SPIED ŠEIT, LAI ATVĒRTU ONLINE
                    </div></a>''', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Kļūda apstrādē: {e}")
