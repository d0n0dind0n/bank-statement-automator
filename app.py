import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGE DICTIONARY ---
LANGUAGES = {
    "English": {"title": "🏦 Bank Automator", "upload": "Upload CSV", "cat": "📁 CATEGORY", "proj": "📁 PROJECT", "add_rule": "➕ Add Rule", "mode": "Excel Mode", "m_sign": "By Debit/Credit", "m_proj": "By Project", "dl": "📥 Download Excel"},
    "Latviešu": {"title": "🏦 Bankas automatizācija", "upload": "Augšupielādēt CSV", "cat": "📁 KATEGORIJA", "proj": "📁 PROJEKTS", "add_rule": "➕ Pievienot noteikumu", "mode": "Excel formāts", "m_sign": "Pa Debetu/Kredītu", "m_proj": "Pa Projektiem", "dl": "📥 Lejupielādēt"},
    "Русский": {"title": "🏦 Автоматизация", "upload": "Загрузить CSV", "cat": "📁 КАТЕГОРИЯ", "proj": "📁 ПРОЕКТ", "add_rule": "➕ Добавить правило", "mode": "Формат Excel", "m_sign": "По Дебету/Кредиту", "m_proj": "По Проектам", "dl": "📥 Скачать Excel"}
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
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība, Kursi', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA', 'keywords': 'NVA', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True},
        {'name': 'Lessons', 'keywords': 'Lesson, Nodarbība', 'active': True}
    ]

# --- 4. SIDEBAR (STAYS THE SAME) ---
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

# --- 5. MAIN LOGIC & UPDATED EXPORT ---
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
        df_proc['Project Name'] = search_txt.apply(lambda x: classify(x, st.session_state.proj_rules))
        df_proc['Commentary'] = ""

        st.dataframe(df_proc.drop(columns=['_Sign']), use_container_width=True)

        st.divider()
        mode = st.radio(t["mode"], [t["m_sign"], t["m_proj"]])
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
            
            if mode == t["m_sign"]:
                for sign, s_name in [('K', 'Income'), ('D', 'Expenses')]:
                    subset = df_proc[df_proc['_Sign'] == sign].copy()
                    subset[cols].to_excel(writer, index=False, sheet_name=s_name)
            else:
                # SEPARATE INCOME/EXPENSE SHEETS FOR EACH PROJECT
                for p_rule in st.session_state.proj_rules:
                    if p_rule['active']:
                        # Filter rows for this project
                        p_df = df_proc[df_proc['Project Name'] == p_rule['name']].copy()
                        
                        if not p_df.empty:
                            # 1. Project Income Sheet
                            inc_df = p_df[p_df['_Sign'] == 'K'].copy()
                            if not inc_df.empty:
                                sheet_name = f"{p_rule['name']} Income"[:31].strip()
                                inc_df[cols].to_excel(writer, index=False, sheet_name=sheet_name)
                            
                            # 2. Project Expenses Sheet
                            exp_df = p_df[p_df['_Sign'] == 'D'].copy()
                            if not exp_df.empty:
                                sheet_name = f"{p_rule['name']} Expenses"[:31].strip()
                                exp_df[cols].to_excel(writer, index=False, sheet_name=sheet_name)

        st.download_button(t["dl"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
