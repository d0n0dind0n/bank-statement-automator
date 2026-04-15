import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import Flow
from datetime import datetime

# --- 1. KONFIGURĀCIJA ---
# PRECIZS URL: Šim ir jāsakrīt ar Google Cloud Console iestatījumiem
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"

# Ielādējam datus no Streamlit Secrets
try:
    CLIENT_ID = st.secrets["google_oauth"]["client_id"]
    CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
except KeyError:
    st.error("Kļūda: Streamlit Secrets nav konfigurēti 'google_oauth' dati!")
    st.stop()

SCOPES = ['https://www.googleapis.com/auth/drive.file']

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

# --- 2. SESIJAS STĀVOKLIS UN PIETEIKŠANĀS ---
if 'auth_creds' not in st.session_state:
    st.session_state.auth_creds = None

# Apstrādājam ienākošo autorizācijas kodu no Google
if "code" in st.query_params:
    try:
        auth_code = st.query_params.get("code")
        flow = get_flow()
        flow.fetch_token(code=auth_code)
        st.session_state.auth_creds = flow.credentials
        # Iztīrām URL, lai novērstu koda atkārtotu izmantošanu
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Autorizācijas kļūda: {e}")
        st.query_params.clear()

# Ja lietotājs nav ielogojies, apturam visu un rādām pogu
if st.session_state.auth_creds is None:
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    st.title("🏦 Young Folks Bank Automator")
    st.info("Lai saglabātu atskaites Google Drive, lūdzu, autorizējieties.")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 3. KATEGORIJAS UN PROJEKTU NOTEIKUMI ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Membership & Donations', 'keywords': 'Biedru maksa, Dalības maksa, Ziedojums', 'active': True},
        {'name': 'Salaries & Taxes', 'keywords': 'Alga, VSAOI, IIN, Nodokļi', 'active': True},
        {'name': 'Logistics & Travel', 'keywords': 'Citybee, Bolt, airBaltic, Pirkums', 'active': True},
        {'name': 'Operational Expenses', 'keywords': 'Komisija, Apkalpošana', 'active': True},
        {'name': 'Rent & Admin', 'keywords': 'Telpu noma, Līgums', 'active': True},
        {'name': 'Equipment & Supplies', 'keywords': 'IKEA, Latvia, Pirkums', 'active': True}
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
    try:
        service = build('drive', 'v3', credentials=st.session_state.auth_creds)
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Google Drive kļūda: {e}")
        return None

# --- 5. LIETOTNES UI UN APSTRĀDE ---
st.title("🏦 Bankas datu apstrāde")
st.sidebar.button("Izlogoties", on_click=lambda: st.session_state.update({"auth_creds": None}))

with st.sidebar:
    st.header("Noteikumu rediģēšana")
    with st.expander("📁 KATEGORIJAS"):
        for i, rule in enumerate(st.session_state.cat_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"c_{i}")
            rule['keywords'] = st.text_area(f"Atslēgvārdi ({rule['name']})", value=rule['keywords'], key=f"ck_{i}", height=60)
    with st.expander("📁 PROJEKTI"):
        for i, rule in enumerate(st.session_state.proj_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"p_{i}")
            rule['keywords'] = st.text_area(f"Atslēgvārdi ({rule['name']})", value=rule['keywords'], key=f"pk_{i}", height=60)

uploaded_file = st.file_uploader("Augšupielādēt Bankas CSV failu", type="csv")

if uploaded_file:
    try:
        # Apstrādes loģika
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
        df_proc['Commentary'] = ""

        # Excel ģenerēšana atmiņā
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_proc.to_excel(writer, index=False, sheet_name="Bankas_Atskaite")
        excel_data = output.getvalue()

        st.divider()
        c1, c2 = st.columns(2)
        
        with c1:
            st.download_button("📥 Lejupielādēt (.xlsx)", excel_data, f"Report_{datetime.now().strftime('%Y%m%d')}.xlsx")
            
        with c2:
            if st.button("🚀 Atvērt Google Sheets Online"):
                with st.spinner("Augšupielādē..."):
                    output.seek(0)
                    fname = f"Bank_Report_{datetime.now().strftime('%d-%m_%H-%M')}.xlsx"
                    link = upload_to_drive(output, fname)
                    if link:
                        st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                            <div style="background-color:#0F9D58;color:white;padding:15px;border-radius:8px;text-align:center;font-weight:bold;">
                            👉 SPIED ŠEIT, LAI ATVĒRTU SHEETU
                            </div></a>''', unsafe_allow_html=True)
                        st.balloons()
    except Exception as e:
        st.error(f"Kļūda apstrādē: {e}")
