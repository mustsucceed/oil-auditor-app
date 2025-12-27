import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
from io import StringIO

# --- CONFIGURATION ---
st.set_page_config(page_title="VisaVault Pro", page_icon="🛡️", layout="wide")

# --- SECURE API ---
try:
    if "GROQ_API_KEY" in st.secrets:
        API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        st.error("🚨 API Key Missing.")
        st.stop()
except:
    st.warning("⚠️ Local Run? Check secrets.toml")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("🛡️ VisaVault")
page = st.sidebar.radio("Menu", ["🏠 Home", "🛂 Visa Auditor"])

# --- HELPER ---
def clean_money(val):
    if not val: return 0.0
    s = str(val).replace(",", "").replace("₦", "").replace("Dr", "").replace("Cr", "").strip()
    try:
        return float(s)
    except:
        return 0.0

if page == "🏠 Home":
    st.title("DataFlow Automations")
    st.info("Select 'Visa Auditor' in the sidebar.")

elif page == "🛂 Visa Auditor":
    st.title("🛂 Visa Statement Auditor")
    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")
    salary = st.number_input("Client Salary (₦)", value=200000, step=10000)

    if st.button("🚀 Run Audit") and uploaded_file:
        status = st.empty()
        status.info("Reading PDF...")

        try:
            # 1. GET TEXT
            with pdfplumber.open(uploaded_file) as pdf:
                text_data = ""
                for p in pdf.pages[:4]: 
                    text_data += p.extract_text() or ""
            
            if len(text_data) < 50:
                st.error("❌ Error: Scanned Image detected. Use a digital PDF.")
                st.stop()

            # 2. ASK AI (PIPE SEPARATOR, NO HEADERS)
            status.info("AI Analyzing...")
            client = Groq(api_key=API_KEY)
            
            prompt = f"""
            Extract bank transactions from this text.
            Return ONLY raw data separated by PIPES (|).
            Do NOT return a header row.
            Format: Date | Description | Credit_Amount | Debit_Amount | Balance
            Rules:
            - If Credit is empty/missing, put 0.
            - If Debit is empty/missing, put 0.
            - Do not write 'Here is the data'. Just the data.
            
            TEXT:
            {text_data[:6000]}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_ai_text = resp.choices[0].message.content

            # 3. FORCE-FIELD PARSING
            # Remove any intro text, keep only lines with Pipes |
            valid_lines = [line for line in raw_ai_text.split('\n') if "|" in line]
            clean_csv = "\n".join(valid_lines)
            
            if not valid_lines:
                st.error("AI could not find transaction data.")
                st.stop()

            # READ WITH NO HEADER (header=None)
            df = pd.read_csv(StringIO(clean_csv), sep="|", header=None, on_bad_lines='skip')
            
            # 4. MANUALLY NAME COLUMNS (The Fix for 'Error: Credit')
            # We assume the AI followed the order: Date, Desc, Credit, Debit, Balance
            # We check how many columns we actually got
            col_count = df.shape[1]
            
            if col_count >= 5:
                df.columns = ["Date", "Description", "Credit", "Debit", "Balance"] + [f"Col{i}" for i in range(5, col_count)]
                # Drop extra columns if any
                df = df[["Date", "Description", "Credit", "Debit", "Balance"]]
            elif col_count == 4:
                # Sometimes AI misses Balance column
                df.columns = ["Date", "Description", "Credit", "Debit"]
                df["Balance"] = 0
            else:
                st.error(f"Structure Error: AI returned {col_count} columns instead of 5.")
                st.write("Raw Data Preview:", df.head())
                st.stop()

            # 5. CLEAN DATA
            for col in ["Credit", "Debit", "Balance"]:
                df[col] = df[col].apply(clean_money)

            status.success("✅ Data Extracted!")
            
            # 6. RISK CHECK
            flags = []
            limit = salary * 3
            suspicious = df[(df['Credit'] > limit) & (~df['Description'].str.contains('SALARY', case=False, na=False))]
            
            for _, row in suspicious.iterrows():
                flags.append(f"🚩 **LUMP SUM:** ₦{row['Credit']:,.2f} on {row['Date']}")

            # DISPLAY
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("Total Inflow", f"₦{df['Credit'].sum():,.2f}")
            c2.metric("Closing Balance", f"₦{df.iloc[-1]['Balance']:,.2f}")
            
            st.subheader("⚠️ Audit Report")
            if flags:
                for f in flags: st.error(f)
            else:
                st.success("✅ Clean Sheet.")
            
            st.dataframe(df)

        except Exception as e:
            st.error(f"System Error: {e}")
