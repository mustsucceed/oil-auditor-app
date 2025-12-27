import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
from io import StringIO

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="DataFlow Automations", page_icon="🚀", layout="wide")

# --- 2. SECURE API CONNECTION ---
try:
    if "GROQ_API_KEY" in st.secrets:
        API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        st.error("🚨 Configuration Error: API Key not found.")
        st.stop()
except FileNotFoundError:
    st.warning("⚠️ Running Locally? You need a .streamlit/secrets.toml file.")
    st.stop()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
st.sidebar.title("Navigation")
st.sidebar.success("✅ System Online")
page = st.sidebar.radio("Go to:", ["🏠 Home / Portfolio", "🚛 Logistics Auditor", "🛂 Visa Statement Auditor"])

# --- 4. HELPER FUNCTIONS ---
def clean_money(text):
    """Converts text like '₦1,000,000.00' into a float."""
    if not text: return 0.0
    # Remove currency symbols, commas, and pipe characters just in case
    clean = str(text).replace(",", "").replace("₦", "").replace("$", "").replace("|", "").strip()
    try:
        return float(clean)
    except:
        return 0.0

# ==========================================
# PAGE 1: HOME
# ==========================================
if page == "🏠 Home / Portfolio":
    st.title("🚀 DataFlow Automations Nigeria")
    st.markdown("### We turn piles of Paperwork into Profit.")
    st.divider()
    st.info("Select a tool from the Sidebar to start.")

# ==========================================
# PAGE 2: LOGISTICS AUDITOR (Pipe Fix)
# ==========================================
elif page == "🚛 Logistics Auditor":
    st.title("🚛 Logistics Document Processor")
    uploaded_files = st.file_uploader("Upload Logistics PDFs", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Process Waybills") and uploaded_files:
        client = Groq(api_key=API_KEY)
        master_data = []
        bar = st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            try:
                with pdfplumber.open(file) as pdf:
                    text = pdf.pages[0].extract_text()
                
                # UPDATED PROMPT: Uses | instead of comma
                prompt = f"""
                Extract 4 fields. Return ONLY a list separated by PIPES (|).
                Format: Date | Waybill_Number | Vendor_Name | Total_Amount
                Text: {text[:4000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # UPDATED PARSING: Split by |
                raw_line = resp.choices[0].message.content
                parts = raw_line.split('|')
                
                # Clean up whitespace around the parts
                parts = [p.strip() for p in parts]
                
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
# PAGE 3: VISA AUDITOR (Pipe Fix + Robust)
# ==========================================
elif page == "🛂 Visa Statement Auditor":
    st.title("🛂 Visa Risk Auditor")
    salary = st.number_input("Client's Declared Salary (₦)", value=200000, step=10000)
    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")
    
    if st.button("🔍 Run Audit") and uploaded_file:
        status = st.empty()
        status.info("Scanning Statement...")
        
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                text_data = ""
                for p in pdf.pages[:4]: 
                    extracted = p.extract_text()
                    if extracted: text_data += extracted
            
            # --- THE MAGIC FIX: FORCE PIPE SEPARATOR ---
            client = Groq(api_key=API_KEY)
            prompt = f"""
            Extract bank transactions.
            Return ONLY data separated by PIPES (|).
            Do NOT use commas to separate columns.
            Format: Date | Description | Credit | Debit | Balance
            If a column is empty, put 0.
            Text: {text_data[:6000]}
            """
            
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            
            csv_raw = resp.choices[0].message.content
            
            # Filter lines
            lines = csv_raw.split('\n')
            clean_lines = []
            
            # Add Header manually to ensure it matches
            clean_lines.append("Date|Description|Credit|Debit|Balance")
            
            for line in lines:
                # Only keep lines that have pipes in them
                if "|" in line and "Date" not in line: 
                    clean_lines.append(line)
            
            cleaned_data = "\n".join(clean_lines)

            # Load into Pandas using | as separator
            if len(clean_lines) < 2:
                st.error("AI could not find valid transaction data.")
                st.stop()

            # sep='|' is the key here!
            df = pd.read_csv(StringIO(cleaned_data), sep="|", on_bad_lines='skip')
            
            # Strip whitespace from column names
            df.columns = df.columns.str.strip()
            
            # Clean Numbers
            for col in ['Credit', 'Debit', 'Balance']:
                if col in df.columns:
                    df[col] = df[col].astype(str).apply(clean_money)
                else:
                    df[col] = 0.0
            
            # RISK LOGIC
            flags = []
            limit = salary * 3
            if 'Credit' in df.columns:
                suspicious = df[(df['Credit'] > limit)]
                for _, row in suspicious.iterrows():
                    flags.append(f"🚩 **LUMP SUM:** ₦{row['Credit']:,.2f} on {row['Date']}")
            
            st.divider()
            if not df.empty:
                st.metric("Total Inflow", f"₦{df['Credit'].sum():,.2f}" if 'Credit' in df.columns else "0")
            
            st.subheader("⚠️ Risk Report")
            if flags:
                for f in flags: st.error(f)
            else:
                st.success("✅ No obvious Red Flags found.")
                
            st.dataframe(df)
            
        except Exception as e:
            st.error(f"Error: {e}")
