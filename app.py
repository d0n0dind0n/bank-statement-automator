import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {
        "title": "🏦 Bank Statement Automator",
        "upload_label": "Upload Bank CSV",
        "rule_manager": "Rule Manager",
        "cat_header": "📁 CATEGORIES",
        "proj_header": "📁 PROJECTS",
        "add_btn": "➕ Add New Rule",
        "name": "Name",
        "keywords": "Keywords",
        "success": "Processed: {} Income and {} Expenses",
        "download_mode": "Excel Format",
        "mode_sign": "By Debit/Credit",
        "mode_proj": "By Projects",
        "download_btn": "📥 Download Excel",
        "reset": "♻️ Reset"
    },
    "Latviešu": {
        "title": "🏦 Bankas automatizācija",
        "upload_label": "Augšupielādēt bankas CSV",
        "rule_manager": "Noteikumu vadība",
        "cat_header": "📁 KATEGORIJAS",
        "proj_header": "📁 PROJEKTI",
        "add_btn": "➕ Pievienot jaunu",
        "name": "Nosaukums",
        "keywords": "Atslēgvārdi",
        "success": "Apstrādāts: {} ienākumi un {} izdevumi",
        "download_mode": "Excel formāts",
        "mode_sign": "Pa Debetu/Kredītu",
        "mode_proj": "Pa projektiem",
        "download_btn": "📥 Lejupielādēt Excel",
        "reset": "♻️ Atiestatīt"
    }
}

# --- 2. CONFIG & DYNAMIC RESPONSIVE STYLE ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    /* Makes text and buttons scale based on sidebar width */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] button p {
        font-size: 0.9vw !important; 
        min-font-size: 12px;
    }
    [data-testid="stSidebar"] input {
        font-size: 1vw !important;
        font-weight: bold !important;
    }
    section[data-testid="stSidebar"] {
        min-width: 250px;
        max-width: 600px;
    }
    .stButton button {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE (Restoring All Original Data) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE, RENFE', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa', 'active': True},
        {'name': 'Project Funding', 'keywords': 'NVA, Erasmus, Līgums', 'active': True},
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība, Kursi', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas maksa', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums, Donation', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'LESSONS', 'keywords': 'Lesson, Nodarbība, Kursi', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True},
        {'name': 'NVA Project', 'keywords': 'NVA, 8.3-8.1', 'active': True}
    ]

# --- 4. SIDEBAR ---
with st.sidebar:
    selected_lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    try:
        st.image("YoungFolks-circle-42.png", use_container_width=True)
    except:
        pass

    st.divider()
    
    h_col, r_col = st.columns([2, 1])
    h_col.subheader(t["rule_manager"])
    if r_col.button(t["reset"]):
        st.session_state.clear()
        st.rerun()
    
    # MASTER CATEGORIES
    with st.expander(t["cat_header"], expanded=False):
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([0.7, 3, 0.7])
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"c_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input(t["name"], value=rule['name'], key=f"c_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"c_del_{i}"):
                st.session_state.cat_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"c_k_{i}", height=70)
            st.divider()
        if st.button(t["add_btn"], key="add_cat_main"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True})
            st.rerun()

    # MASTER PROJECTS
    with st.expander(t["proj_header"], expanded=False):
        for i, rule in enumerate(st.session_state.proj_rules):
            p1, p2, p3 = st.columns([0.7, 3, 0.7])
            rule['active'] = p1.checkbox("On", value=rule['active'], key=f"p_on_{i}", label_visibility="collapsed")
            rule['name'] = p2.text_input(t["name"], value=rule['name'], key=f"p_n_{i}", label_visibility="collapsed")
            if p3.button("🗑️", key=f"p_del_{i}"):
                st.session_state.proj_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"p_k_{i}", height=70)
            st.divider()
        if st.button(t["add_btn"], key="add_proj_main"):
            st.session_state.proj_rules.append({'name': 'New Project', 'keywords': '', 'active': True})
            st.rerun()

# --- 5. PROCESSING LOGIC ---
st.title(t["title"])
uploaded_file = st.file_uploader(t["upload_label"], type="csv")

def clean_name(text):
    if pd.isna(text) or text == "": return ""
    return str(text).split('|')[0].strip() if '|' in str(text) else str(text).strip()

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
        df = df[~df['Purpose'].str.contains('balance|Turnover|atlikums|Apgrozījums', case=False, na=False)]
        
        cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
        st.success(t["success"].format(len(df[df['Sign'] == 'K']), len(df[df['Sign'] == 'D'])))
        st.dataframe(df[cols], use_container_width=True)

        st.divider()
        mode = st.radio(t["download_mode"], [t["mode_sign"], t["mode_proj"]])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if mode == t["mode_sign"]:
                df[df['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name='Credit')
                df[df['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name='Debit')
            else:
                # Loop through custom projects to create sheets
                unique_projects = [r['name'] for r in st.session_state.proj_rules if r['active'] and r['name']]
                for project in unique_projects:
                    p_df = df[df['Project Name'] == project]
                    if not p_df.empty:
                        safe = project[:24].replace('/', '_')
                        p_df[p_df['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name=f"{safe} CR")
                        p_df[p_df['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name=f"{safe} DB")
                
                # General Catch-all
                gen = df[df['Project Name'] == ""]
                if not gen.empty:
                    gen[gen['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name='General CR')
                    gen[gen['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name='General DB')

        st.download_button(t["download_btn"], output.getvalue(), "Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
