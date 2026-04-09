import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {"title": "🏦 Bank Automator", "upload": "Upload CSV", "cat": "📁 CATEGORIES", "proj": "📁 PROJECTS", "add_rule": "➕ Add Rule", "add_list": "➕ Add New List", "mode": "Excel Mode", "m_sign": "By Debit/Credit", "m_proj": "By Project", "dl": "📥 Download Excel"},
    "Latviešu": {"title": "🏦 Bankas automatizācija", "upload": "Augšupielādēt CSV", "cat": "📁 KATEGORIJAS", "proj": "📁 PROJEKTI", "add_rule": "➕ Pievienot noteikumu", "add_list": "➕ Izveidot jaunu sarakstu", "mode": "Excel formāts", "m_sign": "Pa Debetu/Kredītu", "m_proj": "Pa Projektiem", "dl": "📥 Lejupielādēt"},
    "Русский": {"title": "🏦 Автоматизация", "upload": "Загрузить CSV", "cat": "📁 КАТЕГОРИИ", "proj": "📁 ПРОЕКТЫ", "add_rule": "➕ Добавить правило", "add_list": "➕ Новый список", "mode": "Формат Excel", "m_sign": "По Дебету/Кредиту", "m_proj": "По Проектам", "dl": "📥 Скачать Excel"}
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

# --- 3. SESSION STATE (RESTORED ORIGINAL DATA) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE, RENFE, Pasažieru vilciens', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda, Dalības maksa', 'active': True},
        {'name': 'Project Funding', 'keywords': 'NVA, Erasmus, Līgums', 'active': True},
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība, Kursi', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija, Apkalpošanas maksa', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums, Donation', 'active': True}
    ]

if 'custom_lists' not in st.session_state:
    st.session_state.custom_lists = [
        {'title': 'LESSONS', 'rules': [{'name': 'Lessons', 'keywords': 'Lesson, Nodarbība', 'active': True}]},
        {'title': 'Young Folks', 'rules': [{'name': 'YF Support', 'keywords': 'Young Folks, YF', 'active': True}]},
        {'title': 'NVA DEBIT', 'rules': [{'name': 'NVA Pay', 'keywords': 'NVA', 'active': True}]},
        {'title': 'NVA CREDIT', 'rules': [{'name': 'NVA Refund', 'keywords': 'NVA Refund', 'active': True}]}
    ]

# --- 4. SIDEBAR (RULE MANAGER) ---
with st.sidebar:
    lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[lang]
    
    st.header("Rule Manager")
    
    # CATEGORIES
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
            st.session_state.cat_rules.append({'name': 'New', 'keywords': '', 'active': True}); st.rerun()

    # PROJECTS
    st.subheader(t["proj"])
    for idx, r_list in enumerate(st.session_state.custom_lists):
        with st.expander(f"📁 {r_list['title']}"):
            l1, l2 = st.columns([3, 1])
            r_list['title'] = l1.text_input("List Name", value=r_list['title'], key=f"lt_{idx}")
            if l2.button("🗑️", key=f"ld_{idx}"):
                st.session_state.custom_lists.pop(idx); st.rerun()
            for i, rule in enumerate(r_list['rules']):
                p1, p2, p3 = st.columns([0.5, 3, 0.5])
                rule['active'] = p1.checkbox("", value=rule['active'], key=f"p_on_{idx}_{i}", label_visibility="collapsed")
                rule['name'] = p2.text_input("Name", value=rule['name'], key=f"p_n_{idx}_{i}", label_visibility="collapsed")
                if p3.button("🗑️", key=f"p_d_{idx}_{i}"):
                    r_list['rules'].pop(i); st.rerun()
                rule['keywords'] = st.text_area("Keywords", value=rule['keywords'], key=f"p_k_{idx}_{i}", height=60)
            if st.button(t["add_rule"], key=f"p_add_{idx}"):
                r_list['rules'].append({'name': 'New', 'keywords': '', 'active': True}); st.rerun()

    if st.button(t["add_list"], type="primary"):
        st.session_state.custom_lists.append({'title': 'NEW LIST', 'rules': []}); st.rerun()

    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    try: st.image("YoungFolks-circle-42.png")
    except: pass
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN LOGIC & EXPORT ---
st.title(t["title"])
file = st.file_uploader(t["upload"], type="csv")

def classify(text, rules):
    text = str(text).lower()
    for r in rules:
        if r['active'] and r['keywords']:
            keys = [k.strip().lower() for k in r['keywords'].split(',')]
            if any(k in text for k in keys if k): return r['name']
    return ""

if file:
    try:
        df = pd.read_csv(file, sep=';', header=None, encoding='utf-8', on_bad_lines='skip')
        df_proc = pd.DataFrame()
        df_proc['Account'] = df[0]
        df_proc['Date'] = df[2]
        df_proc['Partner'] = df[3]
        df_proc['Purpose'] = df[4]
        df_proc['Amount'] = df[5]
        df_proc['_Sign'] = df[7]
        
        search_txt = df_proc['Partner'].fillna('') + " " + df_proc['Purpose'].fillna('')
        df_proc['Category'] = search_txt.apply(lambda x: classify(x, st.session_state.cat_rules))
        df_proc['Commentary'] = ""

        st.dataframe(df_proc.drop(columns=['_Sign']), use_container_width=True)

        st.divider()
        mode = st.radio(t["mode"], [t["m_sign"], t["m_proj"]])
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
            
            if mode == t["m_sign"]:
                # Sheet per Debit (D) / Credit (K)
                for sign, s_name in [('K', 'Income'), ('D', 'Expenses')]:
                    subset = df_proc[df_proc['_Sign'] == sign].copy()
                    subset['Project Name'] = ""
                    subset[cols].to_excel(writer, index=False, sheet_name=s_name)
            else:
                # SEPARATE LISTS PER PROJECT (NVA CREDIT, NVA DEBIT, etc. get their own sheets)
                for r_list in st.session_state.custom_lists:
                    df_proj = df_proc.copy()
                    df_proj['Project Name'] = search_txt.apply(lambda x: classify(x, r_list['rules']))
                    final_subset = df_proj[df_proj['Project Name'] != ""].copy()
                    if not final_subset.empty:
                        sheet_name = str(r_list['title'])[:31].strip()
                        final_subset[cols].to_excel(writer, index=False, sheet_name=sheet_name)

        st.download_button(t["dl"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
