import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime

# --- 1. KONFIGURĀCIJA ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. SESIJAS UN AUTORIZĀCIJA ---
if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None

# Apstrādājam atgriešanos no Google
if "code" in st.query_params:
    try:
        code = st.query_params.get("code")
        google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
        token = google.fetch_token(
            TOKEN_URL,
            client_secret=CLIENT_SECRET,
            code=code,
            include_client_id=True
        )
        st.session_state.auth_creds = token
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Autorizācijas kļūda: {e}")
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    authorization_url, state = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    
    st.title("🏦 Young Folks Automator")
    st.info("Lūdzu, autorizējieties ar Google, lai turpinātu.")
    st.link_button("🔑 Login with Google", authorization_url)
    st.stop()

# --- 3. KATEGORIJAS UN PROJEKTI ---
# (Iestatījumi paliek tie paši, kas iepriekš)
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
        {'name': 'SHIFT (KA210)', 'keywords': 'SHIFT, KA210', 'active': True}
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
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. LIETOTNES UI UN APSTRĀDE ---
st.title("🏦 Bankas datu apstrāde")
st.sidebar.button("Izlogoties", on_click=lambda: st.session_state.update({"auth_creds": None}))

uploaded_file = st.file_uploader("Augšupielādēt Bankas CSV failu", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8')
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = df_filtered[3].str.split('|').str[0].str.strip()
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        amounts = pd.to_numeric(df_filtered[5].str.replace(',', '.'), errors='coerce')
        df_proc['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K')
        df_proc['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D')
        
        txt_to_scan = df_filtered[3].fillna('') + " " + df_filtered[4].fillna('')
        df_proc['Category'] = txt_to_scan.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project Name'] = txt_to_scan.apply(lambda x: classify(x, st.session_state.proj_rules))

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_proc.to_excel(writer, index=False, sheet_name="Atskaite")
        
        st.divider()
        if st.button("🚀 Atvērt Google Sheets Online"):
            output.seek(0)
            fname = f"Bank_Report_{datetime.now().strftime('%d-%m_%H-%M')}.xlsx"
            link = upload_to_drive(output, fname)
            if link:
                st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#0F9D58;color:white;padding:15px;border-radius:8px;text-align:center;font-weight:bold;">🔗 ATVĒRT GOOGLE SHEETS</div></a>', unsafe_allow_html=True)
                st.balloons()
    except Exception as e:
        st.error(f"Kļūda: {e}")
