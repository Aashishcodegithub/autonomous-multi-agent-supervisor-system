# report_lookup.py
"""
LangChain tool wrapper for vector DB semantic report lookup.
"""

from langchain.tools import tool
from vector_store import get_best_report


@tool("lookup_erp_report")
def lookup_erp_report(query: str) -> str:
    """
    Find the best ERP report to use for a user's query.
    Input: Natural language question (e.g., 'how much profit did we make?')
    Output: Exact report name to use (e.g., 'Profit and Loss')
    
    Always use this BEFORE fetching data from erp.
    If no good match is found, returns error asking user to clarify.
    """
    return get_best_report(query)