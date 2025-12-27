import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
from io import StringIO

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="DataFlow Automations", page_icon="🚀", layout="wide")

# --- 2. SECURE API CONNECTION ---
# This block automatically grabs the key from the cloud.
# It does NOT allow you to type it in the code.
try:
    if "GROQ_API_KEY" in st.secrets:
        API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        # If the secret name is wrong or missing
        st.error("🚨 Configuration Error: API Key not found.")
        st.info("Go to Streamlit Dashboard -> Settings -> Secrets and add: GROQ_API_KEY = 'your_key'")
        st.stop() # Stops the app here to prevent crashes
except FileNotFoundError:
    # This happens if you run it locally without a secrets.toml file
    st.warning("⚠️ Running Locally? You need a .streamlit/secrets.toml file.")
    st.stop()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
st.sidebar.title("Navigation")
st.sidebar.success("✅ System Online") # Visual confirmation that Key is working
page = st.sidebar.radio("Go to:", ["🏠 Home / Portfolio", "🚛 Logistics Auditor", "🛂 Visa Statement Auditor"])

# --- 4. HELPER FUNCTIONS (Shared Tools) ---
def clean_money(text):
    """Converts text like '₦1,000,000.00' into a number python can do math with."""
    if not text: return 0.0
    # Remove currency symbols and commas
    clean = str(text).replace(",", "").replace("₦", "").replace("$", "").strip()
    try:
        return float(clean)
    except:
        return 0.0

# ==========================================
# PAGE 1: HOME / PORTFOLIO
# ==========================================
if page == "🏠 Home / Portfolio":
    
    st.title("🚀 DataFlow Automations Nigeria")
    st.markdown("### We turn piles of Paperwork into Profit.")
    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.info("👋 **Status:** Open for Business")
        st.markdown("**📍 Location:** Lagos, Nigeria")
        # You can add your contact info here if you want
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
    
    st.divider()
    st.image("https://raw.githubusercontent.com/streamlit/docs/main/public/images/static_table.png", caption="Sample Output")


# ==========================================
# PAGE 2: LOGISTICS AUDITOR (Waybills)
# ==========================================
elif page == "🚛 Logistics Auditor":
    
    st.title("🚛 Logistics Document Processor")
    st.markdown("Extract data from Invoices, Waybills, and Manifests.")
    
    uploaded_files = st.file_uploader("Upload Logistics PDFs", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Process Waybills") and uploaded_files:
        # Initialize the AI Client using the Secure Key
        client = Groq(api_key=API_KEY)
        master_data = []
        bar = st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            try:
                with pdfplumber.open(file) as pdf:
                    # Extract text from first page
                    text = pdf.pages[0].extract_text()
                
                # The AI Instruction
                prompt = f"""
                Extract 4 fields from this logistics document. Return ONLY a CSV line.
                Format: Date, Waybill_Number, Vendor_Name, Total_Amount
                Text: {text[:4000]}
                """
                
                # Call AI
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Clean up the result
                parts = resp.choices[0].message.content.split(',')
                master_data.append({
                    "File": file.name,
                    "Date": parts[0] if len(parts)>0 else "-",
                    "Waybill #": parts[1] if len(parts)>1 else "-",
                    "Vendor": parts[2] if len(parts)>2 else "-",
                    "Amount": parts[3] if len(parts)>3 else "0"
                })
            except Exception as e:
                st.error(f"Error on {file.name}: {e}")
            
            bar.progress((idx+1)/len(uploaded_files))
            
        if master_data:
            st.success("Processing Complete!")
            st.dataframe(pd.DataFrame(master_data))


# ==========================================
# PAGE 3: VISA STATEMENT AUDITOR
# ==========================================
elif page == "🛂 Visa Statement Auditor":
    
    st.title("🛂 Visa Risk Auditor")
    st.markdown("Scan Bank Statements for 'Lump Sum' deposits and Red Flags.")
    
    # Inputs
    salary = st.number_input("Client's Declared Salary (₦)", value=200000, step=10000)
    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")
    
    if st.button("🔍 Run Audit") and uploaded_file:
        status = st.empty()
        status.info("Scanning Statement...")
        
        try:
            # 1. EXTRACT TEXT
            with pdfplumber.open(uploaded_file) as pdf:
                text_data = ""
                # Scan first 4 pages
                for p in pdf.pages[:4]: 
                    extracted = p.extract_text()
                    if extracted: text_data += extracted
            
            # 2. AI PARSING
            client = Groq(api_key=API_KEY)
            prompt = f"""
            Extract bank transactions. Return ONLY CSV with headers: Date, Description, Credit, Debit, Balance.
            If a column is empty, put 0.
            Text: {text_data[:6000]}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 3. CREATE DATAFRAME
            csv_data = resp.choices[0].message.content
            # Use StringIO to pretend the string is a file
            df = pd.read_csv(StringIO(csv_data), sep=",")
            
            # Clean Numbers
            for col in ['Credit', 'Debit', 'Balance']:
                if col in df.columns:
                    df[col] = df[col].apply(clean_money)
            
            # 4. RISK LOGIC (The "Visa Officer" Brain)
            flags = []
            
            # Check A: Lump Sum (>3x Salary)
            limit = salary * 3
            if 'Credit' in df.columns and 'Description' in df.columns:
                suspicious = df[(df['Credit'] > limit) & (~df['Description'].str.contains('SALARY', case=False, na=False))]
                for _, row in suspicious.iterrows():
                    flags.append(f"🚩 **LUMP SUM:** ₦{row['Credit']:,.2f} on {row['Date']}")
                
            # Check B: Account Padding (High Inflow vs Low Balance)
            if not df.empty and 'Balance' in df.columns:
                last_bal = df.iloc[-1]['Balance']
                total_credit = df['Credit'].sum() if 'Credit' in df.columns else 0
                if total_credit > (last_bal * 5) and last_bal > 0: 
                    flags.append(f"🚩 **TURNOVER RISK:** Deposits are way higher than final balance.")

            # 5. DISPLAY REPORT
            st.divider()
            if not df.empty:
                c1, c2 = st.columns(2)
                c1.metric("Closing Balance", f"₦{df.iloc[-1]['Balance']:,.2f}" if 'Balance' in df.columns else "0")
                c2.metric("Total Inflow", f"₦{df['Credit'].sum():,.2f}" if 'Credit' in df.columns else "0")
            
            st.subheader("⚠️ Risk Report")
            if flags:
                for f in flags: st.error(f)
            else:
                st.success("✅ No obvious Red Flags found.")
                
            st.dataframe(df)
            
        except Exception as e:
            st.error(f"Error: {e}")
            st.info("Tip: Ensure the PDF is digital text (not a scanned image).")
