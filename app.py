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
        "gen_header": "📁 GENERAL RULES",
        "add_btn": "➕ Add New Rule",
        "name": "Name",
        "keywords": "Keywords",
        "success": "Processed: {} Income and {} Expenses",
        "download_mode": "Excel Format",
        "mode_sign": "By Debit/Credit",
        "mode_proj": "By Projects & Rules",
        "download_btn": "📥 Download Excel",
        "reset": "♻️ Reset"
    },
    "Latviešu": {
        "title": "🏦 Bankas automatizācija",
        "upload_label": "Augšupielādēt bankas CSV",
        "rule_manager": "Noteikumu vadība",
        "cat_header": "📁 KATEGORIJAS",
        "proj_header": "📁 PROJEKTI",
        "gen_header": "📁 VISPĀRĪGI NOTEIKUMI",
        "add_btn": "➕ Pievienot jaunu",
        "name": "Nosaukums",
        "keywords": "Atslēgvārdi",
        "success": "Apstrādāts: {} ienākumi un {} izdevumi",
        "download_mode": "Excel formāts",
        "mode_sign": "Pa Debetu/Kredītu",
        "mode_proj": "Pa projektiem un noteikumiem",
        "download_btn": "📥 Lejupielādēt Excel",
        "reset": "♻️ Atiestatīt"
    }
}

# --- 2. CONFIG & DYNAMIC RESPONSIVE STYLE ---
st.set_page_config(page_title="Young Folks Automator", layout="wide")

st.markdown("""
    <style>
    /* Responsive Text: Scales based on sidebar width using clamp */
    [data-testid="stSidebar"] .stText, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] button p {
        font-size: clamp(12px, 1vw, 20px) !important;
    }
    [data-testid="stSidebar"] input {
        font-size: clamp(14px, 1.1vw, 22px) !important;
        font-weight: bold !important;
    }
    /* Button styling */
    .stButton button {
        width: 100%;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SESSION STATE (Rule Storage) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [{'name': 'Transport', 'keywords': 'BOLT, CITYBEE', 'active': True}]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [{'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}]

if 'gen_rules' not in st.session_state:
    st.session_state.gen_rules = [{'name': 'Taxes', 'keywords': 'VID, Nodoklis', 'active': True}]

# --- 4. SIDEBAR ---
with st.sidebar:
    selected_lang = st.selectbox("🌍", options=list(LANGUAGES.keys()), label_visibility="collapsed")
    t = LANGUAGES[selected_lang]
    
    # Logo based on your uploaded image
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
    
    # Helper function to render rule UI
    def render_rules(rule_list, key_prefix):
        for i, rule in enumerate(rule_list):
            c1, c2, c3 = st.columns([0.7, 3, 0.7])
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"{key_prefix}_on_{i}", label_visibility="collapsed")
            rule['name'] = c2.text_input(t["name"], value=rule['name'], key=f"{key_prefix}_n_{i}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"{key_prefix}_del_{i}"):
                rule_list.pop(i)
                st.rerun()
            rule['keywords'] = st.text_area(t["keywords"], value=rule['keywords'], key=f"{key_prefix}_k_{i}", height=70)
            st.divider()

    # SECTION 1: CATEGORIES
    with st.expander(t["cat_header"]):
        render_rules(st.session_state.cat_rules, "cat")
        if st.button(t["add_btn"], key="add_cat_btn"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True})
            st.rerun()

    # SECTION 2: PROJECTS
    with st.expander(t["proj_header"]):
        render_rules(st.session_state.proj_rules, "proj")
        if st.button(t["add_btn"], key="add_proj_btn"):
            st.session_state.proj_rules.append({'name': 'New Project', 'keywords': '', 'active': True})
            st.rerun()

    # SECTION 3: GENERAL RULES (Added as per your request)
    with st.expander(t["gen_header"]):
        render_rules(st.session_state.gen_rules, "gen")
        if st.button(t["add_btn"], key="add_gen_btn"):
            st.session_state.gen_rules.append({'name': 'New General Rule', 'keywords': '', 'active': True})
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
        df['Project Name'] = search_col.apply(lambda x: classify(x, st.session_state.proj_rules))
        df['General Rule'] = search_col.apply(lambda x: classify(x, st.session_state.gen_rules))
        df['Commentary'] = ""
        
        # Filter out balance turnover rows
        df = df[~df['Purpose'].str.contains('balance|Turnover|atlikums|Apgrozījums', case=False, na=False)]
        
        cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'General Rule', 'Commentary']
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
                # Combine Projects and General Rules for sheet creation
                all_rule_sets = [
                    (st.session_state.proj_rules, 'Project Name'),
                    (st.session_state.gen_rules, 'General Rule')
                ]
                
                found_any = False
                for rule_list, col_name in all_rule_sets:
                    active_names = [r['name'] for r in rule_list if r['active'] and r['name']]
                    for name in active_names:
                        sub_df = df[df[col_name] == name]
                        if not sub_df.empty:
                            safe = name[:24].replace('/', '_')
                            sub_df[sub_df['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name=f"{safe} CR")
                            sub_df[sub_df['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name=f"{safe} DB")
                            found_any = True
                
                # General Catch-all (anything not classified by project or general rule)
                catch_all = df[(df['Project Name'] == "") & (df['General Rule'] == "")]
                if not catch_all.empty:
                    catch_all[catch_all['Sign'] == 'K'][cols].to_excel(writer, index=False, sheet_name='Unclassified CR')
                    catch_all[catch_all['Sign'] == 'D'][cols].to_excel(writer, index=False, sheet_name='Unclassified DB')

        st.download_button(t["download_btn"], output.getvalue(), "YoungFolks_Report.xlsx")
    except Exception as e:
        st.error(f"Error: {e}")
