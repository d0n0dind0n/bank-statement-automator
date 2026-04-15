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

# --- [Categories & Project rules sections remain the same as previous version] ---
# (I'm skipping the full list here for brevity, keep your current rules in the code)

# --- 3. GOOGLE DRIVE FUNKCIJA (Returns link) ---
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
        
        # Create file and ask for the webViewLink
        file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"Google Drive Error: {e}")
        return None

# --- [Parsing & Classification functions remain the same] ---

# --- 5. UI ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")
lang = st.sidebar.selectbox("Valoda / Language", options=list(LANGUAGES.keys()))
t = LANGUAGES[lang]

# --- 6. MAIN LOGIC ---
st.title(t["title"])
file = st.file_uploader(t["upload"], type="csv")

if file:
    try:
        # [Processing logic remains the same...]
        # (df_proc creation, category assignment, etc.)
        
        # We need this placeholder to create the final data
        df_final = df_proc.sort_values(by='Date')
        
        # Prepare Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'K (KREDITS)', 'D (DEBETS)', 'Category', 'Project Name', 'Commentary']
            df_final[cols].to_excel(writer, index=False, sheet_name="Atskaite")
        excel_data = output.getvalue()

        st.divider()
        
        # --- SEPARATE BUTTONS ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("Option A: Traditional")
            st.download_button(
                label=t["dl"],
                data=excel_data,
                file_name=f"YF_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with col2:
            st.info("Option B: Online (No download)")
            if st.button(t["sheets"]):
                output.seek(0)
                with st.spinner("Preparing Google Sheet..."):
                    # Create a unique filename with timestamp
                    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M")
                    filename = f"Bank_Report_{timestamp}.xlsx"
                    
                    web_link = upload_to_drive(output, filename)
                    
                    if web_link:
                        st.success("✅ File ready in Google Drive!")
                        # Create the clickable link styled as a button
                        st.markdown(f"""
                            <div style="text-align: center; margin-top: 20px;">
                                <a href="{web_link}" target="_blank" style="
                                    text-decoration: none; 
                                    padding: 15px 25px; 
                                    background-color: #0F9D58; 
                                    color: white; 
                                    border-radius: 8px; 
                                    font-size: 18px;
                                    font-weight: bold;
                                    box-shadow: 2px 2px 5px rgba(0,0,0,0.2);">
                                    👉 CLICK HERE TO OPEN IN SHEETS
                                </a>
                            </div>
                        """, unsafe_allow_html=True)
                        st.balloons()

    except Exception as e:
        st.error(f"Error: {e}")
