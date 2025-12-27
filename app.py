import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
from io import StringIO

# --- CONFIGURATION ---
st.set_page_config(page_title="VisaVault Pro", page_icon="🛡️", layout="wide")

# --- API KEY CHECK ---
try:
    if "GROQ_API_KEY" in st.secrets:
        API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        st.error("🚨 API Key not found. Please check your Secrets.")
        st.stop()
except:
    st.warning("⚠️ Running Locally? Ensure .streamlit/secrets.toml exists.")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("🛡️ VisaVault")
st.sidebar.info("System Status: Online")

# --- HELPER FUNCTION ---
def clean_money(val):
    if not val: return 0.0
    # Clean standard currency formatting
    clean = str(val).replace(",", "").replace("₦", "").replace("DR", "").replace("CR", "").strip()
    try:
        return float(clean)
    except:
        return 0.0

# --- MAIN APP ---
st.title("🛡️ Visa Statement Auditor (Final Fix)")
st.markdown("### This version uses 'Tabs' to prevent comma errors.")

uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")
salary = st.number_input("Declared Monthly Salary (₦)", value=200000, step=10000)

if st.button("🚀 Run Audit") and uploaded_file:
    status = st.empty()
    status.info("⏳ Reading PDF...")

    try:
        # 1. EXTRACT TEXT
        with pdfplumber.open(uploaded_file) as pdf:
            text_data = ""
            # Scanning first 4 pages is usually enough for a quick audit
            for p in pdf.pages[:4]: 
                extracted = p.extract_text()
                if extracted: text_data += extracted
        
        # Check if PDF is empty (Scanned Image Check)
        if len(text_data) < 50:
            st.error("❌ ERROR: This looks like a scanned image. Please use a digital PDF.")
            st.stop()

        # 2. AI EXTRACTION (THE TAB STRATEGY)
        status.info("🤖 AI Analyzing...")
        client = Groq(api_key=API_KEY)
        
        prompt = f"""
        You are a Data Extractor.
        Extract the transaction rows from this bank statement.
        
        RULES:
        1. Return ONLY raw data. No introduction. No markdown.
        2. Separate columns using TABS (\\t). Do NOT use commas.
        3. Columns must be: Date, Description, Credit, Debit, Balance.
        4. If a value is missing, put 0.
        
        DATA:
        {text_data[:6000]}
        """
        
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_data = resp.choices[0].message.content
        
        # 3. ROBUST PARSING
        # We process line by line to remove any AI "chatter"
        clean_lines = []
        lines = raw_data.split('\n')
        
        header = "Date\tDescription\tCredit\tDebit\tBalance"
        clean_lines.append(header)
        
        for line in lines:
            # Only keep lines that look like data (have tabs)
            if "\t" in line and "Date" not in line:
                clean_lines.append(line)
        
        final_csv_string = "\n".join(clean_lines)
        
        # Load into Pandas using Separator = TAB (\t)
        # on_bad_lines='skip' ensures it NEVER crashes even if a line is broken
        df = pd.read_csv(StringIO(final_csv_string), sep='\t', on_bad_lines='skip')
        
        # 4. CLEANING & MATH
        # Ensure columns exist
        needed_cols = ["Credit", "Debit", "Balance"]
        for col in needed_cols:
            if col not in df.columns: df[col] = 0
            df[col] = df[col].apply(clean_money)
            
        status.success("✅ Extraction Complete!")
        
        # 5. RISK CHECKING
        flags = []
        limit = salary * 3
        
        # Lump Sum Detector
        if 'Credit' in df.columns:
            suspicious = df[
                (df['Credit'] > limit) & 
                (~df['Description'].str.contains('SALARY', case=False, na=False))
            ]
            for _, row in suspicious.iterrows():
                flags.append(f"🚩 **LUMP SUM:** ₦{row['Credit']:,.2f} on {row['Date']}")

        # 6. DISPLAY RESULTS
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Total Inflow", f"₦{df['Credit'].sum():,.2f}")
        c2.metric("Closing Balance", f"₦{df.iloc[-1]['Balance']:,.2f}" if not df.empty else "0")
        
        st.subheader("⚠️ Audit Report")
        if flags:
            for f in flags: st.error(f)
        else:
            st.success("✅ clean Sheet. No obvious risks found.")
            
        with st.expander("View Full Data"):
            st.dataframe(df)

    except Exception as e:
        st.error(f"System Error: {e}")
        st.warning("Debugging Hint: Check if your API Key is correct in Secrets.")
