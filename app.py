import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {
        "title": "🏦 Bank Automator",
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
        "download_mode": "Excel Format",
        "mode_sign": "By Debit/Credit",
        "mode_proj": "By Projects",
        "download_btn": "📥 Download Excel File",
        "reset": "♻️ Reset App"
    },
    "Latviešu": {
        "title": "🏦 Bankas automatizācija",
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
        "download_mode": "Excel formāts",
        "mode_sign": "Pa Debetu/Kredītu",
        "mode_proj": "Pa projektiem",
        "download_btn": "📥 Lejupielādēt Excel",
        "reset": "♻️ Atiestatīt"
    },
    "Русский": {
        "title": "🏦 Автоматизация банков",
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
        "download_mode": "Формат Excel",
        "mode_sign": "По Дебету/Кредиту",
        "mode_proj": "По проектам",
        "download_btn": "📥 Скачать Excel",
        "reset": "♻️ Сбросить"
    }
}

# --- 2. PAGE SETUP & BRANDED STYLE ---
st.set_page_config(page_title="Young Folks Automator", layout="wide", page_icon="🏦")

st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #ffffff; }
    
    /* Sidebar - Young Folks Green */
    section[data-testid="stSidebar"] {
        background-color: #006837 !important; 
    }
    
    /* Sidebar Text White */
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: white !important;
    }

    /* Primary Action Buttons - Young Folks Red */
    div.stButton > button {
        background-color: #ff0000 !important;
        color: white !important;
        border-radius: 20px !important;
        border: none !important;
        font-weight: bold;
        width: 100%;
    }

    /* Main Titles Green */
    h1 { color: #006837 !important; border-bottom: 3px solid #ff0000; padding-bottom: 10px; }
    
    /* Input Fields */
    .stTextInput>div>div>input {
        background-color: #ffffff !important;
        border: 1px solid #006837 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa', 'active': True},
        {'name': 'Project Funding', 'keywords': 'NVA, Erasmus, Līgums', 'active': True},
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība, Kursi', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas maksa', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums, Donation', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True},
        {'name': 'NVA Project', 'keywords': 'NVA, 8.3-8.1', 'active': True}
    ]

# --- 4. SIDEBAR ---
with st.sidebar:
    # Attempt to load your specific logo file
    try:
        st.image("YoungFolks-circle-42.png", use_container_width=True)
    except:
        st.info("Logo file not found. Ensure 'YoungFolks-circle-42.png' is in the GitHub folder.")
    
    selected_lang = st.selectbox("🌍 Language", options=list(LANGUAGES.keys()))
    t = LANGUAGES[selected_lang]
    
    if st.button(t["reset"]):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.header(t["rule_manager"])
    
    # Categories
    st.subheader(t["cat_header"])
    for i, rule in enumerate(st.session_state.cat_rules):
        with st.expander(f"{rule['name'] or '...'}"):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"c_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"c_n_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"c_k_{i}")
    if st.button(t["add_cat"]):
        st.session_state.cat_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

    # Projects
    st.subheader(t["proj_header"])
    for i, rule in enumerate(st.session_state.proj_rules):
        with st.expander(f"{rule['name'] or '...'}"):
            rule['active'] = st.checkbox(t["active"], value=rule['active'], key=f"p_on_{i}")
            rule['name'] = st.text_input(t["name"], value=rule['name'], key=f"p_n_{i}")
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"p_k_{i}")
    if st.button(t["add_proj"]):
        st.session_state.proj_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

# --- 5. MAIN LOGIC ---
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
        df = pd.read_csv(uploaded_file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        df.rename(columns={0:'Account', 2:'Date', 3:'Partner', 4:'Purpose', 5:'Amount', 7:'Sign'}, inplace=True)
        df['Partner'] = df['Partner'].apply(clean_name)
        search_col = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
        df['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
        df['Project Name'] = search_col.apply(lambda x: classify(x, st.session_state.proj_rules))
        df['Commentary'] = ""
        df = df[~df['Purpose'].str.contains('balance|Turnover', case=False, na=False)]
        
        cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
        st.success(t["success"].format(len(df[df['Sign'] == 'K']), len(df[df['Sign'] == 'D'])))
        st.dataframe(df[cols], use_container_width=True)

        st.divider()
        st.subheader(t["download_mode"])
        mode = st.radio("Selection", [t["mode_sign"], t["mode_proj"]], label_visibility="collapsed")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if mode == t["mode_sign"]:
                df[df['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name='Credit')
                df[df['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name='Debit')
            else:
                unique_projects = [r['name'] for r in st.session_state.proj_rules if r['active'] and r['name']]
                for project in unique_projects:
                    proj_df = df[df['Project Name'] == project]
                    if not proj_df.empty:
                        p_credit = proj_df[proj_df['Sign'] == 'K'][cols]
                        p_debit = proj_df[proj_df['Sign'] == 'D'][cols]
                        safe_name = project[:24] 
                        if not p_credit.empty: p_credit.to_excel(writer, index=False, sheet_name=f"{safe_name} Cr")
                        if not p_debit.empty: p_debit.to_excel(writer, index=False, sheet_name=f"{safe_name} Db")
                
                # General transactions logic
                gen_df = df[df['Project Name'] == ""]
                if not gen_df.empty:
                    gc = gen_df[gen_df['Sign'] == 'K'][cols]
                    gd = gen_df[gen_df['Sign'] == 'D'][cols]
                    if not gc.empty: gc.to_excel(writer, index=False, sheet_name='General Cr')
                    if not gd.empty: gd.to_excel(writer, index=False, sheet_name='General Db')

        st.download_button(t["download_btn"], output.getvalue(), "YoungFolks_Report.xlsx", "application/vnd.ms-excel")
    except Exception as e:
        st.error(f"Error: {e}")
