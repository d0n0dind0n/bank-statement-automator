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

if "code" in st.query_params:
    try:
        code = st.query_params.get("code")
        google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
        token = google.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, code=code, include_client_id=True)
        st.session_state.auth_creds = token
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Autorizācijas kļūda: {e}")
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    authorization_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Young Folks Automator")
    st.link_button("🔑 Login with Google", authorization_url)
    st.stop()

# --- 3. IZVĒLŅU SARAKSTI (DROPDOWN OPTIONS) ---
CAT_OPTIONS = [
    "Select Category", "Membership YF kids", "Membership YF teens", "Membership Youth", 
    "Membership Forever Young", "Membership & Donations", "Salaries NVA", 
    "Salaries YF Main", "Salaries projekti", "Salaries nodokļi", 
    "YF Travel Japan", "YF Travel New York", "YF Travel Iceland", 
    "Logistics & Travel", "Services Office Rent", "Operational Expenses", 
    "Office supplies", "Rent & Admin"
]

PROJ_OPTIONS = [
    "Select Project", "NVA / ESF", "DiscoverEU (200B)", "Youth Identity Hub (400B)", 
    "Youth Podcast Station (300B)", "Youth Work Bus (500B)", 
    "Young Business (KA210)", "Zemlya (101239301)", "SHIFT (KA210)", 
    "Līderu Skola (GEAR UP!)", "Young Folks"
]

# --- 4. FUNKCIJAS ---
def upload_to_drive(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. LIETOTNES UI ---
st.set_page_config(layout="wide")
st.title("🏦 Bankas datu redaktors")

uploaded_file = st.file_uploader("Augšupielādēt Bankas CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        # Atlasām tikai rindas ar datumiem
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        # Sagatavojam galvenās kolonnas
        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = df_filtered[3].str.split('|').str[0].str.strip()
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        amounts = pd.to_numeric(df_filtered[5].str.replace(',', '.'), errors='coerce')
        df_proc['K (KREDITS)'] = amounts.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['D (DEBETS)'] = amounts.where(df_filtered[7] == 'D').fillna(0.0)
        
        # Pievienojam tukšas kolonnas priekš dropdown
        df_proc['Category'] = "Select Category"
        df_proc['Project Name'] = "Select Project"
        df_proc['Commentary'] = ""

        st.subheader("📝 Datu precizēšana")
        st.write("Izmanto nolaižamās izvēlnes, lai sakārtotu darījumus:")

        # --- DATU REDAKTORS AR DROPDOWN ---
        edited_df = st.data_editor(
            df_proc,
            column_config={
                "Date": st.column_config.Column("Datums", disabled=True, width="small"),
                "Name Surname": st.column_config.Column("Maksātājs/Saņēmējs", disabled=True, width="medium"),
                "Purpose": st.column_config.Column("Mērķis", disabled=True, width="large"),
                "K (KREDITS)": st.column_config.NumberColumn("Ienākumi (€)", format="%.2f", disabled=True),
                "D (DEBETS)": st.column_config.NumberColumn("Izdevumi (€)", format="%.2f", disabled=True),
                "Category": st.column_config.SelectboxColumn(
                    "Kategorija",
                    options=CAT_OPTIONS,
                    width="medium"
                ),
                "Project Name": st.column_config.SelectboxColumn(
                    "Projekts",
                    options=PROJ_OPTIONS,
                    width="medium"
                ),
                "Commentary": st.column_config.TextColumn("Komentārs", width="medium")
            },
            hide_index=True,
            use_container_width=True
        )

        st.divider()
        
        if st.button("🚀 SAGLABĀT UN ATVĒRT GOOGLE SHEETS"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                edited_df.to_excel(writer, index=False, sheet_name="Atskaite")
            
            output.seek(0)
            fname = f"Bank_Atskaite_{datetime.now().strftime('%d-%m_%H-%M')}.xlsx"
            with st.spinner("Augšupielādē..."):
                link = upload_to_drive(output, fname)
            
            if link:
                st.success("Fails veiksmīgi saglabāts!")
                st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                    <div style="background-color:#0F9D58;color:white;padding:20px;border-radius:10px;text-align:center;font-size:20px;font-weight:bold;">
                    🔗 SPIED ŠEIT, LAI ATVĒRTU SHEETU
                    </div></a>''', unsafe_allow_html=True)
                st.balloons()

    except Exception as e:
        st.error(f"Kļūda: {e}")
