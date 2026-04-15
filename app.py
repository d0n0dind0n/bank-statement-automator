import streamlit as st
import pandas as pd
import io
import re
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import Flow
from datetime import datetime

# --- 1. KONFIGURĀCIJA UN OAUTH IESTATĪJUMI ---
# Maini šo adresi uz savu aktuālo lietotnes URL!
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"

CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
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

# Apstrādājam atgriešanos no Google (Auth Code)
params = st.query_params
if "code" in params and st.session_state.auth_creds is None:
    try:
        flow = get_flow()
        flow.fetch_token(code=params["code"])
        st.session_state.auth_creds = flow.credentials
        st.query_params.clear()  # Attīra URL no izmantotā koda
        st.rerun()
    except Exception as e:
        st.error("Pieteikšanās sesija beigusies. Lūdzu, mēģiniet vēlreiz.")
        st.query_params.clear()

# Ja lietotājs nav ielogojies, rādām pogu
if st.session_state.auth_creds is None:
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
    st.title("🏦 Young Folks Bank Automator")
    st.info("Lai turpinātu, lūdzu, ielogojieties ar savu Google kontu.")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 3. KATEGORIJAS UN PROJEKTU NOTEIKUMI ---
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
        {'name': 'Logistics & Travel', 'keywords': 'PIRKUMS, Citybee, Bolt, Bolt.eu', 'active': True},
        {'name': 'Services Office Rent', 'keywords': 'Office Rent, Biroja noma', 'active': True},
        {'name': 'Operational Expenses', 'keywords': 'Komisija, Internetbankas apkalpošana', 'active': True},
        {'name': 'Office supplies', 'keywords': 'IKEA, Latvia, Kanceleja', 'active': True},
        {'name': 'Rent & Admin', 'keywords': 'Telpu noma, Līgums, Admin', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA / ESF', 'keywords': 'NVA, ESF, 4.3.3.2/1/24/I/002, 8.3-8.1/130-2025', 'active': True},
        {'name': 'DiscoverEU (200B)', 'keywords': '200B, DiscoverEU, My Europ too', 'active': True},
        {'name': 'Youth Identity Hub (400B)', 'keywords': '400B, Identity Hub', 'active': True},
        {'name': 'Youth Podcast Station (300B)', 'keywords': '300B, Podcast', 'active': True},
        {'name': 'Youth Work Bus (500B)', 'keywords': '500B, Work Bus', 'active': True},
        {'name': 'Young Business (KA210)', 'keywords': 'Young Business, KA210', 'active': True},
        {'name': 'Zemlya (101239301)', 'keywords': '101239301, Zemlya', 'active': True},
        {'name': 'SHIFT (KA210)', 'keywords': 'SHIFT, KA210', 'active': True},
        {'name': 'Līderu Skola (GEAR UP!)', 'keywords': 'Lapas, GEAR UP, Līderu Skola', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
    ]

# --- 4. PALĪGFUNKCIJAS ---
def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            keys = [k.strip().lower() for k in r['keywords'].split(',')]
            for k in keys:
                if k and k in text:
                    return r['name']
    return ""

def upload_to_drive(file_data, file_name):
    try:
        service = build('drive', 'v3', credentials=st.session_state.auth_creds)
        file_metadata = {'name': file_name}
        media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Google Drive kļūda: {e}")
        return None

# --- 5. LIETOTNES UI UN APSTRĀDE ---
st.title("🏦 Young Folks Bank Automator")
st.sidebar.button("Atslēgties (Logout)", on_click=lambda: st.session_state.update({"auth_creds": None}))

with st.sidebar:
    st.header("Noteikumi / Rules")
    with st.expander("Kategorijas"):
        for i, rule in enumerate(st.session_state.cat_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"c_on_{i}")
            rule['keywords'] = st.text_area(f"Atslēgvārdi ({rule['name']})", value=rule['keywords'], key=f"c_k_{i}", height=60)
    with st.expander("Projekti"):
        for i, rule in enumerate(st.session_state.proj_rules):
            rule['active'] = st.checkbox(f"On: {rule['name']}", value=rule['active'], key=f"p_on_{i}")
            rule['keywords'] = st.text_area(f"Atslēgvārdi ({rule['name']})", value=rule['keywords'], key=f"p_k_{i}", height=60)

file_upload = st.file_uploader("Augšupielādēt Bankas CSV", type="csv")

if file_upload:
    try:
        df_raw = pd.read_csv(file_upload, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        mask = df_raw.stack().str.contains('Turnover|balance|Apgrozījums|Atlikums', case=False, na=False).unstack().any(axis=1)
        df_filtered = df_raw[~mask].copy()
        df_filtered = df_filtered[df_filtered[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)]

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = df_filtered[3].str.split('|').str[0].str.strip()
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

        # Izveidojam Excel atmiņā
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name="Atskaite")
        excel_data = output.getvalue()

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Lejupielādēt datorā", excel_data, f"YF_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")
        with col2:
            if st.button("🚀 SAGLABĀT UN ATVĒRT GOOGLE SHEETS"):
                output.seek(0)
                web_link = upload_to_drive(output, f"Report_{datetime.now().strftime('%d-%m_%H-%M')}.xlsx")
                if web_link:
                    st.markdown(f'''<a href="{web_link}" target="_blank" style="text-decoration:none;">
                        <div style="background-color:#0F9D58;color:white;padding:15px;border-radius:8px;text-align:center;font-weight:bold;">
                        🔗 SPIED ŠEIT, LAI ATVĒRTU ONLINE
                        </div></a>''', unsafe_allow_html=True)
                    st.balloons()

    except Exception as e:
        st.error(f"Kļūda datu apstrādē: {e}")
