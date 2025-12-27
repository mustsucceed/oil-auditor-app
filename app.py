import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
import json
import re

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="DataFlow Automations", page_icon="🚀", layout="wide")

# --- 2. SECURE API ---
try:
    if "GROQ_API_KEY" in st.secrets:
        API_KEY = st.secrets["GROQ_API_KEY"]
    else:
        st.error("🚨 Configuration Error: API Key not found in Secrets.")
        st.stop()
except FileNotFoundError:
    st.warning("⚠️ Running Locally? Ensure you have a secrets.toml file.")
    st.stop()

# --- 3. SIDEBAR ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["🏠 Home", "🚛 Logistics Auditor", "🛂 Visa Statement Auditor"])

# --- 4. HELPER FUNCTIONS ---
def clean_money(val):
    """Converts any money text to a clean number."""
    if not val: return 0.0
    clean = str(val).replace(",", "").replace("₦", "").replace("$", "").replace("DR", "").strip()
    try:
        return float(clean)
    except:
        return 0.0

def extract_json_from_response(content):
    """Finds the JSON bracket { } or [ ] inside the AI's response."""
    try:
        # Look for a list [ ... ]
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        # Look for a dict { ... }
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        return None
    return None

# ==========================================
# PAGE 1: HOME
# ==========================================
if page == "🏠 Home":
    st.title("🚀 DataFlow Automations")
    st.info("Select a tool from the sidebar to begin.")

# ==========================================
# PAGE 2: LOGISTICS AUDITOR (JSON Mode)
# ==========================================
elif page == "🚛 Logistics Auditor":
    st.title("🚛 Logistics Processor")
    uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    
    if st.button("🚀 Process") and uploaded_files:
        client = Groq(api_key=API_KEY)
        master_data = []
        bar = st.progress(0)
        
        for idx, file in enumerate(uploaded_files):
            with pdfplumber.open(file) as pdf:
                text = pdf.pages[0].extract_text()
            
            # CHECK FOR SCANNED IMAGE
            if not text or len(text) < 50:
                st.error(f"⚠️ File '{file.name}' seems to be a scanned image (no text found). Skipping.")
                continue

            prompt = f"""
            Extract data from this logistics document.
            Return ONLY a valid JSON object with these keys: 
            "Date", "Waybill_Number", "Vendor_Name", "Total_Amount".
            If a field is missing, use "N/A".
            
            TEXT:
            {text[:4000]}
            """
            
            try:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Parse JSON
                data = extract_json_from_response(resp.choices[0].message.content)
                
                if data:
                    # Handle if AI returns a list or single object
                    if isinstance(data, list): data = data[0]
                    
                    master_data.append({
                        "File": file.name,
                        "Date": data.get("Date", "-"),
                        "Waybill #": data.get("Waybill_Number", "-"),
                        "Vendor": data.get("Vendor_Name", "-"),
                        "Amount": data.get("Total_Amount", "0")
                    })
            except Exception as e:
                st.error(f"Error on {file.name}: {e}")
            
            bar.progress((idx+1)/len(uploaded_files))
            
        if master_data:
            st.success("Done!")
            st.dataframe(pd.DataFrame(master_data))

# ==========================================
# PAGE 3: VISA AUDITOR (JSON Mode)
# ==========================================
elif page == "🛂 Visa Statement Auditor":
    st.title("🛂 Visa Risk Auditor")
    salary = st.number_input("Client's Declared Salary (₦)", value=200000, step=10000)
    uploaded_file = st.file_uploader("Upload Bank Statement (PDF)", type="pdf")
    
    if st.button("🔍 Run Audit") and uploaded_file:
        status = st.empty()
        status.info("Reading PDF...")
        
        # 1. READ TEXT
        with pdfplumber.open(uploaded_file) as pdf:
            text_data = ""
            for p in pdf.pages[:4]: 
                extracted = p.extract_text()
                if extracted: text_data += extracted
        
        # DEBUG: Check if text exists
        if len(text_data) < 100:
            status.error("❌ Error: This PDF looks like a SCANNED IMAGE (Picture). AI cannot read it directly. Please use a digital PDF exported from the bank app.")
            st.stop()

        # 2. ASK AI FOR JSON
        status.info("AI Analyzing...")
        client = Groq(api_key=API_KEY)
        
        prompt = f"""
        Extract the bank transactions from the text below.
        Return ONLY a JSON list of objects.
        Each object must have these keys: "Date", "Description", "Credit", "Debit", "Balance".
        If a value is missing, use 0.
        
        TEXT DATA:
        {text_data[:6000]}
        """
        
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 3. PARSE JSON
            ai_content = resp.choices[0].message.content
            json_data = extract_json_from_response(ai_content)
            
            if not json_data:
                st.error("⚠️ AI could not find structured data. The statement format might be too complex.")
                st.text_area("Debug Info (AI Output)", ai_content) # Show user what happened
                st.stop()

            # 4. CONVERT TO DATAFRAME
            df = pd.DataFrame(json_data)
            
            # Standardize Columns
            expected_cols = ["Date", "Description", "Credit", "Debit", "Balance"]
            for col in expected_cols:
                if col not in df.columns: df[col] = 0
            
            # Clean Numbers
            for col in ['Credit', 'Debit', 'Balance']:
                df[col] = df[col].apply(clean_money)
            
            status.success("Data Extracted Successfully!")
            
            # 5. RISK LOGIC
            flags = []
            limit = salary * 3
            
            # Lump Sum Check
            suspicious = df[(df['Credit'] > limit) & (~df['Description'].str.contains('SALARY', case=False, na=False))]
            for _, row in suspicious.iterrows():
                flags.append(f"🚩 **LUMP SUM:** ₦{row['Credit']:,.2f} on {row['Date']}")
            
            # Display
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("Total Inflow", f"₦{df['Credit'].sum():,.2f}")
            c2.metric("Closing Balance", f"₦{df.iloc[-1]['Balance']:,.2f}" if not df.empty else "0")
            
            st.subheader("⚠️ Risk Report")
            if flags:
                for f in flags: st.error(f)
            else:
                st.success("✅ No obvious Red Flags found.")
                
            st.dataframe(df)

        except Exception as e:
            st.error(f"System Error: {e}")
