import streamlit as st
import pandas as pd
import io

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Bank Statement Automator", layout="wide")

st.title("🏦 Bank Statement Automator")
st.markdown("""
Upload your bank CSV, define your rules in the sidebar, and download the categorized file.
""")

# --- 2. SIDEBAR: MANAGE RULES ---
st.sidebar.header("⚙️ Classification Rules")
st.sidebar.info("Separate keywords with commas (e.g., *ziedojums, dāvinājums*)")

# Editable Categories
st.sidebar.subheader("Categories")
cat_fees = st.sidebar.text_input("Membership Fees", "dalības maksa, biedru nauda, dalibmaksa, biedru")
cat_donations = st.sidebar.text_input("Donations", "ziedojums, donation")
cat_bank = st.sidebar.text_input("Bank Fees", "komisija, apkalpošanas maksa, maksa par")
cat_edu = st.sidebar.text_input("Education", "nodarbiba, risunok, gleznieciba, lekcija, latv.valoda")

# Editable Projects
st.sidebar.subheader("Project Names")
proj_nva = st.sidebar.text_input("NVA Project", "NVA-20, 8.3-8.1/193-2025, 8.3-8.1")
proj_yf = st.sidebar.text_input("Young Folks", "Young Folks, YF")

# --- 3. PROCESSING LOGIC ---
def get_rules_dict(input_string):
    return [x.strip() for x in input_string.split(",")]

def classify(text, rules_map):
    if pd.isna(text): return "Other"
    text = str(text).lower()
    for label, keywords in rules_map.items():
        for word in keywords:
            if word.lower() in text and word != "":
                return label
    return "Other"

def process_data(file, cat_map, proj_map):
    # Your specific CSV format uses ';' delimiter
    df = pd.read_csv(file, sep=';', header=None)
    
    # Standard column mapping for your bank file
    df.columns = ['Account', 'TypeCode', 'Date', 'Partner', 'Purpose', 'Amount', 
                  'Currency', 'Sign', 'ID', 'Code', 'Extra1', 'Extra2']
    
    df['search_text'] = df['Partner'].fillna('') + " " + df['Purpose'].fillna('')
    
    # Apply the rules from the sidebar
    df['Category'] = df['search_text'].apply(lambda x: classify(x, cat_map))
    df['Project Name'] = df['search_text'].apply(lambda x: classify(x, proj_map))
    
    # Auto-commentary based on Sign (K=Income, D=Expense)
    df['Commentary'] = df['Sign'].map({'K': 'Income / Received', 'D': 'Expense / Paid'}).fillna('Other')
    
    return df.drop(columns=['search_text'])

# --- 4. MAIN APP INTERFACE ---
uploaded_file = st.file_uploader("Upload your bank CSV file", type="csv")

if uploaded_file:
    # Build the rules maps from sidebar inputs
    active_categories = {
        'Membership Fees': get_rules_dict(cat_fees),
        'Donations': get_rules_dict(cat_donations),
        'Bank Fees': get_rules_dict(cat_bank),
        'Education': get_rules_dict(cat_edu)
    }
    
    active_projects = {
        'NVA Project': get_rules_dict(proj_nva),
        'Young Folks': get_rules_dict(proj_yf)
    }

    with st.spinner('Categorizing...'):
        result_df = process_data(uploaded_file, active_categories, active_projects)
        
        st.success("Done! Preview of categorized data:")
        st.dataframe(result_df[['Date', 'Partner', 'Purpose', 'Amount', 'Category', 'Project Name', 'Commentary']].head(15))
        
        # Prepare Excel download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, index=False, sheet_name='Monthly Report')
        
        st.download_button(
            label="📥 Download Enriched Excel File",
            data=output.getvalue(),
            file_name=f"Report_{uploaded_file.name.replace('.csv', '.xlsx')}",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
