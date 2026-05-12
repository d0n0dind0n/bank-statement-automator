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

# --- 2. LOAD MEMBERSHIP LOOKUP FROM TXT FILES ---
membership_files = {
    "YF Youth.txt": "YF Youth",
    "Forever Young.txt": "Forever Young",
    "YF kids.txt": "YF kids",
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
        except Exception as e:
            st.error(f"Could not load {file_name}: {e}")

# --- 3. UPDATED FILTER LOGIC BASED ON YOUR FILE ---
def process_row_advanced(row):
    purpose = str(row['Purpose']).lower()
    name = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose} {name}"

    # Default values
    cat, div, sub = "Services", "YF Main", ""

    # --- CATEGORY FILTERS ---
    if any(kw in full_text for kw in ["ziedojums", "ziedot"]):
        cat = "Donations"
    elif "reimbursement" in full_text or "erasmus" in full_text:
        cat = "Erasmus+"
    elif any(kw in full_text for kw in ["biedru nauda", "dalības maksa", "dalibmaksa", "abonements"]) or name in membership_lookup:
        cat = "Membership"
    elif any(kw in full_text for kw in ["bolt", "citybee", "internetbank", "komisija", "noma", "ikea", "depo"]):
        cat = "Operational Expenses"
    elif "autoratlīdzības" in full_text or "alga" in full_text:
        cat = "Salaries"

    # --- DIVISION FILTERS ---
    if name in membership_lookup:
        div = membership_lookup[name]
    elif "bolt" in full_text or "citybee" in full_text:
        div = "YF logistics"
    elif "internetbank" in full_text:
        div = "Internetbank"
    elif "kartes mēneša maksa" in full_text or "komisija" in full_text:
        div = "Comission"
    elif "latviešu valoda" in full_text or "latv.val" in full_text:
        div = "Latvian language"
    elif "risunok" in full_text or "gleznieciba" in full_text:
        div = "Academic drawing"
    elif "angļu valoda" in full_text:
        div = "English language"
    elif "madeira" in full_text:
        div = "Madeira"
    elif "nva" in full_text:
        div = "NVA / ESF"
    elif "voices in action" in full_text:
        div = "E+ YE Voices in action"
    elif "green realities" in full_text:
        div = "YE GREEN REALITIES"
    elif "podcast" in full_text:
        div = 'Valsts Kase projekts ESC30 "Youth'
    elif "lekcija" in full_text or "workshop" in full_text:
        div = "Workshops"

    # --- SUB FILTERS ---
    if "reimbursement" in full_text:
        sub = "Reimbursement"
    elif any(kw in full_text for kw in ["kouching", "koučings", "coaching"]):
        sub = "Coaching"
    elif "nometne" in full_text or "winter camp" in full_text:
        sub = "Winter camp"
    elif "brein- ring" in full_text or "brainring" in full_text:
        sub = "Brainring"
    elif "green realities" in full_text and "apv" in full_text:
        sub = "APV GREEN REALITIES"

    return cat, div, sub

# --- 4. DATA VALIDATION LISTS ---
CAT_OPTIONS = ["Donations", "Erasmus+", "Help Ukraine", "Membership", "Operational Expenses", "Projects", "Salaries", "Services", "YE Travel"]
DIV_OPTIONS = ["Academic drawing", "BNI Artmen", "Comission", "E+ YE Voices in action", "English language", "Erasmus", "Erasmus Adult", "Forever Young", "German", "Internetbank", "JEF Europe", "Latvian language", "Madeira", "NVA / ESF", "Office Rent", "Office supplies", "Reimbursement", "Say it Ring", "Sense (design)", "Taxes", 'Valsts Kase projekts ESC30 "Youth', "Workshops", "YE GREEN REALITIES", "YF kids", "YF logistics", "YF Main", "YF Teens", "YF Youth"]
SUB_OPTIONS = ["APV GREEN REALITIES", "Brainring", "Christmas party", "Cinema production", "Coaching", "Creative jam event", "Italy?", "Reimbursement", "Sarunvalodas", "Speed Friending", "Umniy dom", "Winter camp"]

# ... [The rest of the Drive authentication and Streamlit UI code remains exactly as in your main version] ...
