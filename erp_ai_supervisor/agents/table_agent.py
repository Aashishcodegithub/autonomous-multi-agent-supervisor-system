import json
from typing import Optional

from tools.get_report_tool import get_report
from tools.data_conversion_tool import data_conversion_tool
from tools.table_tool import table_tool


def run_table_agent(
    company: str,
    report: str,
    max_rows: Optional[int] = 20,
):
    """
    Pure TABLE agent:
    - Fetch report
    - Convert to DataFrame + summary
    - Generate Markdown table
    - Return FINAL output
    """

    # 1️⃣ Fetch report (raw dict)
    raw_dict = get_report.func(company, report)

    # 2️⃣ Convert to structured DataFrame (pass report name for routing)
    conv_output = data_conversion_tool.func(raw_dict, report)

    if isinstance(conv_output, str):
        try:
            conv_output = json.loads(conv_output)
        except Exception:
            return {
                "error": "data_conversion_tool returned invalid JSON",
                "raw": conv_output,
            }

    summary = conv_output.get("summary")
    dataframe_id = conv_output.get("dataframe_id")
    dataframe_dict = conv_output.get("dataframe_dict")
    print("SUMMARY COLUMNS:")
    print(summary.get("columns"))
    print("DATAFRAME_DICT KEYS:")
    print(list(dataframe_dict.keys()))



    if not dataframe_dict:
        return {
            "error": "No tabular data available",
            "summary": summary,
            "dataframe_id": dataframe_id,
        }

    #  ADDITION — DERIVE HUMAN-READABLE COLUMN HEADERS FROM SUMMARY
    display_headers = None
    if summary and "columns" in summary:
        display_headers = []
        for col in summary["columns"]:
            col_upper = col.upper()
            if "DSPDISPNAME" in col_upper:
                display_headers.append("Item Name")
            elif "QTY" in col_upper:
                display_headers.append("Quantity")
            elif "RATE" in col_upper:
                display_headers.append("Rate")
            elif "AMT" in col_upper or "AMTA" in col_upper:
                display_headers.append("Amount")
            else:
                # fallback: clean technical name
                display_headers.append(
                    col.replace("_", " ").title()
                )

    # 3️⃣ Generate Markdown table (NO LLM)
    table_md = table_tool.func(
        dataframe_dict=dataframe_dict,
        max_rows=max_rows,
        display_headers=display_headers,  # ⭐ ADDITION
    )

    # 4️⃣ FINAL OUTPUT (TERMINAL)
    return {
        "table": table_md,
        "summary": summary,
        "dataframe_id": dataframe_id,
    }


def react_table_agent(json_str: str) -> str:
    """
    Wrapper called by supervisor.
    Accepts JSON string and returns FINAL table JSON.
    """

    try:
        data = json.loads(json_str)
    except Exception:
        return "Invalid JSON: expected keys company, report, max_rows?"

    company = data.get("company")
    report = data.get("report")
    max_rows = data.get("max_rows", 20)

    if not company:
        return "Missing required field: company"
    if not report:
        return "Missing required field: report"

    output = run_table_agent(
        company=company,
        report=report,
        max_rows=max_rows,
    )

    return json.dumps(output)
