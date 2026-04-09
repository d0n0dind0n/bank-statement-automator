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
        "add_list_btn": "➕ Create New Rule List",
        "add_rule_btn": "➕ Add Rule",
        "name": "Name",
        "keywords": "Keywords",
        "success": "Processed: {} Income and {} Expenses",
        "download_mode": "Excel Format",
        "mode_sign": "By Debit/Credit",
        "mode_proj": "By All Custom Lists",
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
    }
}

# --- 2. CONFIG & FORCE SCALING CSS ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

# This CSS uses container-query logic to scale text based on the sidebar width
st.markdown("""
    <style>
    /* Force scaling for text and icons in the sidebar */
    [data-testid="stSidebar"] {
        container-type: inline-size;
    }
    @container (min-width: 350px) {
        [data-testid="stSidebar"] * {
            font-size: 1.1rem !important;
        }
    }
    @container (min-width: 500px) {
        [data-testid="stSidebar"] * {
            font-size: 1.4rem !important;
        }
    }
    /* Make buttons and inputs fill space */
    .stButton button, .stTextInput input, .stTextArea textarea {
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE (Rule Storage) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [{'name': 'Transport', 'keywords': 'BOLT', 'active': True}]

if 'custom_lists' not in st.session_state:
    # This stores your dynamic rule lists (e.g., Projects, Taxes, etc.)
    st.session_state.custom_lists = [
        {'title': 'PROJECTS', 'rules': [{'name': 'Young Folks', 'keywords': 'YF', 'active': True}]}
    ]

# --- 4. SIDEBAR ---
with st.sidebar:
    selected_lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    try:
        st.image("YoungFolks-circle-42.png", use_container_width=True)
    except:
        st.write("### YOUNG FOLKS")

    st.divider()
    
    h_col, r_col = st.columns([2, 1])
    h_col.subheader(t["rule_manager"])
    if r_col.button(t["reset"]):
        st.session_state.clear()
        st.rerun()

    # SECTION: CATEGORIES (Fixed)
    with st.expander(t["cat_header"]):
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([0.7, 3, 0.7])
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"cat_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input(t["name"], value=rule['name'], key=f"cat_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"cat_del_{i}"):
                st.session_state.cat_rules.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"cat_k_{i}", height=60)
            st.divider()
        if st.button(t["add_rule_btn"], key="add_cat_rule"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True})
            st.rerun()

    # SECTION: DYNAMIC RULE LISTS
    for list_idx, r_list in enumerate(st.session_state.custom_lists):
        with st.expander(f"📁 {r_list['title']}"):
            # Edit List Title
            r_list['title'] = st.text_input("List Name", value=r_list['title'], key=f"list_title_{list_idx}")
            if st.button(f"🗑️ Delete Entire List: {r_list['title']}", key=f"del_list_{list_idx}"):
                st.session_state.custom_lists.pop(list_idx)
                st.rerun()
            st.divider()
            
            # Rules within this list
            for i, rule in enumerate(r_list['rules']):
                p1, p2, p3 = st.columns([0.7, 3, 0.7])
                rule['active'] = p1.checkbox("On", value=rule['active'], key=f"l_{list_idx}_on_{i}", label_visibility="collapsed")
                rule['name'] = p2.text_input(t["name"], value=rule['name'], key=f"l_{list_idx}_n_{i}", label_visibility="collapsed")
                if p3.button("🗑️", key=f"l_{list_idx}_del_{i}"):
                    r_list['rules'].pop(i)
                    st.rerun()
                rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"l_{list_idx}_k_{i}", height=60)
                st.divider()
            
            if st.button(t["add_rule_btn"], key=f"add_rule_{list_idx}"):
                r_list['rules'].append({'name': 'New Rule', 'keywords': '', 'active': True})
                st.rerun()

    st.divider()
    # BLUE AREA: BUTTON TO CREATE NEW LISTS
    if st.button(t["add_list_btn"], type="primary"):
        st.session_state.custom_lists.append({'title': 'NEW LIST', 'rules': []})
        st.rerun()

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
        
        # Apply all custom lists
        for r_list in st.session_state.custom_lists:
            df[r_list['title']] = search_col.apply(lambda x: classify(x, r_list['rules']))
        
        df = df[~df['Purpose'].str.contains('balance|Turnover|atlikums', case=False, na=False)]
        st.dataframe(df, use_container_width=True)

        st.divider()
        mode = st.radio(t["download_mode"], [t["mode_sign"], t["mode_proj"]])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if mode == t["mode_sign"]:
                df[df['Sign'] == 'K'].to_excel(writer, index=False, sheet_name='Income')
                df[df['Sign'] == 'D'].to_excel(writer, index=False, sheet_name='Expenses')
            else:
                for r_list in st.session_state.custom_lists:
                    col = r_list['title']
                    unique_names = df[df[col] != ""][col].unique()
                    for name in unique_names:
                        sub = df[df[col] == name]
                        safe = str(name)[:24].replace('/', '_')
                        sub.to_excel(writer, index=False, sheet_name=f"{safe}")

        st.download_button(t["download_btn"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
