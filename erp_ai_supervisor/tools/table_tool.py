from langchain.tools import tool
import pandas as pd


@tool("table_formatter")
def table_tool(
    dataframe_dict: dict,
    max_rows: int = 20,
    display_headers: list = None,   #  ADDITION
) -> str:
    """
    Convert a dataframe_dict into a Markdown table.
    Deterministic. No LLM involved.
    """

    if not dataframe_dict or not isinstance(dataframe_dict, dict):
        return "No tabular data available."

    # Rebuild DataFrame
    try:
        df = pd.DataFrame(dataframe_dict)
    except Exception as e:
        return f"Failed to build table: {e}"

    if df.empty:
        return "Table is empty."

    # Limit rows for safety
    df = df.head(max_rows)

    # Build Markdown table
    headers = list(df.columns)

    # USE DISPLAY HEADERS IF PROVIDED
    if display_headers and len(display_headers) == len(headers):
        headers_to_use = display_headers
    else:
        headers_to_use = headers

    lines = []
    
    # Professional header row with formatting
    header_row = "| " + " | ".join([f"**{h}**" for h in headers_to_use]) + " |"
    lines.append(header_row)
    
    # Separator with alignment hints (center-aligned for better look)
    sep_row = "| " + " | ".join([":---:" for _ in headers_to_use]) + " |"
    lines.append(sep_row)

    for _, row in df.iterrows():
        values = []
        for col in df.columns:
            val = row[col]
            # Format date columns as readable strings
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    if pd.isna(val):
                        val = "—"
                    else:
                        val = pd.Timestamp(val).strftime("%d-%b-%y")
                except:
                    val = "—"
            # Check for nanosecond timestamps
            elif isinstance(val, (int, float)) and 1e18 < val < 1e20:
                try:
                    val = pd.Timestamp(val, unit='ns').strftime("%d-%b-%y")
                except:
                    val = str(val)
            else:
                val = str(val) if val else "—"
            
            # Trim long values for readability
            if len(str(val)) > 50:
                val = str(val)[:47] + "..."
            values.append(val)
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)
