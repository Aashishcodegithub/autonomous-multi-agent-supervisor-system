# agents/dashboard_agent.py

from dotenv import load_dotenv
import os
import json
from typing import Optional

from tools.dashboard_tile_fetcher import fetch_and_parse_tile
from tools.graph_code_generator_tool import graph_code_generator
from tools.graph_executor_tool import graph_executor

load_dotenv()


def run_dashboard_agent(
    company: str,
    tile_type: str,
    query: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_date: Optional[str] = None,
    voucher_type: Optional[str] = None,
    user_graph_preference: Optional[str] = None,
    title: Optional[str] = None,
):
    """
    Dashboard agent:
    - Fetch tile data via dashboard_tile_fetcher
    - Convert to DataFrame + summary
    - Generate matplotlib code
    - Execute safely
    - Return graph + table output
    """

    # Fetch and parse tile
    conv_output = fetch_and_parse_tile(
        company=company,
        tile_type=tile_type,
        query=query,
        from_date=from_date,
        to_date=to_date,
        current_date=current_date,
        voucher_type=voucher_type
    )

    # Handle errors from fetcher
    if isinstance(conv_output, dict) and conv_output.get("error"):
        return {
            "error": conv_output.get("error"),
            "summary": None,
            "dataframe_id": None,
        }

    summary = conv_output.get("summary")
    dataframe_id = conv_output.get("dataframe_id")
    dataframe_dict = conv_output.get("dataframe_dict")

    if summary is None or dataframe_dict is None:
        return {
            "error": "dashboard_tile_fetcher output missing 'summary' or 'dataframe_dict'",
            "raw": conv_output,
        }

    # Default chart title
    if not title:
        title = f"{tile_type.title()} Dashboard - {company}"

    # Generate Python matplotlib code string
    code = graph_code_generator.func(
        summary=summary,
        user_graph_preference=user_graph_preference,
        title=title,
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

    # --- FINAL GRAPH-ONLY OUTPUT (table handled by intent_splitter) ---
    return {
        "summary": summary,
        "dataframe_id": dataframe_id,
        "graph_code": code,
        "image_path": image_path,
        "tile_type": tile_type,
        "dataframe_dict": dataframe_dict  # Pass dataframe_dict so intent_splitter can generate table
    }


def react_dashboard_agent(json_str: str) -> str:
    """
    Wrapper tool called by intent splitter.
    Accepts JSON string → validates fields → returns dashboard_agent output JSON.
    """

    try:
        data = json.loads(json_str)
    except Exception:
        return json.dumps({
            "error": "Invalid JSON: expected keys company, tile_type, query?"
        })

    company = data.get("company")
    tile_type = data.get("tile_type")
    query = data.get("query")
    from_date = data.get("from_date")
    to_date = data.get("to_date")
    current_date = data.get("current_date")
    voucher_type = data.get("voucher_type")
    graph_type = data.get("graph_type")
    title = data.get("title")

    if not company:
        return json.dumps({"error": "Missing required field: company"})
    if not tile_type:
        return json.dumps({"error": "Missing required field: tile_type"})

    output = run_dashboard_agent(
        company=company,
        tile_type=tile_type,
        query=query,
        from_date=from_date,
        to_date=to_date,
        current_date=current_date,
        voucher_type=voucher_type,
        user_graph_preference=graph_type,
        title=title,
    )

    return json.dumps(output)
