import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {
        "title": "🏦 Bank Automator",
        "upload_label": "Upload CSV",
        "rule_manager": "Rule Manager",
        "cat_header": "📁 CATEGORIES",
        "proj_header": "📁 PROJECTS",
        "add_list_btn": "➕ New List",
        "add_rule_btn": "➕ Add Rule",
        "name": "Name",
        "keywords": "Keywords",
        "success": "Processed: {} Income / {} Expenses",
        "download_mode": "Excel Format",
        "mode_sign": "By Debit/Credit",
        "mode_proj": "By Custom Lists",
        "download_btn": "📥 Download",
        "reset": "♻️ Reset"
    },
    "Latviešu": {
        "title": "🏦 Bankas automatizācija",
        "upload_label": "Augšupielādēt CSV",
        "rule_manager": "Noteikumu vadība",
        "cat_header": "📁 KATEGORIJAS",
        "proj_header": "📁 PROJEKTI",
        "add_list_btn": "➕ Jauns saraksts",
        "add_rule_btn": "➕ Pievienot",
        "name": "Nosaukums",
        "keywords": "Atslēgvārdi",
        "success": "Apstrādāts: {} ienākumi / {} izdevumi",
        "download_mode": "Formāts",
        "mode_sign": "Debets/Kredīts",
        "mode_proj": "Pa sarakstiem",
        "download_btn": "📥 Lejupielādēt",
        "reset": "♻️ Atiestatīt"
    },
    "Русский": {
        "title": "🏦 Автоматизация",
        "upload_label": "Загрузить CSV",
        "rule_manager": "Правила",
        "cat_header": "📁 КАТЕГОРИИ",
        "proj_header": "📁 ПРОЕКТЫ",
        "add_list_btn": "➕ Новый список",
        "add_rule_btn": "➕ Добавить",
        "name": "Имя",
        "keywords": "Ключи",
        "success": "Итог: {} дох. / {} расх.",
        "download_mode": "Формат",
        "mode_sign": "Дебет/Кредит",
        "mode_proj": "По спискам",
        "download_btn": "📥 Скачать",
        "reset": "♻️ Сброс"
    }
}

# --- 2. CONFIG & COMPACT UI CSS ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    /* Reduce vertical padding in the main block */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    
    /* Tighten Sidebar elements */
    [data-testid="stSidebarContent"] { padding-top: 0rem !important; }
    div[data-testid="stVerticalBlock"] > div { gap: 0.3rem !important; }
    
    /* Reduce divider margins */
    hr { margin: 0.5rem 0px !important; }
    
    /* Compact expanders */
    .streamlit-expanderHeader { padding-top: 0.2rem !important; padding-bottom: 0.2rem !important; }
    
    /* Responsive Text Scaling */
    [data-testid="stSidebarContent"] { container-type: inline-size; }
    @container (min-width: 0px) { [data-testid="stSidebarContent"] * { font-size: calc(11px + 0.1cqw) !important; } }
    @container (min-width: 400px) { [data-testid="stSidebarContent"] * { font-size: calc(13px + 0.4cqw) !important; } }

    /* Square Logo styling */
    .logo-container-bottom { display: flex; justify-content: center; align-items: center; padding-top: 20px; }
    .logo-container-bottom img { width: 80px; height: 80px; object-fit: contain; }
    
    .stButton button { width: 100% !important; border-radius: 4px; padding: 0.2rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE, RENFE', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa', 'active': True},
        {'name': 'Project Funding', 'keywords': 'NVA, Erasmus, Līgums', 'active': True},
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība, Kursi', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas maksa', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums, Donation', 'active': True}
    ]

if 'custom_lists' not in st.session_state:
    st.session_state.custom_lists = [{
        'title': 'PROJECTS', 
        'rules': [
            {'name': 'LESSONS', 'keywords': 'Lesson, Nodarbība', 'active': True},
            {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True},
            {'name': 'NVA Project', 'keywords': 'NVA, 8.3-8.1', 'active': True}
        ]
    }]

# --- 4. SIDEBAR ---
with st.sidebar:
    # Language Picker (Top Left)
    selected_lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    h_col, r_col = st.columns([3, 1])
    h_col.markdown(f"**{t['rule_manager']}**")
    if r_col.button(t["reset"]):
        st.session_state.clear()
        st.rerun()

    # SECTION: CATEGORIES
    with st.expander(t["cat_header"]):
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([0.6, 3, 0.6])
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"c_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input(t["name"], value=rule['name'], key=f"c_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"c_del_{i}"):
                st.session_state.cat_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"c_k_{i}", height=50)
        st.button(t["add_rule_btn"], key="add_cat", on_click=lambda: st.session_state.cat_rules.append({'name': 'New', 'keywords': '', 'active': True}))

    # SECTION: DYNAMIC LISTS
    for idx, r_list in enumerate(st.session_state.custom_lists):
        with st.expander(f"📁 {r_list['title']}"):
            l1, l2 = st.columns([3, 1])
            r_list['title'] = l1.text_input("Title", value=r_list['title'], key=f"lt_{idx}", label_visibility="collapsed")
            if l2.button("🗑️", key=f"ld_{idx}"):
                st.session_state.custom_lists.pop(idx)
                st.rerun()
            
            for i, rule in enumerate(r_list['rules']):
                p1, p2, p3 = st.columns([0.6, 3, 0.6])
                rule['active'] = p1.checkbox("On", value=rule['active'], key=f"l_{idx}_on_{i}", label_visibility="collapsed")
                rule['name'] = p2.text_input(t["name"], value=rule['name'], key=f"l_{idx}_n_{i}", label_visibility="collapsed")
                if p3.button("🗑️", key=f"l_{idx}_del_{i}"):
                    r_list['rules'].pop(i)
                    st.rerun()
                rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"l_{idx}_k_{i}", height=50)
            st.button(t["add_rule_btn"], key=f"ar_{idx}", on_click=lambda r=r_list: r['rules'].append({'name': 'New', 'keywords': '', 'active': True}))

    if st.button(t["add_list_btn"], type="primary"):
        st.session_state.custom_lists.append({'title': 'NEW LIST', 'rules': []})
        st.rerun()

    st.markdown('<div class="logo-container-bottom">', unsafe_allow_html=True)
    try:
        st.image("YoungFolks-circle-42.png")
    except:
        pass
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN LOGIC ---
st.subheader(t["title"])
uploaded_file = st.file_uploader(t["upload_label"], type="csv", label_visibility="collapsed")

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
        search_col = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
        df['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
        for r_list in st.session_state.custom_lists:
            df[r_list['title']] = search_col.apply(lambda x: classify(x, r_list['rules']))
        
        st.write(t["success"].format(len(df[df['Sign'] == 'K']), len(df[df['Sign'] == 'D'])))
        st.dataframe(df, use_container_width=True, height=300)

        c1, c2 = st.columns([2, 1])
        mode = c1.radio(t["download_mode"], [t["mode_sign"], t["mode_proj"]], horizontal=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if mode == t["mode_sign"]:
                df[df['Sign'] == 'K'].to_excel(writer, index=False, sheet_name='Income')
                df[df['Sign'] == 'D'].to_excel(writer, index=False, sheet_name='Expenses')
            else:
                for r_list in st.session_state.custom_lists:
                    col = r_list['title']
                    for name in df[df[col] != ""][col].unique():
                        df[df[col] == name].to_excel(writer, index=False, sheet_name=str(name)[:31])

        c2.download_button(t["download_btn"], output.getvalue(), "Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
