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
        "mode": "Excel Mode", 
        "m_proj": "All",                
        "m_all": "Full Report",         
        "dl": "📥 Download Excel"
    },
    "Latviešu": {
        "title": "🏦 Bankas automatizācija", 
        "upload": "Augšupielādēt CSV", 
        "cat": "📁 KATEGORIJA", 
        "proj": "📁 PROJEKTS", 
        "add_rule": "➕ Pievienot noteikumu", 
        "mode": "Excel formāts", 
        "m_proj": "Visi", 
        "m_all": "Pilna atskaite", 
        "dl": "📥 Lejupielādēt"
    },
    "Русский": {
        "title": "🏦 Автоматизация", 
        "upload": "Загрузить CSV", 
        "cat": "📁 КАТЕГОРИЯ", 
        "proj": "📁 ПРОЕКТ", 
        "add_rule": "➕ Добавить правило", 
        "mode": "Формат Excel", 
        "m_proj": "Все", 
        "m_all": "Полный отчет", 
        "dl": "📥 Скачать Excel"
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

# --- 4. SIDEBAR ---
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

# --- 5. HELPER FUNCTIONS ---
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
    val = str(val)
    # Extracts IBAN (Standard format starting with 2 letters)
    iban = re.search(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', val)
    # Extracts Personal Code (Latvian style: 6 digits - 5 digits)
    p_code = re.search(r'\d{6}-\d{5}', val)
    # Extract SWIFT (8 or 11 characters)
    swift = re.search(r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b', val)
    
    # Clean name: remove the codes found above to leave just the name
    clean_name = val
    if iban: clean_name = clean_name.replace(iban.group(), "")
    if p_code: clean_name = clean_name.replace(p_code.group(), "")
    if swift: clean_name = clean_name.replace(swift.group(), "")
    
    return {
        "Name": clean_name.strip().strip(','),
        "P_Code": p_code.group() if p_code else "",
        "Account": iban.group() if iban else "",
        "SWIFT": swift.group() if swift else ""
    }

# --- 6. MAIN APP ---
st.title(t["title"])
file = st.file_uploader(t["upload"], type="csv")

if file:
    try:
        df = pd.read_csv(file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        df_proc = pd.DataFrame()
        
        # Account column deleted as per request
        df_proc['Date'] = df[2]
        
        # Parse Partner Details
        partner_data = df[3].apply(parse_partner).apply(pd.Series)
        df_proc['Name Surname'] = partner_data['Name']
        df_proc['Personal Code'] = partner_data['P_Code']
        df_proc['Konta numurs'] = partner_data['Account']
        df_proc['Bankas SWIFT'] = partner_data['SWIFT']
        
        df_proc['Purpose'] = df[4]
        
        # Numeric processing
        raw_amount = df[5].astype(str).str.replace(',', '.', regex=False)
        num_amount = pd.to_numeric(raw_amount, errors='coerce')
        df_proc['Amount'] = num_amount
        df_proc['_Sign'] = df[7]
        
        # Column values for Full Report
        df_proc['K (KREDIT)'] = df_proc.apply(lambda x: x['Amount'] if x['_Sign'] == 'K' else None, axis=1)
        df_proc['D (DEBIT)'] = df_proc.apply(lambda x: x['Amount'] if x['_Sign'] == 'D' else None, axis=1)
        
        search_txt = df[3].fillna('') + " " + df[4].fillna('')
        df_proc['Category'] = search_txt.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Project Name'] = search_txt.apply(lambda x: classify(x, st.session_state.proj_rules))
        df_proc['Commentary'] = ""

        st.divider()
        mode = st.radio(t["mode"], [t["m_proj"], t["m_all"]]) 
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if mode == t["m_proj"]:
                # --- ALL MODE (Detailed sheets) ---
                cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
                for p_rule in st.session_state.proj_rules:
                    if p_rule['active']:
                        p_df = df_proc[df_proc['Project Name'] == p_rule['name']]
                        if not p_df.empty:
                            for sign, s_label in [('K', 'Income'), ('D', 'Expenses')]:
                                final_df = p_df[p_df['_Sign'] == sign]
                                if not final_df.empty:
                                    sheet_name = f"{p_rule['name']} {s_label}"[:31]
                                    final_df[cols].to_excel(writer, index=False, sheet_name=sheet_name)
                
                na_df = df_proc[df_proc['Project Name'] == ""]
                if not na_df.empty:
                    for sign, s_label in [('K', 'Income'), ('D', 'Expenses')]:
                        final_na = na_df[na_df['_Sign'] == sign]
                        if not final_na.empty:
                            sheet_name = f"NA {s_label}"[:31]
                            final_na[cols].to_excel(writer, index=False, sheet_name=sheet_name)
            
            else:
                # --- FULL REPORT MODE ---
                all_cols = ['Date', 'Name Surname', 'Personal Code', 'Konta numurs', 'Bankas SWIFT', 'Purpose', 'K (KREDIT)', 'D (DEBIT)', 'Category', 'Project Name', 'Commentary']
                df_all = df_proc.sort_values(by='Date')
                df_all[all_cols].to_excel(writer, index=False, sheet_name="Full Report")

        st.download_button(t["dl"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
