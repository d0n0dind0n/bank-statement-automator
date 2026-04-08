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
        "lang_label": "Select Language / Izvēlēties valodu"
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
        "lang_label": "Izvēlēties valodu / Select Language"
    }
}

# --- 2. PAGE SETUP ---
st.set_page_config(page_title="Bank Automator Pro", layout="wide")

# Language Selector in Sidebar
with st.sidebar:
    selected_lang = st.selectbox("🌍 Language", options=list(LANGUAGES.keys()))
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
    return str(text).split('|')[0].strip()

def classify(text, rules_list):
    if pd.isna(text): return ""
    text = str(text).lower()
    for rule in rules_list:
        if rule['active'] and rule['keywords']:
            keywords = [k.strip().lower() for k in rule['keywords'].split(',')]
            if any(k in text for k in keywords if k):
                return rule['name']
    return ""

def process_data(file):
    df = pd.read_csv(file, sep=';', header=None)
    df.columns = ['Account', 'TypeCode', 'Date', 'Partner', 'Purpose', 'Amount', 
                  'Currency', 'Sign', 'ID', 'Code', 'Extra1', 'Extra2']
    
    df = df[~df['Purpose'].str.contains('Opening balance|Turnover|Closing balance', case=False, na=False)]
    df['Partner'] = df['Partner'].apply(clean_partner_name)
    
    search_col = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
    df['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
    df['Project Name'] = search_col.apply(lambda x: classify(x, st.session_state.proj_rules))
    df['Commentary'] = ""
    
    output_cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
    
    return df[df['Sign'] == 'K'][output_cols], df[df['Sign'] == 'D'][output_cols]

# --- 6. MAIN INTERFACE ---
uploaded_file = st.file_uploader(t["upload_label"], type="csv")

if uploaded_file:
    credit_df, debit_df = process_data(uploaded_file)
    st.success(t["success"].format(len(credit_df), len(debit_df)))
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader(t["credit_title"])
        st.dataframe(credit_df)
    with col_b:
        st.subheader(t["debit_title"])
        st.dataframe(debit_df)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        credit_df.to_excel(writer, index=False, sheet_name='Credit')
        debit_df.to_excel(writer, index=False, sheet_name='Debit')
    
    st.download_button(
        label=t["download_btn"],
        data=output.getvalue(),
        file_name=f"Report_{uploaded_file.name.replace('.csv', '.xlsx')}",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
