import streamlit as st
import pandas as pd
import io

# --- 1. LANGUAGES ---
LANGUAGES = {
    "English": {
        "title": "🏦 Bank Statement Automator",
        "upload_label": "Upload Bank CSV",
        "rule_manager": "Rule Manager",
        "cat_header": "📁 CATEGORIES",
        "proj_header": "📁 PROJECTS",
        "add_list_btn": "➕ Create New Rule List",
        "add_rule_btn": "➕ Add Rule",
        "name": "Name",
        "keywords": "Keywords",
        "success": "Processed: {} Income and {} Expenses",
        "download_mode": "Excel Format",
        "mode_sign": "By Debit/Credit",
        "mode_proj": "By Custom Lists",
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
        "success": "Apstrādāts: {} ienākumi un {} izdevumi",
        "download_mode": "Excel formāts",
        "mode_sign": "Pa Debetu/Kredītu",
        "mode_proj": "Pa visiem sarakstiem",
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
        "success": "Обработано: {} доходов и {} расходов",
        "download_mode": "Формат Excel",
        "mode_sign": "По Дебету/Кредиту",
        "mode_proj": "По спискам правил",
        "download_btn": "📥 Скачать Excel",
        "reset": "♻️ Сброс"
    }
}

# --- 2. CONFIG & SCALING CSS ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    /* Scaling Text based on Sidebar Width */
    [data-testid="stSidebarContent"] { container-type: inline-size; }
    @container (min-width: 0px) { [data-testid="stSidebarContent"] * { font-size: calc(12px + 0.1cqw) !important; } }
    @container (min-width: 450px) { [data-testid="stSidebarContent"] * { font-size: calc(14px + 0.5cqw) !important; } }

    /* Tighten horizontal spacing between checkbox, input, and trash */
    [data-testid="column"] { 
        padding-left: 2px !important; 
        padding-right: 2px !important;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 5px !important;
    }

    /* Logo Styling */
    .logo-container-bottom {
        display: flex;
        justify-content: center;
        margin-top: 40px;
        margin-bottom: 20px;
    }
    .logo-container-bottom img {
        width: 100px;
        height: 100px;
        object-fit: contain;
    }

    /* Full width buttons */
    .stButton button { width: 100% !important; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Transport', 'keywords': 'BOLT, CITYBEE', 'active': True},
        {'name': 'Membership Fees', 'keywords': 'Biedru nauda', 'active': True},
        {'name': 'Project Funding', 'keywords': 'NVA, Erasmus', 'active': True},
        {'name': 'Education', 'keywords': 'Lekcija, Nodarbība', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'Komisija', 'active': True},
        {'name': 'Donations', 'keywords': 'Ziedojums', 'active': True}
    ]

if 'custom_lists' not in st.session_state:
    st.session_state.custom_lists = [
        {
            'title': 'PROJECTS', 
            'rules': [
                {'name': 'LESSONS', 'keywords': 'Lesson, Nodarbība', 'active': True},
                {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
            ]
        }
    ]

# --- 4. SIDEBAR ---
with st.sidebar:
    # Language selector top left
    selected_lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    st.divider()
    
    # Rule Manager Header
    h_col, r_col = st.columns([2, 1])
    h_col.subheader(t["rule_manager"])
    if r_col.button(t["reset"]):
        st.session_state.clear()
        st.rerun()

    # CATEGORIES SECTION
    with st.expander(t["cat_header"]):
        for i, rule in enumerate(st.session_state.cat_rules):
            # Column ratios adjusted to keep elements close
            c1, c2, c3 = st.columns([0.4, 3, 0.4]) 
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"cat_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input(t["name"], value=rule['name'], key=f"cat_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"cat_del_{i}"):
                st.session_state.cat_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"cat_k_{i}", height=60)
            st.divider()
        if st.button(t["add_rule_btn"], key="add_cat"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True})
            st.rerun()

    # DYNAMIC LISTS SECTION
    for idx, r_list in enumerate(st.session_state.custom_lists):
        with st.expander(f"📁 {r_list['title']}"):
            col_lt, col_ld = st.columns([3, 1])
            r_list['title'] = col_lt.text_input("List Name", value=r_list['title'], key=f"lt_{idx}")
            if col_ld.button("🗑️ List", key=f"ld_{idx}"):
                st.session_state.custom_lists.pop(idx)
                st.rerun()
            
            st.divider()
            for i, rule in enumerate(r_list['rules']):
                p1, p2, p3 = st.columns([0.4, 3, 0.4])
                rule['active'] = p1.checkbox("On", value=rule['active'], key=f"l_{idx}_on_{i}", label_visibility="collapsed")
                rule['name'] = p2.text_input(t["name"], value=rule['name'], key=f"l_{idx}_n_{i}", label_visibility="collapsed")
                if p3.button("🗑️", key=f"l_{idx}_del_{i}"):
                    r_list['rules'].pop(i)
                    st.rerun()
                rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"l_{idx}_k_{i}", height=60)
                st.divider()
            
            if st.button(t["add_rule_btn"], key=f"ar_{idx}"):
                r_list['rules'].append({'name': 'New Rule', 'keywords': '', 'active': True})
                st.rerun()

    # Create New List
    if st.button(t["add_list_btn"], type="primary"):
        st.session_state.custom_lists.append({'title': 'NEW LIST', 'rules': []})
        st.rerun()

    # Logo Bottom Center
    st.markdown('<div class="logo-container-bottom">', unsafe_allow_html=True)
    try:
        st.image("YoungFolks-circle-42.png")
    except:
        pass
    st.markdown('</div>', unsafe_allow_html=True)

# --- 5. MAIN LOGIC ---
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
        df.rename(columns={0:'Account', 2:'Date', 3:'Partner', 4:'Purpose', 5:'Amount', 7:'Sign'}, inplace=True)
        search_col = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
        
        df['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
        for r_list in st.session_state.custom_lists:
            df[r_list['title']] = search_col.apply(lambda x: classify(x, r_list['rules']))
        
        st.dataframe(df, use_container_width=True)

        st.divider()
        mode = st.radio(t["download_mode"], [t["mode_sign"], t["mode_proj"]])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if mode == t["mode_sign"]:
                df[df['Sign'] == 'K'].to_excel(writer, index=False, sheet_name='Income')
                df[df['Sign'] == 'D'].to_excel(writer, index=False, sheet_name='Expenses')
            else:
                # Custom Export based on your lists
                for r_list in st.session_state.custom_lists:
                    col = r_list['title']
                    for name in df[df[col] != ""][col].unique():
                        df[df[col] == name].to_excel(writer, index=False, sheet_name=str(name)[:31])

        st.download_button(t["download_btn"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
