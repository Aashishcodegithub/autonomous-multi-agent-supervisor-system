import gradio as gr
import requests
import os
import base64
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------
load_dotenv()

FASTAPI_BASE = os.getenv("FASTAPI_BASE", "http://127.0.0.1:8000")
FASTAPI_URL = f"{FASTAPI_BASE}/api/run"
API_KEY = os.getenv("API_KEY")

HEADERS = {
    "X-API-Key": API_KEY
}

# --------------------------------------------------
# CORE FUNCTION
# --------------------------------------------------
def run_query(query, company, graph_type):
    if not query or not company:
        return None, None, None, None, None

    payload = {
        "query": query,
        "company": company,
        "graph_type": None if graph_type == "auto" else graph_type,
    }

    try:
        r = requests.post(
            FASTAPI_URL,
            json=payload,
            headers=HEADERS,
            timeout=120
        )
        r.raise_for_status()
        result = r.json()
    except Exception as e:
        return None, None, None, None, {"error": str(e)}

    if not result.get("success"):
        return None, None, None, None, result

    # -----------------------------
    # GRAPH
    # -----------------------------
    img = None
    if result.get("image_base64"):
        img_bytes = base64.b64decode(result["image_base64"])
        img = Image.open(BytesIO(img_bytes))

    # -----------------------------
    # SUMMARY
    # -----------------------------
    summary_md = result.get("summary_text")

    # -----------------------------
    # TABLE (Markdown)
    # -----------------------------
    table_md = None
    raw_output = result.get("raw_output", {})
    if isinstance(raw_output, dict):
        table_md = raw_output.get("table")

    # -----------------------------
    # SAMPLE DATA
    # -----------------------------
    sample_rows = result.get("sample_rows")

    return img, summary_md, table_md, sample_rows, result


# --------------------------------------------------
# GRADIO UI
# --------------------------------------------------
with gr.Blocks(title="ERP AI Assistant") as demo:

    gr.Markdown("## 📊 ERP AI Assistant")
    gr.Markdown(
        "Ask questions about your **ERP data** in natural language.\n\n"
        "You can get:\n"
        "- 📈 Graphs\n"
        "- 📝 Summaries\n"
        "- 📋 Tables\n"
    )

    with gr.Row():
        query = gr.Textbox(
            label="Query",
            placeholder="Example: Give me an analysis of my stock items based on quantity"
        )

    with gr.Row():
        company = gr.Textbox(
            label="Company",
            placeholder="Enter company name"
        )

        graph_type = gr.Dropdown(
            label="Graph Type",
            choices=["auto", "bar", "line", "pie"],
            value="auto"
        )

    run_btn = gr.Button("Run Query")

    gr.Markdown("---")

    graph_out = gr.Image(label="📈 Generated Graph")
    summary_out = gr.Markdown(label="📝 Summary")
    table_out = gr.Markdown(label="📋 Table")
    sample_out = gr.Dataframe(label="📋 Sample Data", interactive=False)
    raw_out = gr.JSON(label="🔍 Raw API Response")

    run_btn.click(
        fn=run_query,
        inputs=[query, company, graph_type],
        outputs=[
            graph_out,
            summary_out,
            table_out,
            sample_out,
            raw_out
        ]
    )

# --------------------------------------------------
# RUN
# --------------------------------------------------
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
