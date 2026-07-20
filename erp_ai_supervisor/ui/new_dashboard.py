import streamlit as st
import requests
import os
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from datetime import datetime

# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------
load_dotenv()

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
FASTAPI_BASE = os.getenv("FASTAPI_BASE", "http://127.0.0.1:8000")
FASTAPI_URL = f"{FASTAPI_BASE}/api/run"
COMPANY_API_URL = f"{FASTAPI_BASE}/api/companies"

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    st.error("API_KEY not found in .env")
    st.stop()

HEADERS = {"X-API-Key": API_KEY}

# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------
st.set_page_config(page_title="ERP AI Dashboard", layout="wide")

# --------------------------------------------------
# INITIALIZE SESSION STATE FOR CHAT HISTORY
# --------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.title("📊 ERP AI Assistant")
st.markdown("""
Ask questions about your **ERP data** in natural language.

You can get:
- 📈 Graphs
- 📝 Summaries
- 📋 Sample data
""")

# --------------------------------------------------
# LOAD COMPANY LIST
# --------------------------------------------------
@st.cache_data
def load_companies():
    try:
        r = requests.get(COMPANY_API_URL, headers=HEADERS, timeout=30)
        data = r.json()
        if data.get("success"):
            return data.get("companies", [])
    except Exception:
        pass
    return []

companies = load_companies()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.header("Company & Graph Options")

if companies:
    company = st.sidebar.selectbox("Choose Company", companies)
else:
    st.sidebar.warning("No companies available")
    company = ""

graph_type = st.sidebar.selectbox(
    "Graph Type (optional)",
    ["auto", "bar", "line", "pie"]
)

# --------------------------------------------------
# MAIN QUERY
# --------------------------------------------------
query = st.text_input(
    "Ask your question",
    placeholder="Example: Give me an analysis of my stock items based on quantity"
)

run = st.button("Run Query")

# --------------------------------------------------
# HELPER FUNCTION: DISPLAY SINGLE CHAT ITEM
# --------------------------------------------------
def display_chat_item(item):
    """Display a single chat history item"""
    with st.container():
        # Header with query and timestamp
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**User:** {item['query']}")
        with col2:
            st.caption(item['timestamp'])
        
        result = item['result']
        
        # Display based on result type
        if result.get("image_base64"):
            try:
                img_bytes = base64.b64decode(result["image_base64"])
                img = Image.open(BytesIO(img_bytes))
                st.image(img, use_column_width=True)
            except Exception as e:
                st.warning(f"Could not display image: {str(e)}")
        
        if result.get("summary_text"):
            st.markdown(f"**Summary:** {result['summary_text']}")
        
        # Show table if available
        raw_output = result.get("raw_output")
        if isinstance(raw_output, dict):
            table_md = raw_output.get("table")
            if table_md:
                st.markdown(table_md)
        
        # Show sample data if available
        sample_rows = result.get("sample_rows")
        if sample_rows and isinstance(raw_output, dict):
            summary = raw_output.get("summary", {})
            raw_columns = summary.get("columns", [])
            
            def humanize(col):
                name = col.split("_")[-1]
                name = name.replace("QTY", "Quantity")
                name = name.replace("RATE", "Rate")
                name = name.replace("AMTA", "Amount")
                name = name.replace("DSPDISPNAME", "Item Name")
                return name.title()
            
            column_map = {col: humanize(col) for col in raw_columns}
            fixed_rows = []
            for row in sample_rows:
                fixed_row = {}
                for k, v in row.items():
                    fixed_row[column_map.get(k, k)] = v
                fixed_rows.append(fixed_row)
            
            st.table(fixed_rows)
        
        st.divider()

# --------------------------------------------------
# API CALL
# --------------------------------------------------
if run:
    if not query.strip():
        st.warning("Please enter a query")
        st.stop()

    if not company.strip():
        st.warning("Please enter or select a company")
        st.stop()

    payload = {
        "query": query,
        "company": company,
        "graph_type": None if graph_type == "auto" else graph_type,
    }

    st.info("Processing request...")

    try:
        response = requests.post(
            FASTAPI_URL,
            json=payload,
            headers=HEADERS,
            timeout=120
        )
    except Exception as e:
        st.error(f"API call failed: {str(e)}")
        st.stop()

    if response.status_code != 200:
        st.error(f"Backend error ({response.status_code}): {response.text}")
        st.stop()

    result = response.json()

    if not result.get("success"):
        st.error(result.get("message", "Something went wrong"))
        st.stop()

    # --------------------------------------------------
    # ADD TO CHAT HISTORY
    # --------------------------------------------------
    chat_item = {
        "query": query,
        "result": result,
        "timestamp": datetime.now().strftime("%I:%M %p")
    }
    
    # Add to beginning of list (newest first)
    st.session_state.chat_history.insert(0, chat_item)
    
    # Keep only last 10 items
    if len(st.session_state.chat_history) > 10:
        st.session_state.chat_history = st.session_state.chat_history[:10]

# --------------------------------------------------
# DISPLAY CHAT HISTORY (REVERSE CHRONOLOGICAL)
# --------------------------------------------------
if st.session_state.chat_history:
    st.markdown("---")
    
    # Header with Clear History button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("💬 Chat History")
    with col2:
        if st.button("🗑️ Clear History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Display all items (already in reverse chronological order)
    for item in st.session_state.chat_history:
        display_chat_item(item)
else:
    if not run:
        st.info("💡 Your chat history will appear here")
