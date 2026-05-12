import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re
import os

# --- 1. CONFIGURATION ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. LOAD MEMBERSHIP FROM TXT FILES ---
membership_files = {
    "YF Youth.txt": "YF Youth",
    "Forever Young.txt": "Forever Young",
    "YF kids.txt": "YF Kids",
    "YF teens.txt": "YF Teens"
}

membership_lookup = {}
for file_name, div_label in membership_files.items():
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                for line in f:
                    name_clean = line.strip().lower()
                    if name_clean and name_clean != "participant":
                        membership_lookup[name_clean] = div_label
        except Exception:
            pass

# --- 3. GOOGLE AUTHENTICATION FLOW ---
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
        st.error(f"Login error: {e}")

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("Bank to Sheets")
    st.link_button("Login with Google", auth_url)
    st.stop()

# --- 4. DROPDOWN OPTIONS ---
CAT_OPTIONS = ["Donations", "Erasmus+", "Help Ukraine", "Membership", "Operational Expenses", "Projects", "Salaries", "Services", "YE Travel"]
DIV_OPTIONS = ["Academic drawing", "BNI Artmen", "Comission", "E+ YE Voices in action", "English language", "Erasmus", "Erasmus Adult", "Forever Young", "German", "Internetbank", "JEF Europe", "Latvian language", "Madeira", "NVA / ESF", "Office Rent", "Office supplies", "Reimbursement", "Say it Ring", "Sense (design)", "Taxes", 'Valsts Kase projekts ESC30 "Youth', "Workshops", "YE GREEN REALITIES", "YF kids", "YF logistics", "YF Main", "YF Teens", "YF Youth"]
SUB_OPTIONS = ["APV GREEN REALITIES", "Brainring", "Christmas party", "Cinema production", "Coaching", "Creative jam event", "Italy?", "Reimbursement", "Sarunvalodas", "Speed Friending", "Umniy dom", "Winter camp"]

# --- 5. FILTERING LOGIC ---
def process_row(row):
    purpose = str(row['Purpose']).lower()
    name = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose} {name}"
    
    cat, div, sub = "", "YF Main", ""

    # Category Logic
    if any(kw in full_text for kw in ["ziedojum", "ziedot"]): cat = "Donations"
    elif any(kw in full_text for kw in ["alga", "stipendija", "autoratl"]): cat = "Salaries"
    elif "erasmus" in full_text or "reimbursement" in full_text: cat = "Erasmus+"
    elif any(kw in full_text for kw in ["biedru nauda", "dalības maksa", "dalibmaksa"]) or name in membership_lookup:
        cat = "Membership"
    elif any(kw in full_text for kw in ["bolt", "citybee", "noma", "komisija", "internetbank", "ikea", "depo"]):
        cat = "Operational Expenses"

    # Division Logic
    if name in membership_lookup:
        div = membership_lookup[name]
    elif "nva" in full_text: div = "NVA / ESF"
    elif "bolt" in full_text or "citybee" in full_text: div = "YF logistics"
    elif "internetbank" in full_text: div = "Internetbank"
    elif "komisija" in full_text or "kartes mēneša maksa" in full_text: div = "Comission"
    elif "latv" in full_text: div = "Latvian language"
    elif "angļu" in full_text or "english" in full_text: div = "English language"
    elif any(kw in full_text for kw in ["risunok", "gleznie", "akad"]): div = "Academic drawing"
    elif "madeira" in full_text: div = "Madeira"
    elif "podcast" in full_text or "300b" in full_text: div = 'Valsts Kase projekts ESC30 "Youth'
    elif any(kw in full_text for kw in ["lekcija", "workshop", "brein", "kouch", "coach"]): div = "Workshops"

    # Sub Logic
    if "brein" in full_text or "brain" in full_text: sub = "Brainring"
    elif "kouch" in full_text or "coach" in full_text: sub = "Coaching"
    elif "reimbursement" in full_text: sub = "Reimbursement"
    elif "nometne" in full_text or "camp" in full_text: sub = "Winter camp"
    if "sarunvalodas" in full_text in full_text: sub = "Sarunvalodas"

    return cat, div, sub

# --- 6. DRIVE EXPORT FUNCTION ---
def upload_and_convert(file_data, file_name):
    if st.session_state.auth_creds is None:
        st.error("Session expired. Please log in again.")
        return None
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials(token=st.session_state.auth_creds['access_token'])
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
        media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Upload Error: {e}")
        return None

# --- 7. UI AND MAIN APP ---
st.title("🚀 Bank Automator v3")
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip').fillna("")
        
        # 1. Filter for valid dates
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()
        
        # 2. NEW: Filter out Opening balance, Turnover, and Closing balance
        exclude_keywords = ["opening balance", "turnover", "closing balance", "sākuma atlikums", "apgrozījums", "beigu atlikums"]
        pattern = '|'.join(exclude_keywords)
        # We check column 4 (Purpose) for these keywords
        df_filtered = df_filtered[~df_filtered[4].astype(str).str.lower().str.contains(pattern, na=False)]

        def parse_partner_details(val):
            if not val: return "", "", "", ""
            parts = [p.strip() for p in str(val).split('|')]
            name = parts[0]
            p_code, iban, swift = "", "", ""
            for p in parts[1:]:
                clean = p.replace(" ", "").upper()
                if re.match(r'^\d{6}-\d{5}$', clean): p_code = clean
                elif len(clean) >= 15 and clean[0:2].isalpha(): iban = clean
                elif len(clean) in [8, 11] and clean[0:4].isalpha(): swift = clean
            return name, p_code, iban, swift

        parsed_data = df_filtered[3].apply(parse_partner_details)
        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = [x[0] for x in parsed_data]
        df_proc['Personal Code'] = [x[1] for x in parsed_data]
        df_proc['Konta numurs'] = [x[2] for x in parsed_data]
        df_proc['Bankas SWIFT'] = [x[3] for x in parsed_data]
        df_proc['Purpose'] = df_filtered[4]
        
        amounts_raw = pd.to_numeric(df_filtered[5].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        df_proc['K (KREDITS)'] = amounts_raw.where(df_filtered[7] == 'K').fillna(0.0)
        df_proc['D (DEBETS)'] = amounts_raw.where(df_filtered[7] == 'D').fillna(0.0)
        
        results = df_proc.apply(process_row, axis=1)
        df_proc['Category'], df_proc['Division'], df_proc['Sub'] = zip(*results)
        df_proc['Commentary'] = ""

        if st.button("CREATE GOOGLE SHEET"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankReport')
                workbook, worksheet = writer.book, writer.sheets['BankReport']
                
                data_sheet = workbook.add_worksheet('HiddenData')
                for i, v in enumerate(CAT_OPTIONS): data_sheet.write(i, 0, v)
                for i, v in enumerate(DIV_OPTIONS): data_sheet.write(i, 1, v)
                for i, v in enumerate(SUB_OPTIONS): data_sheet.write(i, 2, v)
                data_sheet.hide()

                last_r = len(df_proc) + 1
                worksheet.data_validation(f'I2:I{last_r}', {'validate': 'list', 'source': f'=HiddenData!$A$1:$A${len(CAT_OPTIONS)}'})
                worksheet.data_validation(f'J2:J{last_r}', {'validate': 'list', 'source': f'=HiddenData!$B$1:$B${len(DIV_OPTIONS)}'})
                worksheet.data_validation(f'K2:K{last_r}', {'validate': 'list', 'source': f'=HiddenData!$C$1:$C${len(SUB_OPTIONS)}'})
                
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(df_proc.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                
                worksheet.set_column('A:B', 12); worksheet.set_column('C:E', 25); worksheet.set_column('F:F', 40); worksheet.set_column('G:L', 18)

            output.seek(0)
            link = upload_and_convert(output, f"Bank_Export_{datetime.now().strftime('%Y-%m-%d')}")
            if link:
                st.markdown(f'<a href="{link}" target="_blank" style="text-decoration:none;"><div style="background-color:#0F9D58;color:white;padding:20px;border-radius:10px;text-align:center;font-size:18px;">📊 OPEN GOOGLE SHEET</div></a>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Processing error: {e}")
