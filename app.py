import streamlit as st
import pandas as pd
import io
import re

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {
        "title": "🏦 Bank Automator", 
        "upload": "Upload CSV", 
        "cat": "📁 CATEGORY", 
        "proj": "📁 PROJECT", 
        "add_rule": "➕ Add Rule", 
        "dl": "📥 Download Excel Report"
    },
    "Latviešu": {
        "title": "🏦 Bankas automatizācija", 
        "upload": "Augšupielādēt CSV", 
        "cat": "📁 KATEGORIJA", 
        "proj": "📁 PROJEKTS", 
        "add_rule": "➕ Pievienot noteikumu", 
        "dl": "📥 Lejupielādēt atskaiti"
    },
    "Русский": {
        "title": "🏦 Автоматизация", 
        "upload": "Загрузить CSV", 
        "cat": "📁 КАТЕГОРИЯ", 
        "proj": "📁 ПРОЕКТ", 
        "add_rule": "➕ Добавить правило", 
        "dl": "📥 Скачать отчет Excel"
    }
}

# --- 2. CONFIG ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    .logo-container { display: flex; justify-content: center; padding: 20px 0; }
    .logo-container img { width: 100px; }
    .stButton button { width: 100% !important; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE, RENFE, Pasažieru vilciens', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas maksa', 'active': True},
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība, Kursi, sarunvalodas', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA', 'keywords': 'NVA', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True},
        {'name': 'Lessons', 'keywords': 'Lesson, Nodarbība, sarunvalodas', 'active': True}
    ]

# --- 4. HELPER FUNCTIONS ---
def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            keys = [k.strip().lower() for k in r['keywords'].split(',')]
            for k in keys:
                if k:
                    pattern = rf"\b{re.escape(k)}\b"
                    if re.search(pattern, text):
                        return r['name']
    return ""

def parse_partner(val):
    if pd.isna(val) or str(val).strip() == "":
        return {"Name": "", "P_Code": "", "Account": "", "SWIFT": ""}
    
    val = str(val).replace('|', ' ')
    iban = re.search(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', val)
    p_code = re.search(r'\d{6}-\d{5}', val)
    swift = re.search(r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b', val)
    
    clean_name = val
    if iban: clean_name = clean_name.replace(iban.group(), "")
    if p_code: clean_name = clean_name.replace(p_code.group(), "")
    if swift: clean_name = clean_name.replace(swift.group(), "")
    
    clean_name = re.sub(r'\s+', ' ', clean_name).strip().strip(',')
    return {
        "Name": clean_name if clean_name else "",
        "P_Code": p_code.group() if p_code else "",
        "Account": iban.group() if iban else "",
        "SWIFT": swift.group() if swift else ""
    }

# --- 5. SIDEBAR ---
with st.sidebar:
    lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[lang]
    st.header("Rule Manager")
    
    with st.expander(t["cat"], expanded=True):
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([0.5, 3, 0.5])
            rule['active'] = c1.checkbox("", value=rule['active'], key=f"c_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input("Name", value=rule['name'], key=f"c_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"c_d_{i}"):
                st.session_state.cat_rules.pop(i); st.rerun()
            rule['keywords'] = st.text_area("Keywords", value=rule['keywords'], key=f"c_k_{i}", height=60)
            st.divider()
        if st.button(t["add_rule"], key="add_cat"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True}); st.rerun()

    with st.expander(t["proj"], expanded=True):
        for i, rule in enumerate(st.session_state.proj_rules):
            p1, p2, p3 = st.columns([0.5, 3, 0.5])
            rule['active'] = p1.checkbox("", value=rule['active'], key=f"p_on_{i}", label_visibility="collapsed")
            rule['name'] = p2.text_input("Name", value=rule['name'], key=f"p_n_{i}", label_visibility="collapsed")
            if p3.button("🗑️", key=f"p_d_{i}"):
                st.session_state.proj_rules.pop(i); st.rerun()
            rule['keywords'] = st.text_area("Keywords", value=rule['keywords'], key=f"p_k_{i}", height=60)
            st.divider()
        if st.button(t["add_rule"], key="add_proj"):
            st.session_state.proj_rules.append({'name': 'New Project', 'keywords': '', 'active': True}); st.rerun()

    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    try: st.image("YoungFolks-circle-42.png")
    except: pass
    st.markdown('</div>', unsafe_allow_html=True)

# --- 6. MAIN APP ---
st.title(t["title"])
file = st.file_uploader(t["upload"], type="csv")

if file:
    try:
        df_raw = pd.read_csv(file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        
        # Exclusion logic for summary rows
        mask = df_raw.stack().str.contains('Turnover|balance|Apgrozījums|Atlikums', case=False, na=False).unstack().any(axis=1)
        df_filtered = df_raw[~mask].copy()
        df_filtered = df_filtered[df_filtered[2].astype(str).str.contains(r'\d{2}\.\d{2}\.\d{4}', na=False)]

        df_proc = pd.DataFrame()
        df_proc['Date'] = df_filtered[2]
        
        # Parse Name, Personal Code, IBAN, SWIFT
        partner_data = df_filtered[3].apply(parse_partner).apply(pd.Series).fillna("")
        df_proc['Name Surname'] = partner_data['Name']
        df_proc['Personal Code'] = partner_data['P_Code']
        df_proc['Konta numurs'] = partner_data['Account']
        df_proc['Bankas SWIFT'] = partner_data['SWIFT']
        
        df_proc['Purpose'] = df_filtered[4].fillna("")
        
        # Numeric Amount (dot decimal)
        raw_amount = df_filtered[5].astype(str).str.replace(',', '.', regex=False)
        num_amount = pd.to_numeric(raw_amount, errors='coerce')
        df_proc['Amount'] = num_amount
        df_proc['_Sign'] = df_filtered[7]
        
        # Classify based on rules
        search_txt = df_filtered[3].fillna('') + " " + df_filtered[4].fillna('')
        df_proc['Category'] = search_txt.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project Name'] = search_txt.apply(lambda x: classify(x, st.session_state.proj_rules))
        df_proc['Commentary'] = ""

        # Export everything to one sheet
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
            
            # Sorted by date, all together
            final_df = df_proc.sort_values(by='Date')
            final_df[cols].to_excel(writer, index=False, sheet_name="Full Report")

        st.divider()
        st.download_button(t["dl"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
