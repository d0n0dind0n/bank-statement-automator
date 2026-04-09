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
        "add_btn": "➕ Add New",
        "name": "Name",
        "keywords": "Keywords (comma separated)",
        "success": "Processed: {} Income and {} Expenses",
        "download_mode": "Choose Excel Format",
        "mode_sign": "Separated by Debit/Credit",
        "mode_proj": "Separated by Projects",
        "download_btn": "📥 Download Excel File",
        "reset": "♻️ Reset"
    },
    "Latviešu": {
        "title": "🏦 Bankas izrakstu automatizācija",
        "upload_label": "Augšupielādēt bankas CSV",
        "rule_manager": "Noteikumu vadība",
        "cat_header": "📁 KATEGORIJAS",
        "proj_header": "📁 PROJEKTI",
        "add_btn": "➕ Pievienot jaunu",
        "name": "Nosaukums",
        "keywords": "Atslēgvārdi (atdalīti ar komatu)",
        "success": "Apstrādāts: {} ienākumi un {} izdevumi",
        "download_mode": "Izvēlieties Excel formātu",
        "mode_sign": "Atdalīts pēc Debeta/Kredīta",
        "mode_proj": "Atdalīts pēc projektiem",
        "download_btn": "📥 Lejupielādēt Excel failu",
        "reset": "♻️ Atiestatīt"
    },
    "Русский": {
        "title": "🏦 Автоматизация банковских выписок",
        "upload_label": "Загрузить банковский CSV",
        "rule_manager": "Управление правилами",
        "cat_header": "📁 КАТЕГОРИИ",
        "proj_header": "📁 ПРОЕКТЫ",
        "add_btn": "➕ Добавить",
        "name": "Название",
        "keywords": "Ключевые слова (через запятую)",
        "success": "Обработано: {} доходов и {} расходов",
        "download_mode": "Выберите формат Excel",
        "mode_sign": "Разделение по Дебету/Кредиту",
        "mode_proj": "Разделение по проектам",
        "download_btn": "📥 Скачать Excel файл",
        "reset": "♻️ Сброс"
    }
}

# --- 2. CONFIG & SESSION STATE ---
st.set_page_config(page_title="Young Folks Bank Automator", layout="wide")

if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums, Donation', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'LESSONS', 'keywords': 'Lesson, Nodarbība', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
    ]

# --- 3. SIDEBAR ---
with st.sidebar:
    # 1. Language Picker at the top left
    selected_lang = st.selectbox("🌍 Language", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    # Logo
    try:
        st.image("YoungFolks-circle-42.png", use_container_width=True)
    except:
        pass

    st.divider()
    
    # 2. Rule Manager Header + Reset Button side-by-side
    header_col, reset_col = st.columns([2, 1])
    header_col.subheader(t["rule_manager"])
    if reset_col.button(t["reset"]):
        st.session_state.clear()
        st.rerun()
    
    # --- CATEGORIES SECTION ---
    with st.expander(t["cat_header"], expanded=False):
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([0.6, 3, 0.6])
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"c_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input(t["name"], value=rule['name'], key=f"c_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"c_del_{i}"):
                st.session_state.cat_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"c_k_{i}", height=68)
            st.divider()
        if st.button(t["add_btn"], key="add_cat"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True})
            st.rerun()

    # --- PROJECTS SECTION ---
    with st.expander(t["proj_header"], expanded=False):
        for i, rule in enumerate(st.session_state.proj_rules):
            p1, p2, p3 = st.columns([0.6, 3, 0.6])
            rule['active'] = p1.checkbox("On", value=rule['active'], key=f"p_on_{i}", label_visibility="collapsed")
            rule['name'] = p2.text_input(t["name"], value=rule['name'], key=f"p_n_{i}", label_visibility="collapsed")
            if p3.button("🗑️", key=f"p_del_{i}"):
                st.session_state.proj_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"p_k_{i}", height=68)
            st.divider()
        if st.button(t["add_btn"], key="add_proj"):
            st.session_state.proj_rules.append({'name': 'New Project', 'keywords': '', 'active': True})
            st.rerun()

# --- 4. MAIN LOGIC ---
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
                        safe_name = project[:24].replace('/', '_') 
                        if not p_credit.empty: p_credit.to_excel(writer, index=False, sheet_name=f"{safe_name} Credit")
                        if not p_debit.empty: p_debit.to_excel(writer, index=False, sheet_name=f"{safe_name} Debit")
                
                gen_df = df[df['Project Name'] == ""]
                if not gen_df.empty:
                    gc, gd = gen_df[gen_df['Sign'] == 'K'][cols], gen_df[gen_df['Sign'] == 'D'][cols]
                    if not gc.empty: gc.to_excel(writer, index=False, sheet_name='General Credit')
                    if not gd.empty: gd.to_excel(writer, index=False, sheet_name='General Debit')

        st.download_button(t["download_btn"], output.getvalue(), "Report.xlsx", "application/vnd.ms-excel")
    except Exception as e:
        st.error(f"Error: {e}")
