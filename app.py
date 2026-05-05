import streamlit as st
import pandas as pd
import io
import os  # Added to handle paths
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests_oauthlib import OAuth2Session
from datetime import datetime
import re

# --- 1. CONFIGURATION & PATHS ---
# Get the absolute path to the current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMBERSHIP_FILE = os.path.join(BASE_DIR, "membership.xlsx")

# --- 2. LOAD MEMBERSHIP REFERENCE ---
@st.cache_data
def get_membership_mapping():
    # Use the absolute path
    if not os.path.exists(MEMBERSHIP_FILE):
        st.warning(f"⚠️ Reference file not found at {MEMBERSHIP_FILE}. Skipping name-based routing.")
        return {}
    
    try:
        ref_df = pd.read_excel(MEMBERSHIP_FILE)
        mapping = {}
        # Clean column names just in case of spaces
        ref_df.columns = [c.strip() for c in ref_df.columns]
        
        for _, row in ref_df.iterrows():
            project = str(row['Club']).strip()
            # Map both Participant and Parent
            if pd.notna(row['Participant']):
                mapping[str(row['Participant']).lower().strip()] = project
            if 'Parent' in ref_df.columns and pd.notna(row['Parent']):
                mapping[str(row['Parent']).lower().strip()] = project
        return mapping
    except Exception as e:
        st.error(f"Error reading membership.xlsx: {e}")
        return {}

MEMBERSHIP_MAP = get_membership_mapping()

# --- 3. UPDATED LOGIC FUNCTION ---
def process_row(row):
    purpose_lower = str(row['Purpose']).lower()
    name_lower = str(row['Name Surname']).lower().strip()
    full_text = f"{purpose_lower} {name_lower}"
    
    project = "YF Main"
    
    # 1. Check membership mapping first
    if name_lower in MEMBERSHIP_MAP:
        project = MEMBERSHIP_MAP[name_lower]
    else:
        # Check if any name from our mapping is mentioned in the Purpose
        for ref_name, ref_project in MEMBERSHIP_MAP.items():
            if ref_name in purpose_lower:
                project = ref_project
                break

    # 2. If still YF Main, check other keyword filters
    if project == "YF Main":
        if "lv nodarbības" in full_text or re.search(r'\b(latv|val)\b', full_text):
            project = "Latvian language"
        elif re.search(r'\bnva\b', purpose_lower):
            project = "NVA / ESF"
        # ... [Rest of your PROJ_FILTER logic here] ...

    # 3. Determine Category
    category = ""
    # Force 'Membership' category if project was found in membership.xlsx
    if project in ["Forever Young", "YF teens", "YF kids", "YF Youth"]:
        category = "Membership"
    elif "noma" in full_text:
        category = "Operational Expenses"
    else:
        # ... [Rest of your CAT_FILTER logic here] ...
        pass
                
    return category, project

# --- 4. APP INTERFACE ---
# (Keep the rest of your CSV reading and XlsxWriter logic as before)
