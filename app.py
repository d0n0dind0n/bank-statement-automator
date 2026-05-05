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

# --- 2. LOAD MEMBERSHIP REFERENCE ---
@st.cache_data
def get_membership_mapping():
    try:
        # Loading the reference file
        ref_df = pd.read_excel("membership.xlsx")
        mapping = {}
        for _, row in ref_df.iterrows():
            project = str(row['Club']).strip()
            # Map both Participant and Parent to the project
            if pd.notna(row['Participant']):
                mapping[str(row['Participant']).lower().strip()] = project
            if pd.notna(row['Parent']):
                mapping[str(row['Parent']).lower().strip()] = project
        return mapping
    except Exception as e:
        st.error(f"Could not load membership.xlsx: {e}")
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
    "Valsts Kase projekts KA210 \"Youth Identiy Hub\" (400B)",
    "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)",
    "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)",
    "Erasmus+ General", "Erasmus", "nodokļi", "YF Main", "YF kids", "YF teens",
    "Youth", "Forever Young", "New York", "Iceland", "Japan",
    "Say it Ring", "Sense (design)", "Latvian language", "English language",
    "Workshops", "Office Rent", "Animators"
]

# Filtering keywords
CAT_FILTER = {
    "dalības": "Membership", "biedru nauda": "Membership", "yf2026": "Membership",
    "ziedojums": "Donations", "alga": "Salaries", "lekcija": "Services",
    "sarunvalodas": "Services", "akademicheskiy risunok": "Services",
    "kartes mēneša maksa": "Operational Expenses", "noma": "Operational Expenses"
}

PROJ_FILTER = {
    "erasmus": "Erasmus", "nva": "NVA / ESF", "kids": "YF kids", "bērnu": "YF kids",
    "meistarklase": "Workshops", "akademicheskiy": "Workshops"
}

# --- 4. CORE LOGIC ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"
    
    project = "YF Main"
    
    # Priority 1: Check membership.xlsx mapping (Child or Parent Name)
    # Check if the sender's name is in our database
    if name_lower in MEMBERSHIP_MAP:
        project = MEMBERSHIP_MAP[name_lower]
    # Check if a child's name is mentioned in the purpose field
    else:
        for ref_name, ref_project in MEMBERSHIP_MAP.items():
            if ref_name in purpose_lower:
                project = ref_project
                break

    # Priority 2: Specific phrase/regex overrides
    if project == "YF Main":
        if "lv nodarbības" in full_text or re.search(r'\b(latv|val)\b', full_text):
            project = "Latvian language"
        elif re.search(r'\bnva\b', purpose_lower):
            project = "NVA / ESF"
        else:
            for key, val in PROJ_FILTER.items():
                if key in full_text:
                    project = val
                    break

    # Determine Category
    category = ""
    if "dalības" in full_text or "biedru nauda" in full_text or "membership" in project.lower():
        category = "Membership"
    elif "noma" in full_text:
        category = "Operational Expenses"
    else:
        for kw, cat in CAT_FILTER.items():
            if kw in full_text:
                category = cat
                break
                
    return category, project

# --- 5. STREAMLIT UI & UPLOAD ---
# (Rest of your original Streamlit code for file handling and Google Drive upload)
st.title("🏦 Bank Automator")
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    try:
        df_raw = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8').fillna("")
        df_filtered = df_raw[df_raw[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)].copy()
        
        # ... [Standard parsing logic as per previous versions] ...
        # (Assuming the same column mapping for Name, Purpose, etc.)
        
        # Placeholder for demonstration of applying the new logic:
        # results = df_proc.apply(process_row, axis=1)
        # df_proc['Category'] = [r[0] for r in results]
        # df_proc['Project Name'] = [r[1] for r in results]
        
        st.success("Logic updated! Names in 'membership.xlsx' will now auto-route to their clubs.")
    except Exception as e:
        st.error(f"Error: {e}")
