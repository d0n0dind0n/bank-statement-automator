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
        "add_list_btn": "➕ Create New List",
        "add_rule_btn": "➕ Add Rule",
        "name": "Name",
        "keywords": "Keywords",
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
        "add_list_btn": "➕ Izveidot jaunu sarakstu",
        "add_rule_btn": "➕ Pievienot noteikumu",
        "name": "Nosaukums",
        "keywords": "Atslēgvārdi",
        "download_mode": "Excel formāts",
        "mode_sign": "Pa Debetu/Kredītu",
        "mode_proj": "Pa Projektiem",
        "download_btn": "📥 Lejupielādēt Excel",
        "reset": "♻️ Atiestatīt"
    },
    "Русский": {
        "title": "🏦 Автоматизация банковских выписок",
        "upload_label": "Загрузить банковский CSV",
        "rule_manager": "Управление правилами",
        "cat_header": "📁 КАТЕГОРИИ",
        "proj_header": "📁 ПРОЕКТЫ",
        "add_list_btn": "➕ Создать новый список",
        "add_rule_btn": "➕ Добавить правило",
        "name": "Название",
        "keywords": "Ключевые слова",
        "download_mode": "Формат Excel",
        "mode_sign": "По Дебету/Кредиту",
        "mode_proj": "По Проектам",
        "download_btn": "📥 Скачать Excel",
        "reset": "♻️ Сброс"
    }
}

# --- 2. CONFIG ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    .logo-container-bottom { display: flex; justify-content: center; padding-top: 50px; padding-bottom: 20px; }
    .logo-container-bottom img { width: 100px; height: 100px; object-fit: contain; }
    .stButton button { width: 100% !important; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE (CATEGORIES & PROJECTS ONLY) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE, RENFE, Pasažieru vilciens', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas maksa', 'active': True}
    ]

if 'custom_lists' not in st.session_state:
    st.session_state.custom_lists = [
        {'title': 'NVA DEBIT', 'rules': [{'name': 'NVA Payment', 'keywords': 'NVA', 'active': True}]},
        {'title': 'NVA CREDIT', 'rules': [{'name': 'NVA Refund', 'keywords': 'NVA Refund', 'active': True}]},
        {'title': 'LESSONS', 'rules': [{'name': 'Lessons', 'keywords': 'Lesson, Nodarbība', 'active': True}]},
        {'title': 'Young Folks', 'rules': [{'name': 'YF Support', 'keywords': 'Young Folks, YF', 'active': True}]}
    ]

# --- 4. SIDEBAR ---
with st.sidebar:
    selected_lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    st.divider()
    h_col, r_col = st.columns([2, 1])
    h_col.subheader(t["rule_manager"])
    if r_col.button(t["reset"]):
        st.session_state.clear(); st.rerun()

    # SECTION 1: CATEGORIES
    with st.expander(t["cat_header"], expanded=True):
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([0.4, 3, 0.5])
            rule['active'] = c1.checkbox("", value=rule['active'], key=f"cat_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input("", value=rule['name'], key=f"cat_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"cat_del_{i}"):
                st.session_state.cat_rules.pop(i); st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"cat_k_{i}", height=60)
            st.divider()
        if st.button(t["add_rule_btn"], key="add_cat"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True}); st.rerun()

    # SECTION 2: PROJECTS
    st.markdown(f"### {t['proj_header']}")
    for idx, r_list in enumerate(st.session_state.custom_lists):
        with st.expander(f"📁 {r_list['title']}"):
            l1, l2 = st.columns([3, 1])
            r_list['title'] = l1.text_input("List Name", value=r_list['title'], key=f"lt_{idx}")
            if l2.button("🗑️", key=f"ld_{idx}"):
                st.session_state.custom_lists.pop(idx); st.rerun()
            for i, rule in enumerate(r_list['rules']):
                p1, p2, p3 = st.columns([0.4, 3, 0.5])
                rule['active'] = p1.checkbox("", value=rule['active'], key=f"l_{idx}_on_{i}", label_visibility="collapsed")
                rule['name'] = p2.text_input("", value=rule['name'], key=f"l_{idx}_n_{i}", label_visibility="collapsed")
                if p3.button("🗑️", key=f"l_{idx}_del_{i}"):
                    r_list['rules'].pop(i); st.rerun()
                rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"l_{idx}_k_{i}", height=60)
                st.divider()
            if st.button(t["add_rule_btn"], key=f"ar_{idx}"):
                r_list['rules'].append({'name': 'New Rule', 'keywords': '', 'active': True}); st.rerun()

    if st.button(t["add_list_btn"], type="primary"):
        st.session_state.custom_lists.append({'title': 'NEW PROJECT', 'rules': []}); st.rerun()

    st.markdown('<div class="logo-container-bottom">', unsafe_allow_html=True)
    try: st.image("YoungFolks-circle-42.png")
    except: pass
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. PROCESSING & EXCEL ---
st.title(t["title"])
uploaded_file = st.file_uploader(t["upload_label"], type="csv")

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
        
        df_proc = pd.DataFrame()
        df_proc['Account'] = df[0]
        df_proc['Date'] = df[2]
        df_proc['Partner'] = df[3]
        df_proc['Purpose'] = df[4]
        df_proc['Amount'] = df[5]
        df_proc['_Sign'] = df[7]
        
        search_col = df_proc['Partner'].fillna('') + " " + df_proc['Purpose'].fillna('')
        df_proc['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Commentary'] = ""

        st.dataframe(df_proc.drop(columns=['_Sign']), use_container_width=True)

        st.divider()
        mode = st.radio(t["download_mode"], [t["mode_sign"], t["mode_proj"]])
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
            
            if mode == t["mode_sign"]:
                for s, sheet_name in [('K', 'Income'), ('D', 'Expenses')]:
                    subset = df_proc[df_proc['_Sign'] == s].copy()
                    subset['Project Name'] = ""
                    subset[cols].to_excel(writer, index=False, sheet_name=sheet_name)
            else:
                for r_list in st.session_state.custom_lists:
                    df_proj = df_proc.copy()
                    df_proj['Project Name'] = search_col.apply(lambda x: classify(x, r_list['rules']))
                    final_subset = df_proj[df_proj['Project Name'] != ""].copy()
                    if not final_subset.empty:
                        sheet_name = str(r_list['title'])[:31].strip()
                        final_subset[cols].to_excel(writer, index=False, sheet_name=sheet_name)

        st.download_button(t["download_btn"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
