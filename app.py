import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
from io import StringIO

# --- 1. CONFIGURATION (Must be first) ---
st.set_page_config(page_title="DataFlow Automations", page_icon="🔒", layout="wide")

# --- 2. PASSWORD PROTECTION SYSTEM ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.markdown("## 🔒 Restricted Access")
        st.text_input(
            "Please enter the Client Access Key:", type="password", on_change=password_entered, key="password"
        )
        st.info("To purchase an access key, contact support: [+234 905 143 9712]")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again.
        st.markdown("## 🔒 Restricted Access")
        st.text_input(
            "Please enter the Client Access Key:", type="password", on_change=password_entered, key="password"
        )
        st.error("❌ Access Denied. Incorrect Key.")
        return False
    else:
        # Password correct.
        return True

# 🛑 STOP HERE IF PASSWORD IS WRONG
if not check_password():
    st.stop()

# --- 3. SECURE API CONNECTION ---
try:
    if "GROQ_API_KEY" in st.secrets:
        API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        st.error("🚨 Configuration Error: GROQ_API_KEY missing in Secrets.")
        st.stop()
except:
    st.warning("⚠️ Local Run? Check secrets.toml")
    st.stop()

# --- 4. SIDEBAR NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
st.sidebar.title("Navigation")
st.sidebar.success("🔓 Logged In")
if st.sidebar.button("Log Out"):
    del st.session_state["password_correct"]
    st.rerun()

page = st.sidebar.radio("Go to:", ["🏠 Home / Portfolio", "🛂 Visa Statement Auditor"])

# --- 5. HELPER FUNCTION ---
def clean_money(val):
    if not val: return 0.0
    s = str(val).replace(",", "").replace("₦", "").replace("Dr", "").replace("Cr", "").strip()
    try:
        return float(s)
    except:
        return 0.0

# ==========================================
# PAGE 1: HOME
# ==========================================
if page == "🏠 Home / Portfolio":
    st.title("🚀 DataFlow Automations Nigeria")
    st.markdown("### We turn piles of Paperwork into Profit.")
    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("👋 **Status:** Open for Business")
        st.markdown("**📍 Location:** Lagos, Nigeria")
        st.markdown("🟢 **Server:** Secure & Encrypted")

    with col2:
        st.markdown("""
        ### Hi, I am a Python Automation Specialist.
        
        I build custom AI tools for Nigerian businesses to eliminate manual data entry.
        
        **My Solutions:**
        * **For Logistics:** I convert scanned Waybills & Invoices into Excel instantly.
        * **For Travel Agents:** I audit Bank Statements for 'Visa Risks' (Lump Sums) in seconds.
        
        👉 **Select a tool from the Sidebar to start.**
        """)

# ==========================================
# PAGE 2: LOGISTICS AUDITOR
# ==========================================
# elif page == "🚛 Logistics Auditor":
#     st.title("🚛 Logistics Document Processor")
#     st.markdown("Extract data from Invoices, Waybills, and Manifests.")
    
#     uploaded_files = st.file_uploader("Upload Logistics PDFs", type="pdf", accept_multiple_files=True)
    
#     if st.button("🚀 Process Waybills") and uploaded_files:
#         client = Groq(api_key=API_KEY)
#         master_data = []
#         bar = st.progress(0)
        
#         for idx, file in enumerate(uploaded_files):
#             try:
#                 with pdfplumber.open(file) as pdf:
#                     text = pdf.pages[0].extract_text() or ""
                
#                 # Logistics Prompt
#                 prompt = f"""
#                 Extract 4 fields. Return ONLY a CSV line separated by PIPES (|).
#                 Format: Date | Waybill_Number | Vendor_Name | Total_Amount
#                 Text: {text[:4000]}
#                 """
                
#                 resp = client.chat.completions.create(
#                     model="llama-3.1-8b-instant",
#                     messages=[{"role": "user", "content": prompt}]
#                 )
                
#                 line = resp.choices[0].message.content
#                 parts = line.split('|')
                
#                 master_data.append({
#                     "File": file.name,
#                     "Date": parts[0].strip() if len(parts)>0 else "-",
#                     "Waybill #": parts[1].strip() if len(parts)>1 else "-",
#                     "Vendor": parts[2].strip() if len(parts)>2 else "-",
#                     "Amount": parts[3].strip() if len(parts)>3 else "0"
#                 })
#             except Exception as e:
#                 st.error(f"Error on {file.name}: {e}")
            
#             bar.progress((idx+1)/len(uploaded_files))
            
#         if master_data:
#             st.success("Processing Complete!")
#             st.dataframe(pd.DataFrame(master_data))

# ==========================================
# PAGE 3: VISA AUDITOR (The Fixed Version)
# ==========================================
elif page == "🛂 Visa Statement Auditor":
    st.title("🛂 Visa Risk Auditor")
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

            # 2. ASK AI
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
            
            TEXT:
            {text_data[:6000]}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_ai_text = resp.choices[0].message.content

            # 3. CLEAN & PARSE
            valid_lines = [line for line in raw_ai_text.split('\n') if "|" in line]
            clean_csv = "\n".join(valid_lines)
            
            if not valid_lines:
                st.error("AI could not find transaction data.")
                st.stop()

            df = pd.read_csv(StringIO(clean_csv), sep="|", header=None, on_bad_lines='skip')
            
            # 4. FORCE COLUMNS
            col_count = df.shape[1]
            if col_count >= 5:
                df.columns = ["Date", "Description", "Credit", "Debit", "Balance"] + [f"Col{i}" for i in range(5, col_count)]
                df = df[["Date", "Description", "Credit", "Debit", "Balance"]]
            elif col_count == 4:
                df.columns = ["Date", "Description", "Credit", "Debit"]
                df["Balance"] = 0

            # 5. CLEAN DATA
            for col in ["Credit", "Debit", "Balance"]:
                if col in df.columns:
                    df[col] = df[col].apply(clean_money)

            status.success("✅ Data Extracted!")
            
            # 6. RISK CHECK
            flags = []
            limit = salary * 3
            if 'Credit' in df.columns:
                suspicious = df[(df['Credit'] > limit) & (~df['Description'].str.contains('SALARY', case=False, na=False))]
                for _, row in suspicious.iterrows():
                    flags.append(f"🚩 **LUMP SUM:** ₦{row['Credit']:,.2f} on {row['Date']}")

            # DISPLAY
            st.divider()
            if 'Credit' in df.columns:
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



