# tools/react_wrappers.py

import json
from tools.company_list_tool import get_company_list
from tools.get_report_tool import get_report
from tools.data_conversion_tool import data_conversion_tool


def react_company_list(_input: str):
    """No input required for this tool."""
    return get_company_list.func()


def react_get_report(json_str: str):
    """Expects JSON string: {"company": "...", "report": "..."}"""
    try:
        data = json.loads(json_str)
    except Exception:
        return 'Invalid JSON. Expected {"company": "...", "report": "..."}'

    company = data.get("company")
    report = data.get("report")

    if not company:
        return "Missing required field: company"
    if not report:
        return "Missing required field: report"

    # Return RAW dict directly
    raw_dict = get_report.func(company, report)

    # IMPORTANT — return it as VALID JSON string
    return json.dumps(raw_dict)
    

def react_convert_report(json_str: str):
    """Expects JSON string: {"report_dict": {...}}"""
    try:
        data = json.loads(json_str)
    except Exception:
        return 'Invalid JSON. Expected {"report_dict": {...}}'

    report_dict = data.get("report_dict")
    if not report_dict:
        return "Missing required field: report_dict"

    # Now safe to call tool
    output = data_conversion_tool.func(report_dict)

    # Return valid JSON string
    return json.dumps(output)