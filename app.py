import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {"title": "Bank Automator", "upload_label": "Upload Bank CSV", "download_btn": "📥 Download Excel", "reset": "♻️ Reset", "rule_manager": "Settings"},
    "Latviešu": {"title": "Bankas automatizācija", "upload_label": "Augšupielādēt CSV", "download_btn": "📥 Lejupielādēt Excel", "reset": "♻️ Atiestatīt", "rule_manager": "Iestatījumi"},
    "Русский": {"title": "Автоматизация банка", "upload_label": "Загрузить CSV", "download_btn": "📥 Скачать Excel", "reset": "♻️ Сбросить", "rule_manager": "Настройки"}
}

# --- 2. PAGE SETUP & BLACK/WHITE STYLE ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    /* Global Background White */
    .stApp { background-color: #ffffff; }
    
    /* Sidebar Light Gray */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        border-right: 1px solid #000000;
    }

    /* All Text Black */
    h1, h2, h3, p, span, label { color: #000000 !important; }

    /* Buttons Black with White Text */
    div.stButton > button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 0px !important;
        border: 1px solid #000000 !important;
    }
    
    /* Input Fields White with Black Border */
    .stTextInput>div>div>input {
        background-color: #ffffff !important;
        border: 1px solid #000000 !important;
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [{'name': 'Transport', 'keywords': 'BOLT, CITYBEE', 'active': True}]
if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [{'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}]

# --- 4. SIDEBAR (LOGO ADDED HERE) ---
with st.sidebar:
    # --- LOGO SECTION ---
    # If the file is in your GitHub folder, use the filename here:
    try:
        st.image("YoungFolks-circle-42.png", use_container_width=True) 
    except:
        st.write("📌 *Add logo.png to your folder*")
    
    selected_lang = st.selectbox("🌍 Language", options=list(LANGUAGES.keys()))
    t = LANGUAGES[selected_lang]
    
    if st.button(t["reset"]):
        st.session_state.clear()
        st.rerun()
    
    st.divider()
    st.header(t["rule_manager"])
    # (Category and Project management UI remains same as previous versions...)

# --- 5. MAIN APP ---
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
        st.dataframe(df[cols], use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df[df['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name='Credit')
            df[df['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name='Debit')

        st.download_button(t["download_btn"], output.getvalue(), "Report.xlsx", "application/vnd.ms-excel")
    except Exception as e:
        st.error(f"Error: {e}")
