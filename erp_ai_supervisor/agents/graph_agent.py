# agents/graph_agent.py
from dotenv import load_dotenv
import os
import json
from typing import Optional

from tools.get_report_tool import get_report
from tools.data_conversion_tool import data_conversion_tool
from tools.graph_code_generator_tool import graph_code_generator
from tools.graph_executor_tool import graph_executor

load_dotenv()


def run_graph_agent(
    company: str,
    report: str,
    user_graph_preference: Optional[str] = None,
    title: Optional[str] = None,
):
    """
    Pure GRAPH agent:
    - Fetch report
    - Convert to DataFrame + summary
    - Generate matplotlib code
    - Execute safely
    - Return ONLY graph-related output (NO natural-language summary)
    """

    # Fetch report (returns dict)
    raw_dict = get_report.func(company, report)

    # Convert to summary + dataframe (pass report name for routing)
    conv_output = data_conversion_tool.func(raw_dict, report)

    # Handle JSON outputs from tool
    if isinstance(conv_output, str):
        try:
            conv_output = json.loads(conv_output)
        except Exception:
            return {
                "error": "data_conversion_tool returned invalid JSON string",
                "raw": conv_output,
            }

    summary = conv_output.get("summary")
    dataframe_id = conv_output.get("dataframe_id")
    dataframe_dict = conv_output.get("dataframe_dict")

    if summary is None or dataframe_dict is None:
        return {
            "error": "data_conversion_tool output missing 'summary' or 'dataframe_dict'",
            "raw": conv_output,
        }

    # Default chart title
    if not title:
        title = f"{report} - {company}"

    # Generate Python matplotlib code string
    code = graph_code_generator.func(
        summary=summary,
        user_graph_preference=user_graph_preference,
        title=title,
        report=report,
    )

    # Handle code generation errors
    if isinstance(code, str) and code.startswith("Graph code generation failed"):
        return {
            "error": code,
            "summary": summary,
            "dataframe_id": dataframe_id,
        }

    # Execute matplotlib code safely
    exec_result = graph_executor.func(
        code=code,
        dataframe=dataframe_dict
    )

    if isinstance(exec_result, dict) and exec_result.get("error"):
        return {
            "error": exec_result["error"],
            "summary": summary,
            "dataframe_id": dataframe_id,
            "graph_code": code,
        }

    image_path = None
    if isinstance(exec_result, dict):
        image_path = exec_result.get("image_path")

    # --- FINAL GRAPH-ONLY OUTPUT ---
    return {
        "dataframe_id": dataframe_id,
        "graph_code": code,
        "image_path": image_path
    }


def react_graph_agent(json_str: str) -> str:
    """
    Wrapper tool called by supervisor.
    Accepts JSON string → validates fields → returns graph_agent output JSON.
    """

    try:
        data = json.loads(json_str)
    except Exception:
        return "Invalid JSON: expected keys company, report, graph_type?, title?"

    company = data.get("company")
    report = data.get("report")
    graph_type = data.get("graph_type")
    title = data.get("title")

    if not company:
        return "Missing required field: company"
    if not report:
        return "Missing required field: report"

    output = run_graph_agent(
        company=company,
        report=report,
        user_graph_preference=graph_type,
        title=title,
    )

    return json.dumps(output)
