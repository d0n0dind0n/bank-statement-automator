import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re

# --- 1. CONFIGURATION ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- 2. AUTHENTICATION ---
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
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Bank to Google Sheets")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 3. UPDATED CONFIGURATION ---
CAT_OPTIONS = [
    "Membership", "YF Logistics", "YF Travel", "Erasmus+",
    "Services", "Salaries", "Donations", "Operational Expenses",
    "Office supplies", "Rent & Admin", "Single payment"
]

PROJ_OPTIONS = [
    "projekti", "NVA / ESF", "Erasmus+ KA210 project \"Young Business\"",
    "Erasmus+ project Project 101239301 \"Zemlya\"", "Erasmus+ KA210 \"SHIFT\"",
    "projekts Lapas GEAR UP! \"Līderu Skola\"",
    "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)",
    "Valsts Kase projekts KA210 \"Youth Identiy Hub\" (400B)",
    "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)",
    "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)",
    "Erasmus+ General", "Erasmus", "nodokļi", "YF Main", "YF kids", "YF teens",
    "Youth", "Forever Young", "New York", "Iceland", "Japan",
    "Say it Ring", "Sense (design)", "Latvian language", "English language",
    "Workshops", "Office Rent", "Animators"
]

CAT_FILTER = {
    "dalības": "Membership", "biedru nauda": "Membership", "dalībmaksa": "Membership",
    "abonements": "Membership", "biedriba nauda": "Membership", "yf2024": "Membership", 
    "fy": "Membership", "dalibmaksa par klubu": "Membership", "biedra nauda": "Membership",
    "ziedojums": "Donations", "ziedojumu": "Donations",
    "stipendija": "Salaries", "alga": "Salaries", "nodokli": "Salaries",
    "autoratlīdzības": "Salaries", "autoratlidzibas": "Salaries", "līgums": "Salaries",
    "ligums nva": "Salaries",
    "bolt": "YF Logistics", "wolt": "YF Logistics", "citybee": "YF Logistics",
    "pirkums": "YF Logistics", "travel": "YF Travel", "japan": "YF Travel",
    "iceland": "YF Travel", "lekcija": "Services", "latviesu": "Services",
    "english": "Services", "valoda": "Services", "rent": "Rent & Admin",
    "noma": "Rent & Admin", "komisija": "Operational Expenses",
    "apkalpošanas": "Operational Expenses", "tele2": "Office supplies",
    "reimbursement": "Erasmus+", "erasmus": "Erasmus+"
}

PROJ_FILTER = {
    "nva": "NVA / ESF", "erasmus": "Erasmus",
    "200b": "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)",
    "300b": "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)",
    "400b": "Valsts Kase projekts KA210 \"Youth Identiy Hub\" (400B)",
    "500b": "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)",
    "zemlya": "Erasmus+ project Project 101239301 \"Zemlya\"",
    "shift": "Erasmus+ KA210 \"SHIFT\"",
    "young business": "Erasmus+ KA210 project \"Young Business\"",
    "gear up": "projekts Lapas GEAR UP! \"Līderu Skola\"",
    "līderu skola": "projekts Lapas GEAR UP! \"Līderu Skola\"",
    "nodokļi": "nodokļi", "kids": "YF kids", "new york": "New York",
    "iceland": "Iceland", "japan": "Japan", "gredzen": "Say it Ring",
    "ring": "Say it Ring", "fy": "Forever Young", "forever": "Forever Young",
    "sense": "Sense (design)", "latviesu": "Latvian language",
    "english": "English language", "meistarklase": "Workshops",
    "workshops": "Workshops", "noma": "Office Rent", "animators": "Animators",
    "bolt": "projekti", "wolt": "projekti"
}

# --- 4. DRIVE UPLOAD ---
def upload_and_convert(file_data, file_name):
    from google.oauth2.credentials import Credentials
    creds = Credentials(token=st.session_state.auth_creds['access_token'])
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': file_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'}
    media = MediaIoBaseUpload(file_data, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    return file.get('webViewLink')

# --- 5. DATA PROCESSING ---
st.title("🏦 Bank Automator")
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()

        try:
            first_date_str = df_filtered.iloc[0, 2] 
            dt_obj = datetime.strptime(first_date_str, "%d.%m.%Y")
            sheet_name = dt_obj.strftime("%B_%Y")
        except:
            sheet_name = f"Bank_Export_{datetime.now().strftime('%Y-%m-%d')}"

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
        
        # --- ENHANCED LOGIC ---
        def get_project_name(row):
            purpose_lower = str(row['Purpose']).lower()
            amt = max(row['K (KREDITS)'], row['D (DEBETS)'])
            
            # Check for Membership amount logic first
            text_for_cat = (purpose_lower + " " + str(row['Name Surname']).lower())
            is_membership = any(kw in text_for_cat for kw in ["dalības", "biedru nauda", "dalībmaksa", "biedriba nauda", "yf2024", "fy", "biedra nauda"])
            
            if is_membership:
                if amt in [20, 30]:
                    return "Forever Young"
                elif amt in [15, 25]:
                    return "YF teens"
            
            # General keyword search for projects
            for key, proj in PROJ_FILTER.items():
                if key in purpose_lower:
                    return proj
                    
            return "YF Main"

        def get_category(row, project_name):
            # Requirement: If 'Say it Ring' is used, put it in 'Services'
            if project_name == "Say it Ring":
                return "Services"
                
            text = (str(row['Purpose']) + " " + str(row['Name Surname'])).lower()
            for kw, cat in CAT_FILTER.items():
                if kw.lower() in text: return cat
            return ""

        # Processing columns in order of dependency
        df_proc['Project Name'] = df_proc.apply(get_project_name, axis=1)
        df_proc['Category'] = df_proc.apply(lambda r: get_category(r, r['Project Name']), axis=1)
        df_proc['Commentary'] = ""

        if st.button(f"🚀 CREATE {sheet_name.upper()} SHEET"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_proc.to_excel(writer, index=False, sheet_name='BankReport')
                workbook, worksheet = writer.book, writer.sheets['BankReport']
                
                options_sheet = workbook.add_worksheet('HiddenData')
                for i, cat in enumerate(CAT_OPTIONS): options_sheet.write(i, 0, cat)
                for i, proj in enumerate(PROJ_OPTIONS): options_sheet.write(i, 1, proj)
                options_sheet.hide()

                worksheet.data_validation('I2:I2000', {'validate': 'list', 'source': f'=HiddenData!$A$1:$A${len(CAT_OPTIONS)}'})
                worksheet.data_validation('J2:J2000', {'validate': 'list', 'source': f'=HiddenData!$B$1:$B${len(PROJ_OPTIONS)}'})
                
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                for col_num, value in enumerate(df_proc.columns.values):
                    worksheet.write(0, col_num, value, header_fmt)
                
                worksheet.set_column('A:B', 15)
                worksheet.set_column('C:E', 28) 
                worksheet.set_column('F:F', 50) 
                worksheet.set_column('G:K', 25)

            output.seek(0)
            link = upload_and_convert(output, sheet_name)
            
            if link:
                st.markdown(f'''<a href="{link}" target="_blank" style="text-decoration:none;">
                    <div style="background-color:#0F9D58;color:white;padding:25px;border-radius:15px;text-align:center;font-size:22px;font-weight:bold;">
                    📊 OPEN {sheet_name.replace("_", " ")}
                    </div></a>''', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error: {e}")
