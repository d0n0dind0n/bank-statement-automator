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
        "success": "Processed: {} Income and {} Expenses",
        "download_btn": "📥 Download Excel",
        "reset": "♻️ Reset App"
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
        "success": "Apstrādāts: {} ienākumi un {} izdevumi",
        "download_btn": "📥 Lejupielādēt Excel",
        "reset": "♻️ Atiestatīt"
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
        "success": "Обработано: {} доходов и {} расходов",
        "download_btn": "📥 Скачать Excel",
        "reset": "♻️ Сбросить"
    }
}

# --- 2. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Bank Automator", layout="wide")

if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [{'name': 'Donations', 'keywords': 'ziedojums', 'active': True}]
if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [{'name': 'Young Folks', 'keywords': 'Young Folks', 'active': True}]

# --- 3. SIDEBAR ---
with st.sidebar:
    selected_lang = st.selectbox("🌍 Language", options=list(LANGUAGES.keys()))
    t = LANGUAGES[selected_lang]
    
    if st.button(t["reset"]):
        st.rerun()
    
    st.divider()
    st.header(t["rule_manager"])
    
    # Categories
    st.subheader(t["cat_header"])
    for i, rule in enumerate(st.session_state.cat_rules):
        with st.expander(f"{rule['name'] if rule['name'] else '...'}"):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"c_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"c_n_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"c_k_{i}")
    if st.button(t["add_cat"]):
        st.session_state.cat_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

    # Projects
    st.subheader(t["proj_header"])
    for i, rule in enumerate(st.session_state.proj_rules):
        with st.expander(f"{rule['name'] if rule['name'] else '...'}"):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"p_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"p_n_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"p_k_{i}")
    if st.button(t["add_proj"]):
        st.session_state.proj_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

# --- 4. MAIN APP ---
st.title(t["title"])

# The uploader is placed here so
