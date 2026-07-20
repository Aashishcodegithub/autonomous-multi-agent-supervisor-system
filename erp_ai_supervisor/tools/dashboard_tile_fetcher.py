# tools/dashboard_tile_fetcher.py
"""
Dashboard Tile Fetcher - Fetches dashboard tiles from erp.

Responsibilities:
1. Call ERP API (via erp.client)
2. Parse tile response using erp.parser
3. Auto-fill missing dates
4. Adapt output to standard DataFrame format
5. Return summary + dataframe_dict (standard contract)

Integration point: Called by dashboard_agent to get tile data.
"""

import pandas as pd
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from langchain.tools import tool

from erp.client import send_to_erp
from erp.parser import parse_periodic_trend, parse_tiles


# ---------------------------------------------------------------
# AUTO-FILL LOGIC
# ---------------------------------------------------------------

def auto_fill_dates(from_date: Optional[str], to_date: Optional[str], current_date: Optional[str]):
    """
    Auto-fill missing date parameters.
    
    Default behavior:
    - current_date: today if not provided
    - from_date: 3 months ago if not provided
    - to_date: today if not provided
    """
    today = datetime.now()
    
    if current_date:
        try:
            current = datetime.strptime(current_date, "%Y-%m-%d")
        except Exception:
            current = today
    else:
        current = today
    
    if to_date:
        try:
            to_d = datetime.strptime(to_date, "%Y-%m-%d")
        except Exception:
            to_d = current
    else:
        to_d = current
    
    if from_date:
        try:
            from_d = datetime.strptime(from_date, "%Y-%m-%d")
        except Exception:
            from_d = current - timedelta(days=90)
    else:
        from_d = current - timedelta(days=90)
    
    return {
        "from_date": from_d.strftime("%Y-%m-%d"),
        "to_date": to_d.strftime("%Y-%m-%d"),
        "current_date": current.strftime("%Y-%m-%d")
    }


def infer_voucher_type(query: str) -> str:
    """
    Infer voucher type from query keywords.
    """
    query_lower = query.lower()
    
    if "purchase" in query_lower:
        return "Purchase"
    elif "sales" in query_lower:
        return "Sales"
    else:
        return "Sales"  # Default


# ---------------------------------------------------------------
# ADAPTER: Convert parsed data to standard DataFrame format
# ---------------------------------------------------------------

def build_df_summary(df: pd.DataFrame, sample_size: int = 5):
    """
    Build summary dict compatible with existing graph pipeline.
    Mirrors tools/data_conversion_tool.py:build_df_summary()
    """
    def simplify_dtype(dtype):
        dtype = str(dtype)
        if "int" in dtype or "float" in dtype:
            return "number"
        if "datetime" in dtype:
            return "date"
        return "string"
    
    summary = {
        "columns": df.columns.tolist(),
        "dtypes": {col: simplify_dtype(df[col].dtype) for col in df.columns},
        "sample_rows": df.head(sample_size).to_dict(orient="records"),
        "row_count": len(df)
    }
    
    return summary


def adapter_periodic_trend(months: list, amounts: list) -> Dict[str, Any]:
    """
    Convert parse_periodic_trend output to standard format.
    Input: (months, amounts) from parse_periodic_trend()
    Output: {summary, dataframe_dict, dataframe_id}
    """
    df = pd.DataFrame({
        "Month": months,
        "Amount": amounts
    })
    
    summary = build_df_summary(df)
    df_id = f"df_{uuid.uuid4().hex[:8]}"
    
    return {
        "summary": summary,
        "dataframe_id": df_id,
        "dataframe_dict": df.to_dict(orient="list")
    }


def adapter_tiles(tiles_dict: Dict[str, float], tile_name: str = "Amount") -> Dict[str, Any]:
    """
    Convert parse_tiles output to standard format.
    Input: {name: value} from parse_tiles()
    Output: {summary, dataframe_dict, dataframe_id}
    """
    names = list(tiles_dict.keys())
    values = list(tiles_dict.values())
    
    df = pd.DataFrame({
        "Name": names,
        tile_name: values
    })
    
    summary = build_df_summary(df)
    df_id = f"df_{uuid.uuid4().hex[:8]}"
    
    return {
        "summary": summary,
        "dataframe_id": df_id,
        "dataframe_dict": df.to_dict(orient="list")
    }


# ---------------------------------------------------------------
# MAIN FETCHER TOOL
# ---------------------------------------------------------------

def fetch_and_parse_tile(
    company: str,
    tile_type: str,
    query: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_date: Optional[str] = None,
    voucher_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function to fetch and parse a dashboard tile.
    
    Args:
        company: Company name
        tile_type: "trend", "trading", "cashflow", "assets"
        query: Optional user query (for auto-detecting voucher_type)
        from_date: Optional start date (YYYY-MM-DD)
        to_date: Optional end date (YYYY-MM-DD)
        current_date: Optional current date (YYYY-MM-DD)
        voucher_type: Optional voucher type (Sales/Purchase for trends)
    
    Returns:
        {summary, dataframe_dict, dataframe_id} compatible with graph pipeline
    """
    
    # Auto-fill dates
    dates = auto_fill_dates(from_date, to_date, current_date)
    
    # Infer voucher type if not provided and needed
    if not voucher_type and query:
        voucher_type = infer_voucher_type(query)
    
    # ---------------------------------------------------------------
    # ROUTE BY TILE TYPE
    # ---------------------------------------------------------------
    
    if tile_type == "trend":
        # Sales/Purchase Trend (periodic)
        if not voucher_type:
            voucher_type = "Sales"
        
        response = send_to_erp(
            "periodic_trend.xml",
            {
                "company_name": company,
                "voucher_type": voucher_type,
                "from_date": dates["from_date"],
                "to_date": dates["to_date"],
                "current_date": dates["current_date"],
                "periodicity": "Month"
            }
        )
        
        months, amounts = parse_periodic_trend(response)
        return adapter_periodic_trend(months, amounts)
    
    elif tile_type == "cashflow":
        # Cash Flow tile
        response = send_to_erp(
            "cashflow.xml",
            {
                "company": company,
                "from_date": dates["from_date"],
                "to_date": dates["to_date"],
                "current_date": dates["current_date"]
            }
        )
        
        tiles_dict = parse_tiles(response)
        return adapter_tiles(tiles_dict, tile_name="CashFlow")
    
    elif tile_type == "trading":
        # Trading tile (Sales, Purchases, Profit)
        response = send_to_erp(
            "trading.xml",
            {
                "company": company,
                "from_date": dates["from_date"],
                "to_date": dates["to_date"],
                "current_date": dates["current_date"]
            }
        )
        
        tiles_dict = parse_tiles(response)
        return adapter_tiles(tiles_dict, tile_name="Amount")
    
    else:
        # Unsupported tile type
        return {
            "error": f"Unsupported tile type: {tile_type}. Supported: 'trend', 'cashflow', 'trading'.",
            "summary": None,
            "dataframe_dict": None,
            "dataframe_id": None
        }


@tool("dashboard_tile_fetcher")
def dashboard_tile_fetcher(
    company: str,
    tile_type: str,
    query: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_date: Optional[str] = None,
    voucher_type: Optional[str] = None
) -> str:
    """
    Fetches and parses a ERP dashboard tile.
    Returns JSON with summary + dataframe for graph pipeline.
    """
    result = fetch_and_parse_tile(
        company=company,
        tile_type=tile_type,
        query=query,
        from_date=from_date,
        to_date=to_date,
        current_date=current_date,
        voucher_type=voucher_type
    )
    
    return json.dumps(result)
