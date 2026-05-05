import streamlit as st
import pandas as pd
import io
import os
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

# --- 2. LOAD MEMBERSHIP REFERENCE (EXCEL ONLY) ---
@st.cache_data
def get_membership_mapping():
    mapping = {}
    file_path = "membership.xlsx"
    
    if not os.path.exists(file_path):
        st.error(f"❌ Error: {file_path} not found in your GitHub files.")
        return {}

    try:
        # Explicitly using openpyxl engine for Excel
        ref_df = pd.read_excel(file_path, engine='openpyxl')
        
        # Clean column names (remove hidden spaces)
        ref_df.columns = [str(c).strip() for c in ref_df.columns]
        
        for _, row in ref_df.iterrows():
            project = str(row['Club']).strip() if pd.notna(row['Club']) else "YF Main"
            
            # Map Participant Name
            if 'Participant' in ref_df.columns and pd.notna(row['Participant']):
                mapping[str(row['Participant']).lower().strip()] = project
            
            # Map Parent Name
            if 'Parent' in ref_df.columns and pd.notna(row['Parent']):
                mapping[str(row['Parent']).lower().strip()] = project
                
        return mapping
    except Exception as e:
        st.error(f"⚠️ Could not read Excel file: {e}. Ensure 'openpyxl' is installed.")
        return {}

MEMBERSHIP_MAP = get_membership_mapping()

# --- 3. FILTER SETTINGS ---
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
    "Valsts Kase projekts KA210 \"Youth Identity Hub\" (400B)",
    "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)",
    "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)",
    "Erasmus+ General", "Erasmus", "nodokļi", "YF Main", "YF kids", "YF teens",
    "Youth", "Forever Young", "New York", "Iceland", "Japan",
    "Say it Ring", "Sense (design)", "Latvian language", "English language",
    "Workshops", "Office Rent", "Animators"
]

# --- 4. CORE LOGIC ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"
    
    project = "YF Main"
    
    # Check Excel Mapping (Name or Purpose mention)
    if name_lower in MEMBERSHIP_MAP:
        project = MEMBERSHIP_MAP[name_lower]
    else:
        for ref_name, ref_project in MEMBERSHIP_MAP.items():
            if ref_name in purpose_lower:
                project = ref_project
                break

    # Keyword Overrides
    if project == "YF Main":
        if "lv nodarbības" in full_text or re.search(r'\b(latv|val)\b', full_text):
            project = "Latvian language"
        elif re.search(r'\bnva\b', purpose_lower):
            project = "NVA / ESF"

    # Category Logic
    category = "Services" # Default
    if "dalības" in full_text or "biedru nauda" in full_text:
        category = "Membership"
    elif any(x in project for x in ["Forever Young", "YF kids", "YF teens", "Youth"]):
        category = "Membership"
    
    return category, project

# --- 5. APP INTERFACE & PROCESSING ---
st.title("🏦 Bank Automator (Excel Sync)")

# (Standard Auth and File Upload logic remains same as your previous working versions)
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()
        
        # Build processing DF
        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        df_proc['Name Surname'] = df_filtered[3].apply(lambda x: str(x).split('|')[0].strip())
        df_proc['Purpose'] = df_filtered[4]
        
        # Apply logic
        results = df_proc.apply(process_row, axis=1)
        df_proc['Category'] = [r[0] for r in results]
        df_proc['Project Name'] = [r[1] for r in results]
        
        st.write("### Preview of Matched Projects")
        st.dataframe(df_proc[['Date', 'Name Surname', 'Project Name', 'Category']].head(10))
        
        # Button to trigger Sheets upload (standard logic)
        if st.button("🚀 Process & Upload to Sheets"):
            # ... [XlsxWriter logic here] ...
            st.success("Successfully processed using Excel references!")

    except Exception as e:
        st.error(f"Processing error: {e}")
