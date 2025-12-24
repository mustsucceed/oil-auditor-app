import streamlit as st
import pdfplumber
import pandas as pd
from groq import Groq
import io
import time

# ==========================================
# 🔐 CONFIGURATION
# ==========================================
# If you created secrets.toml, use: st.secrets["GROQ_API_KEY"]
# If not, paste your key here for now:

API_KEY = st.secrets["GROQ_API_KEY"]
# ==========================================

st.set_page_config(page_title="AI Auditor Pro", page_icon="📈", layout="wide")

st.title("📈 AI Oil Field Auditor (Dashboard Edition)")
st.markdown("### Upload Daily Reports to see Trends & Analytics")

# 1. THE SIDEBAR (Professional Look)
with st.sidebar:
    st.header("Upload Station")
    uploaded_files = st.file_uploader("Drop PDFs Here", type="pdf", accept_multiple_files=True)
    process_btn = st.button("🚀 Process Files")

# 2. MAIN APP LOGIC
if process_btn and uploaded_files:
    
    master_data_list = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    client = Groq(api_key=API_KEY)
    
    # --- PROCESSING LOOP ---
    for index, file in enumerate(uploaded_files):
        status_text.text(f"Analyzing: {file.name}...")
        
        try:
            with pdfplumber.open(file) as pdf:
                pdf_text = pdf.pages[0].extract_text()
            
            # PROMPT: We ask for purely numeric data for the graphs
            prompt = f"""
            Extract these 3 fields. Return ONLY a CSV line.
            Format: Date,Well_Name,Depth,Mud_Weight
            
            RULES:
            1. For Depth, return ONLY the number (e.g., 4500), remove "feet" or commas.
            2. For Mud Weight, return ONLY the number (e.g., 9.8), remove "ppg".
            3. Assume Date is 2025-10-{25 + index}.
            
            Text:
            {pdf_text}
            """
            
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}]
            )
            
            csv_line = response.choices[0].message.content
            clean_values = csv_line.strip().split(',')
            
            # Add to list with numeric conversion
            master_data_list.append({
                "Source_File": file.name,
                "Date": clean_values[0],
                "Well_Name": clean_values[1],
                "Depth": float(clean_values[2]),      # Convert text to Number
                "Mud_Weight": float(clean_values[3])  # Convert text to Number
            })

        except Exception as e:
            st.error(f"Error on {file.name}: {e}")
        
        progress_bar.progress((index + 1) / len(uploaded_files))
        time.sleep(0.2)
        
    status_text.text("✅ Analytics Ready!")
    
    # --- DASHBOARD SECTION ---
    if master_data_list:
        df_master = pd.DataFrame(master_data_list)
        
        # Layout: Two columns for charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📉 Drilling Depth Progress")
            # Line Chart: Depth over Time
            st.line_chart(df_master.set_index("Date")["Depth"])
            
        with col2:
            st.subheader("⚖️ Mud Weight Safety")
            # Bar Chart: Mud Weight
            st.bar_chart(df_master.set_index("Date")["Mud_Weight"])
            
        # Display Data Table below charts
        st.divider()
        st.subheader("📄 Master Data Record")
        st.dataframe(df_master)
        
        # Download Button
        csv_bytes = df_master.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report", csv_bytes, "Master_Audit.csv", "text/csv")