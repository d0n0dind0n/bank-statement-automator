import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {
        "title": "🏦 Bank Statement Automator",
        "upload_label": "Upload Bank CSV",
        "rule_manager": "⚙️ Rule Manager",
        "cat_header": "Categories",
        "proj_header": "Projects",
        "add_cat": "➕ Add Category",
        "add_proj": "➕ Add Project",
        "active": "Active",
        "name": "Name",
        "keywords": "Keywords",
        "success": "Processed: {} Income entries and {} Expense entries.",
        "credit_title": "Credit (Income)",
        "debit_title": "Debit (Expense)",
        "download_btn": "📥 Download Split Sheets Excel",
    },
    "Latviešu": {
        "title": "🏦 Bankas izrakstu automatizācija",
        "upload_label": "Augšupielādēt bankas CSV",
        "rule_manager": "⚙️ Noteikumu vadība",
        "cat_header": "Kategorijas",
        "proj_header": "Projekti",
        "add_cat": "➕ Pievienot kategoriju",
        "add_proj": "➕ Pievienot projektu",
        "active": "Aktīvs",
        "name": "Nosaukums",
        "keywords": "Atslēgvārdi",
        "success": "Apstrādāts: {} ienākumu ieraksti un {} izdevumu ieraksti.",
        "credit_title": "Kredīts (Ienākumi)",
        "debit_title": "Debets (Izdevumi)",
        "download_btn": "📥 Lejupielādēt Excel failu",
    },
    "Русский": {
        "title": "🏦 Автоматизация банковских выписок",
        "upload_label": "Загрузить банковский CSV",
        "rule_manager": "⚙️ Управление правилами",
        "cat_header": "Категории",
        "proj_header": "Проекты",
        "add_cat": "➕ Добавить категорию",
        "add_proj": "➕ Добавить проект",
        "active": "Активен",
        "name": "Название",
        "keywords": "Ключевые слова",
        "success": "Обработано: {} записей о доходах и {} записей о расходах.",
        "credit_title": "Кредит (Доходы)",
        "debit_title": "Дебет (Расходы)",
        "download_btn": "📥 Скачать Excel файл",
    }
}

# --- 2. PAGE SETUP ---
st.set_page_config(page_title="Bank Automator Pro", layout="wide")

# Language Selector in Sidebar
with st.sidebar:
    selected_lang = st.selectbox("🌍 Language / Valoda / Язык", options=list(LANGUAGES.keys()))
    t = LANGUAGES[selected_lang]

st.title(t["title"])

# --- 3. SESSION STATE ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Membership Fees', 'keywords': 'dalības maksa, biedru nauda', 'active': True},
        {'name': 'Donations', 'keywords': 'ziedojums, donation', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA Project', 'keywords': 'NVA-20, 8.3-8.1', 'active': True}
    ]

# --- 4. SIDEBAR: RULE MANAGER ---
with st.sidebar:
    st.divider()
    st.header(t["rule_manager"])
    
    st.subheader(t["cat_header"])
    for i, rule in enumerate(st.session_state.cat_rules):
        with st.expander(f"{rule['name'] if rule['name'] else '...'}", expanded=False):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"cat_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"cat_name_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"cat_key_{i}")
    
    if st.button(t["add_cat"]):
        st.session_state.cat_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

    st.divider()
    
    st.subheader(t["proj_header"])
    for i, rule in enumerate(st.session_state.proj_rules):
        with st.expander(f"{rule['name'] if rule['name'] else '...'}", expanded=False):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"proj_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"proj_name_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"proj_key_{i}")
            
    if st.button(t["add_proj"]):
        st.session_state.proj_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

# --- 5. PROCESSING LOGIC ---
def clean_partner_name(text):
    if pd.isna(text) or text == "": return ""
    # Split by '|' only if it exists, otherwise return
