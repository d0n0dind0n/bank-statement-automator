import streamlit as st
import pandas as pd
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re
import os

# --- 1. KONFIGURĀCIJA ---
REDIRECT_URI = "https://bank-statement-automator-wm4atvbmldyrwdehnbnkzb.streamlit.app/"
CLIENT_ID = st.secrets["google_oauth"]["client_id"]
CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- NEW: LOAD MEMBERSHIP FROM TXT FILES ---
# Mapping the filename to the Project Name used in your app
membership_files = {
    "YF Youth.txt": "YF Youth",
    "Forever Young.txt": "Forever Young",
    "YF kids.txt": "YF kids",
    "YF teens.txt": "YF teens"
}

membership_lookup = {}

for file_name, project_label in membership_files.items():
    try:
        # Checking if file exists to prevent crash
        if os.path.exists(file_name):
            with open(file_name, "r", encoding="utf-8") as f:
                for line in f:
                    name = line.strip().lower()
                    if name and "participant" not in name: # Skip header if present
                        membership_lookup[name] = project_label
    except Exception as e:
        st.error(f"Could not load {file_name}: {e}")

# --- 2. AUTENTIFIKĀCIJA (No changes here) ---
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
        st.error(f"Pieteikšanās kļūda: {e}")
        st.query_params.clear()

if st.session_state.auth_creds is None:
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPES)
    auth_url, _ = google.authorization_url(AUTH_URL, access_type="offline", prompt="select_account")
    st.title("🏦 Bank to Sheets")
    st.link_button("🔑 Login with Google", auth_url)
    st.stop()

# --- 3. OPTIONS & FILTERS ---
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
    "YF Youth", "Forever Young", "New York", "Iceland", "Japan",
    "Say it Ring", "Sense (design)", "Latvian language", "English language",
    "Workshops", "Office Rent", "Animators"
]

CAT_FILTER = {
    "dalības": "Membership", "biedru nauda": "Membership", "dalībmaksa": "Membership",
    "dalibmaksa": "Membership", "abonements": "Membership", "biedriba nauda": "Membership", 
    "yf2024": "Membership", "yf2026": "Membership", "fy": "Membership", 
    "dalibmaksa par klubu": "Membership", "biedra nauda": "Membership",
    "ziedojums": "Donations", "ziedojumu": "Donations",
    "stipendija": "Salaries", "alga": "Salaries", "nodokli": "Salaries",
    "autoratlīdzības": "Salaries", "autoratlidzibas": "Salaries", "līgums": "Salaries",
    "ligums nva": "Salaries",
    "bolt": "YF Logistics", "wolt": "YF Logistics", "citybee": "YF Logistics",
    "pirkums": "YF Logistics", "travel": "YF Travel", "japan": "YF Travel",
    "iceland": "YF Travel", "lekcija": "Services", "latviesu": "Services",
    "english": "Services", "valoda": "Services", "sarunvalodas": "Services",
    "akademicheskiy risunok": "Services", "akademicheskiy": "Services", "gleznieciba": "Services", 
    "akademiska": "Services", "urok": "Services", "lv nodarbības": "Services",
    "rent": "Rent & Admin", "komisija": "Operational Expenses",
    "apkalpošanas": "Operational Expenses", "noma": "Operational Expenses", 
    "telpu noma": "Operational Expenses", "kartes mēneša maksa": "Operational Expenses",
    "tele2": "Office supplies", "reimbursement": "Erasmus+", "erasmus": "Erasmus+"
}

PROJ_FILTER = {
    "erasmus": "Erasmus",
    "200b": "Valsts Kase projekts DiscoverEU \"My Europ too\" (200B)",
    "300b": "Valsts Kase projekts ESC30 \"Youth Podcast Station\" (300B)",
    "400b": "Valsts Kase projekts KA210 \"Youth Identiy Hub\" (400B)",
    "500b": "Valsts Kase projekts ESC30\"Youth Work Bus\" (500B)",
    "zemlya": "Erasmus+ project Project 101239301 \"Zemlya\"",
    "shift": "Erasmus+ KA210 \"SHIFT\"",
    "young business": "Erasmus+ KA210 project \"Young Business\"",
    "gear up": "projekts Lapas GEAR UP! \"Līderu Skola\"",
    "līderu skola": "projekts Lapas GEAR UP! \"Līderu Skola\"",
    "nodokļi": "nodokļi", "kids": "YF kids", "bērnu": "YF kids", "new york": "New York",
    "iceland": "Iceland", "japan": "Japan", "gredzen": "Say it Ring",
    "ring": "Say it Ring", "fy": "Forever Young", "forever": "Forever Young",
    "sense": "Sense (design)", "latviesu": "Latvian language", "lv nodarbības": "Latvian language",
    "akademicheskiy risunok": "Workshops", "akademicheskiy": "Workshops",
    "english": "English language", "meistarklase": "Workshops",
    "workshops": "Workshops", "sarunvalodas": "Workshops", 
    "noma": "Office Rent", "animators": "Animators",
    "bolt": "projekti", "wolt": "projekti"
}

# --- 4. DATA LOGIC (Modified to prioritize file lookups) ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    amt = max(row['K (KREDITS)'], row['D (DEBETS)'])
    name_orig = str(row['Name Surname'])
    name_lower = name_orig.lower().strip()
    full_text = f"{purpose_lower} {name_lower}"

    # Step 1: Specific Check for NVA
    if "ligums nva" in purpose_lower or "līgums nva" in purpose_lower:
        return "Salaries", "NVA / ESF"

    # Step 2: Normal Category Detection
    category = "Single payment" # Default
    if "say it ring" in full_text:
        category = "Services"
    elif "noma" in full_text:
        category = "Operational Expenses"
    elif "lv nodarbības" in full_text or re.search(r'\b(latv|val)\b', full_text):
        category = "Services"
    else:
        for kw, cat in CAT_FILTER.items():
            if kw.lower() in full_text:
                category = cat
                break

    # Step 3: Project Assignment Logic
    project = "YF Main" # Default fallback
    
    # Check if the name exists in our Club text files
    if name_lower in membership_lookup:
        project = membership_lookup[name_lower]
    else:
        # Fallback keyword logic if name not in files
        if re.search(r'\bnva\b', purpose_lower):
            project = "NVA / ESF"
        elif "lv nodarbības" in full_text or re.search(r'\b(latv|val)\b', full_text):
            project = "Latvian language"
        else:
            membership_keywords = [
                "dalības", "biedru nauda", "dalībmaksa", "dalibmaksa", 
                "biedriba nauda", "yf2024", "yf2026", "fy", 
                "biedra nauda", "dalibmaksa par klubu"
            ]
            is_membership_signal = any(kw in full_text for kw in membership_keywords)
            
            if is_membership_signal:
                if amt in [20, 30]: project = "Forever Young"
                elif amt in [15, 25]: project = "YF teens"
            else:
                for key, proj in PROJ_FILTER.items():
                    if key in full_text:
                        project = proj
                        break
    
    return category, project

# --- 5. DRIVE & APP FLOW (Rest of code remains the same) ---
# ... (include existing upload_and_convert and Streamlit UI logic)
