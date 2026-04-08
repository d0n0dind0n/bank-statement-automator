import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Bank Automator Pro", layout="wide")

st.title("🏦 Bank Statement Automator")

# --- 2. SESSION STATE (Rule Persistence) ---
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

# --- 3. SIDEBAR: RULE MANAGER (Minimizable) ---
with st.sidebar:
    st.header("⚙️ Rule Manager")
    st.info("Edit rules here. These will be applied when you upload the file.")
    
    st.subheader("Categories")
    for i, rule in enumerate(st.session_state.cat_rules):
        with st.expander(f"Category: {rule['name'] if rule['name'] else 'New'}", expanded=False):
            rule['active'] = st.checkbox("Active", value=rule['active'], key=f"cat_on_{i}")
            rule['name'] = st.text_input("Name", value=rule['name'], key=f"cat_name_{i}")
            rule['keywords'] = st.text_area("Keywords", value=rule['keywords'], key=f"cat_key_{i}")
    
    if st.button("➕ Add Category"):
        st.session_state.cat_rules.append({'name': '', 'keywords': '', 'active': True})
        st.rerun()

    st.divider()
    
    st.subheader("Projects")
    for i, rule in enumerate(st.session_state.proj_rules):
        with st.expander(f"Project: {rule['name'] if rule['name'] else 'New'}", expanded=False):
            rule['active'] = st.checkbox("Active", value=rule['active'], key=f"proj_on_{i}")
            rule['name'] = st.text_input("Name", value=rule['name'], key=f"proj_name_{i}")
            rule['keywords'] = st.text_area("Keywords", value=rule['keywords'], key=f"proj_key_{i}")
            
    if st.button("➕ Add Project"):
        st.session_state.proj_rules.append({'name': '', 'keywords': '', 'active': True})
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
    df.columns = ['Account', 'TypeCode', 'Date', 'Partner', 'Purpose', 'Amount', 
                  'Currency', 'Sign', 'ID', 'Code', 'Extra1', 'Extra2']
    
    search_col = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
    df['Category'] = search_col.apply(lambda x: classify(x, st.session_state.cat_rules))
    df['Project Name'] = search_col.apply(lambda x: classify(x, st.session_state.proj_rules))
    df['Commentary'] = ""
    
    output_cols = ['Account', 'Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']
    
    # Split by Sign: K = Credit (Income), D = Debit (Expense)
    credit_df = df[df['Sign'] == 'K'][output_cols]
    debit_df = df[df['Sign'] == 'D'][output_cols]
    
    return credit_df, debit_df

# --- 5. MAIN INTERFACE ---
uploaded_file = st.file_uploader("Upload Bank CSV", type="csv")

if uploaded_file:
    credit_df, debit_df = process_data(uploaded_file)
    
    st.success(f"Processed: {len(credit_df)} Income entries and {len(debit_df)} Expense entries.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Credit (Income) Preview")
        st.dataframe(credit_df.head(10))
    with col_b:
        st.subheader("Debit (Expense) Preview")
        st.dataframe(debit_df.head(10))
    
    # Download as Dual-Sheet Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        credit_df.to_excel(writer, index=False, sheet_name='Credit')
        debit_df.to_excel(writer, index=False, sheet_name='Debit')
    
    st.download_button(
        label="📥 Download Split Sheets Excel",
        data=output.getvalue(),
        file_name=f"Split_Report_{uploaded_file.name.replace('.csv', '.xlsx')}",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
