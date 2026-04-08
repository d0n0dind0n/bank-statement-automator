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
        "credit_title": "Credit (Income)",
        "debit_title": "Debit (Expense)",
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
        "credit_title": "Kredīts (Ienākumi)",
        "debit_title": "Debets (Izdevumi)",
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
        "credit_title": "Кредит (Доходы)",
        "debit_title": "Дебет (Расходы)",
        "download_btn": "📥 Скачать Excel",
        "reset": "♻️ Сбросить"
    }
}

# --- 2. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Bank Automator", layout="wide")

if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport & Mobility', 'keywords': 'BOLT, CITYBEE, RENFE', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa, Dalībasmaksa', 'active': True},
        {'name': 'Project Funding / Grants', 'keywords': 'NVA, Erasmus, Līgums, 4.3.3.2, 8.3-8.1', 'active': True},
        {'name': 'Professional Services', 'keywords': 'Rēķins, Invoice, YF2026, YF2025', 'active': True},
        {'name': 'Education & Training', 'keywords': 'Lekcija, Nodarbība, Kursi, Valoda, Zanjatija', 'active': True},
        {'name': 'Bank & Finance', 'keywords': 'Komisija, Apkalpošanas maksa, Internetbankas', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums, Donation', 'active': True},
        {'name': 'Administrative', 'keywords': 'Opening balance, Closing balance, Turnover', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True},
        {'name': 'NVA', 'keywords': 'NVA, 8.3-8.1', 'active': True}
    ]

# --- 3. SIDEBAR ---
with st.sidebar:
    selected_lang = st.selectbox("🌍 Language", options=list(LANGUAGES.keys()))
    t = LANGUAGES[selected_lang]
    if st.button(t["reset"]):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.header(t["rule_manager"])
    st.subheader(t["cat_header"])
    for i, rule in enumerate(st.session_state.cat_rules):
        with st.expander(f"{rule['name'] or '...'}"):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"c_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"c_n_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"c_k_{i}")
    if st.button(t["add_cat"]):
        st.session_state.cat_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

# --- 4. MAIN APP ---
st.title(t["title"])
uploaded_file = st.file_uploader(t["upload_label"], type="csv")

def clean_name(text):
    if pd.isna(text) or text == "": return ""
    return str(text).split('|')[0].strip()

def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            keys = [k.strip().lower() for k in r['keywords'].split(',')]
            if any(k in text for k in keys if k): return r['name']
    return ""

if uploaded_file is not None:
    try:
        # Using on_bad_lines='skip' to avoid the ParserError if a line is formatted weirdly
        df = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        
        # We handle files with different column counts dynamically
        num_cols = len(df.columns)
        col_names = ['Account', 'Type', 'Date', 'Partner', 'Purpose', 'Amount', 'Currency', 'Sign', 'ID', 'Code', 'Extra1', 'Extra2']
        df.columns = col_names[:num_cols]
        
        # Processing
        df['Partner'] = df['Partner'].apply(clean_name)
        combined = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
        df['Category'] = combined.apply(lambda x: classify(x, st.session_state.cat_rules))
        df['Project Name'] = combined.apply(lambda x: classify(x, st.session_state.proj_rules))
        df['Commentary'] = ""
        
        cols_to_show = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
        # Filter out balance rows
        df = df[~df['Purpose'].str.contains('balance|Turnover|atlikums|Apgrozījums', case=False, na=False)]
        
        credit = df[df['Sign'] == 'K'][cols_to_show]
        debit = df[df['Sign'] == 'D'][cols_to_show]
        
        st.success(t["success"].format(len(credit), len(debit)))
        tab1, tab2 = st.tabs([t["credit_title"], t["debit_title"]])
        with tab1: st.dataframe(credit, use_container_width=True)
        with tab2: st.dataframe(debit, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            credit.to_excel(writer, index=False, sheet_name='Credit')
            debit.to_excel(writer, index=False, sheet_name='Debit')
        
        st.download_button(t["download_btn"], output.getvalue(), f"Report.xlsx", "application/vnd.ms-excel")
    except Exception as e:
        st.error(f"Error processing file: {e}")
