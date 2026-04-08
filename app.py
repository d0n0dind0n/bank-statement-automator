import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Bank Automator Pro", layout="wide")

st.title("🏦 Custom Bank Statement Automator")
st.markdown("Upload your file, manage rules below, and download the cleaned Excel.")

# --- 2. SESSION STATE (To remember added categories/projects) ---
if 'cat_rules' not in st.session_state:
    st.session_state.cat_rules = [
        {'name': 'Membership Fees', 'keywords': 'dalības maksa, biedru nauda', 'active': True},
        {'name': 'Donations', 'keywords': 'ziedojums, donation', 'active': True},
        {'name': 'Bank Fees', 'keywords': 'komisija, apkalpošanas maksa', 'active': True}
    ]

if 'proj_rules' not in st.session_state:
    st.session_state.proj_rules = [
        {'name': 'NVA Project', 'keywords': 'NVA-20, 8.3-8.1', 'active': True},
        {'name': 'Young Folks', 'keywords': 'Young Folks, YF', 'active': True}
    ]

# --- 3. SIDEBAR / SETTINGS: DYNAMIC RULES ---
with st.expander("🛠️ Manage Categories & Projects (Add, Edit, Deactivate)"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Categories")
        for i, rule in enumerate(st.session_state.cat_rules):
            c1, c2, c3 = st.columns([1, 3, 1])
            rule['active'] = c1.checkbox("On", value=rule['active'], key=f"cat_on_{i}")
            rule['name'] = c2.text_input("Category Name", value=rule['name'], key=f"cat_name_{i}")
            rule['keywords'] = c2.text_area("Keywords (comma separated)", value=rule['keywords'], key=f"cat_key_{i}")
        
        if st.button("➕ Add New Category"):
            st.session_state.cat_rules.append({'name': 'New Category', 'keywords': '', 'active': True})
            st.rerun()

    with col2:
        st.subheader("Projects")
        for i, rule in enumerate(st.session_state.proj_rules):
            p1, p2, p3 = st.columns([1, 3, 1])
            rule['active'] = p1.checkbox("On", value=rule['active'], key=f"proj_on_{i}")
            rule['name'] = p2.text_input("Project Name", value=rule['name'], key=f"proj_name_{i}")
            rule['keywords'] = p2.text_area("Keywords (comma separated)", value=rule['keywords'], key=f"proj_key_{i}")
        
        if st.button("➕ Add New Project"):
            st.session_state.proj_rules.append({'name': 'New Project', 'keywords': '', 'active': True})
            st.rerun()

# --- 4. PROCESSING LOGIC ---
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
    # Bank structure
    df.columns = ['Account', 'TypeCode', 'Date', 'Partner', 'Purpose', 'Amount', 
                  'Currency', 'Sign', 'ID', 'Code', 'Extra1', 'Extra2']
    
    search_col = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
    
    df['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
    df['Project Name'] = search_col.apply(lambda x: classify(x, st.session_state.proj_rules))
    df['Commentary'] = "" # Keep blank as requested
    
    # Final column selection
    output_cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
    return df[output_cols]

# --- 5. MAIN INTERFACE ---
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    result_df = process_data(uploaded_file)
    st.success("File processed successfully!")
    st.dataframe(result_df)
    
    # Download as Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        result_df.to_excel(writer, index=False, sheet_name='Report')
    
    st.download_button(
        label="📥 Download Result (Excel)",
        data=output.getvalue(),
        file_name=f"Clean_Report_{uploaded_file.name.replace('.csv', '.xlsx')}",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
