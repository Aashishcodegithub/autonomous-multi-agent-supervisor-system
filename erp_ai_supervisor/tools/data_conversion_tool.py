# tools/data_conversion_tool.py

import pandas as pd
from langchain.tools import tool
import uuid
import json


# ----------------------------------------------------
# Helper: Build JSON summary from a DataFrame
# ----------------------------------------------------
def build_df_summary(df: pd.DataFrame, sample_size: int = 5):

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



# ----------------------------------------------------
# Helper: Flatten nested dict into single-level dict
# ----------------------------------------------------
def flatten_dict(d, parent_key="", sep="_"):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())

        elif isinstance(v, list):
            items.append((new_key, v))

        else:
            items.append((new_key, v))

    return dict(items)



# ----------------------------------------------------
# NEW: Detect all list-of-dicts tables (parallel lists)
# ----------------------------------------------------
def find_all_tables(data: dict):
    """
    Find ALL repeated list-of-dict sections.
    Example in Stock Summary:
      DSPACCNAME -> 3 names
      DSPSTKINFO -> 3 stocks
    """
    tables = {}
    stack = [(None, data)]

    while stack:
        key, val = stack.pop()

        if isinstance(val, list) and all(isinstance(x, dict) for x in val):
            tables[key] = val

        elif isinstance(val, dict):
            for k, v in val.items():
                stack.append((k, v))

    return tables



# ----------------------------------------------------
# NEW: Try merging parallel tables
# ----------------------------------------------------
def merge_parallel_lists(tables: dict):
    """
    If multiple tables exist AND they all have same length,
    merge row-by-row.
    """
    if len(tables) < 2:
        return None

    keys = list(tables.keys())
    lists = [tables[k] for k in keys]

    # Check equal length
    lengths = {len(lst) for lst in lists}
    if len(lengths) != 1:
        return None

    merged = []
    row_count = lengths.pop()

    for i in range(row_count):
        row = {}
        for key, lst in tables.items():
            flat = flatten_dict(lst[i])
            for col, val in flat.items():
                row[f"{key}_{col}"] = val
        merged.append(row)

    return merged



# ----------------------------------------------------
# Helper: Old single table extractor (kept for fallback)
# ----------------------------------------------------
def extract_table_from_dict(data: dict):
    stack = [data]

    while stack:
        current = stack.pop()

        if isinstance(current, dict):
            for v in current.values():
                stack.append(v)

        elif isinstance(current, list):
            if all(isinstance(x, dict) for x in current):
                return current
            else:
                for item in current:
                    stack.append(item)

    return []


# ----------------------------------------------------
# Helper: Parse Sales Register (period-wise structure)
# ----------------------------------------------------
def parse_sales_register(report_dict: dict):
    """
    Extracts Sales Register data where:
    - DSPPERIOD: list of month names ['April', 'May', ...]
    - DSPACCINFO: list of dicts with credit/closing amounts
    Converts to: Month | Credit | ClosingBalance
    """
    rows = []
    
    # Get periods and account info from top level
    periods_list = report_dict.get("DSPPERIOD", [])
    accinfo_list = report_dict.get("DSPACCINFO", [])
    
    print(f"DEBUG: Periods: {periods_list}")
    print(f"DEBUG: AccInfo type: {type(accinfo_list)}, length: {len(accinfo_list) if isinstance(accinfo_list, list) else 'N/A'}")
    
    if isinstance(accinfo_list, list) and len(accinfo_list) > 0:
        print(f"DEBUG: First accinfo item: {accinfo_list[0]}")
    
    # Zip periods with account info
    if isinstance(accinfo_list, list):
        for i, period in enumerate(periods_list):
            if i < len(accinfo_list):
                accinfo = accinfo_list[i]
                
                # Extract credit and closing from nested structure
                # Flatten this one item to find the amounts
                flat_accinfo = flatten_dict(accinfo)
                
                print(f"DEBUG: Flattened accinfo[{i}] keys: {list(flat_accinfo.keys())}")
                
                # Find credit amount (DSPCRAMTA)
                credit_key = [k for k in flat_accinfo.keys() if "dspcramta" in k.lower()]
                closing_key = [k for k in flat_accinfo.keys() if "dspclamta" in k.lower()]
                
                print(f"DEBUG: Credit key: {credit_key}, Closing key: {closing_key}")
                
                credit = None
                closing = None
                
                if credit_key:
                    try:
                        credit_val = flat_accinfo[credit_key[0]]
                        credit = float(credit_val) if credit_val is not None else None
                        print(f"DEBUG: Period {i} ({period}) - Credit: {credit}")
                    except Exception as e:
                        print(f"DEBUG: Error converting credit: {e}")
                
                if closing_key:
                    try:
                        closing_val = flat_accinfo[closing_key[0]]
                        closing = float(closing_val) if closing_val is not None else None
                        print(f"DEBUG: Period {i} ({period}) - Closing: {closing}")
                    except Exception as e:
                        print(f"DEBUG: Error converting closing: {e}")
                
                row = {
                    "Month": str(period).strip() if period else "",
                    "Credit": credit,
                    "ClosingBalance": closing
                }
                rows.append(row)
                print(f"DEBUG: Added row: {row}")
    
    print(f"DEBUG: parse_sales_register final rows count: {len(rows)}")
    if rows:
        print(f"DEBUG: First row: {rows[0]}")
        print(f"DEBUG: Last row: {rows[-1]}")
    
    return rows if rows else None


# Cash Flow Parser
# -----------------------------------------------
def parse_cash_flow(report_dict: dict):
    """
    Extracts Cash Flow data:
    - DSPPERIOD: month name or list
    - DSPACCINFO: list with DSPCRAMT (inflow) and DSPDRAMT (outflow)
    Returns: Month | Inflow | Outflow | NetFlow
    """
    rows = []
    
    periods_raw = report_dict.get("DSPPERIOD")
    accinfo_raw = report_dict.get("DSPACCINFO")
    
    periods_list = periods_raw if isinstance(periods_raw, list) else ([periods_raw] if periods_raw else [])
    accinfo_list = accinfo_raw if isinstance(accinfo_raw, list) else ([accinfo_raw] if accinfo_raw else [])
    
    print(f"DEBUG CF: Periods count: {len(periods_list)}, AccInfo count: {len(accinfo_list)}")
    
    for i, period in enumerate(periods_list):
        if i < len(accinfo_list):
            accinfo = accinfo_list[i]
            inflow = None
            outflow = None
            
            if isinstance(accinfo, dict):
                # Get DSPCRAMT (credit/inflow)
                cramt = accinfo.get("DSPCRAMT")
                if cramt:
                    if isinstance(cramt, dict):
                        cramt = cramt.get("DSPCRAMTA") or list(cramt.values())[0] if cramt else None
                    try:
                        inflow = float(cramt) if cramt else None
                    except:
                        pass
                
                # Get DSPDRAMT (debit/outflow)
                dramt = accinfo.get("DSPDRAMT")
                if dramt:
                    if isinstance(dramt, dict):
                        dramt = dramt.get("DSPDRAMTA") or list(dramt.values())[0] if dramt else None
                    try:
                        outflow = abs(float(dramt)) if dramt else None
                    except:
                        pass
            
            netflow = None
            if inflow is not None and outflow is not None:
                netflow = inflow - outflow
            
            row = {
                "Month": str(period).strip() if period else "",
                "Inflow": inflow,
                "Outflow": outflow,
                "NetFlow": netflow
            }
            rows.append(row)
            print(f"DEBUG CF: Row {i}: {row}")
    
    print(f"DEBUG CF: Total rows: {len(rows)}")
    return rows if rows else None


# Helper: Convert non-tabular dict → rows
# -----------------------------------------------
def non_tabular_to_rows(report_dict: dict):

    flat = flatten_dict(report_dict)

    rows = []
    for k, v in flat.items():
        rows.append({"key": k, "value": v})

    return rows



# ----------------------------------------------------
# MAIN TOOL
# ----------------------------------------------------
@tool("data_conversion")
def data_conversion_tool(report_dict: dict, report_name: str = ""):
    """
    Universal data conversion tool for ERP reports.
    report_name: optional - helps distinguish similar structures (e.g., "Cash Flow" vs "Sales Register")
    """
    
    print(f"DEBUG: data_conversion_tool called with report_name='{report_name}'")

    #  STEP 0 — Route by report type if known
    if report_name and "cash flow" in report_name.lower():
        print(f"DEBUG: Routing to CASH FLOW parser")
        cf_rows = parse_cash_flow(report_dict)
        print(f"DEBUG: Cash Flow parser returned {len(cf_rows) if cf_rows else 0} rows")
        if cf_rows:
            print(f"DEBUG: CF First row: {cf_rows[0]}")
            df = pd.DataFrame(cf_rows)
            print(f"DEBUG: CF DataFrame columns: {df.columns.tolist()}")
            df = df.dropna(subset=["Month"])
            if not df.empty:
                summary = build_df_summary(df)
                df_id = f"df_{uuid.uuid4().hex[:8]}"
                return {
                    "summary": summary,
                    "dataframe_id": df_id,
                    "dataframe_dict": df.to_dict(orient="list")
                }
    
    #  STEP 1 — Default to Sales Register for periodic reports
    flat_check = flatten_dict(report_dict)
    has_period = any("dspperiod" in k.lower() for k in flat_check.keys())
    has_accinfo = any("dspaccinfo" in k.lower() for k in flat_check.keys())
    
    print(f"DEBUG: has_period={has_period}, has_accinfo={has_accinfo}")
    
    if has_period and has_accinfo:
        # Try Sales Register parser
        sr_rows = parse_sales_register(report_dict)
        print(f"DEBUG: Sales Register parser returned {len(sr_rows) if sr_rows else 0} rows")
        if sr_rows:
            print(f"DEBUG: First row: {sr_rows[0]}")
            df = pd.DataFrame(sr_rows)
            print(f"DEBUG: DataFrame columns: {df.columns.tolist()}")
            # Remove rows with missing critical data
            df = df.dropna(subset=["Month"])
            if not df.empty:
                summary = build_df_summary(df)
                df_id = f"df_{uuid.uuid4().hex[:8]}"
                return {
                    "summary": summary,
                    "dataframe_id": df_id,
                    "dataframe_dict": df.to_dict(orient="list")
                }

    #  STEP 1 — Detect ALL tables (parallel lists included)
    all_tables = find_all_tables(report_dict)

    #  STEP 2 — Try smart merge (Stock Summary, etc.)
    merged_rows = merge_parallel_lists(all_tables)

    if merged_rows:
        # Parallel lists successfully merged
        df = pd.DataFrame(merged_rows)

    else:
        #  STEP 3 — Default old logic

        # case A: single table
        rows = extract_table_from_dict(report_dict)

        if rows:
            flattened_rows = [flatten_dict(r) for r in rows]
            df = pd.DataFrame(flattened_rows)

            for col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col])
                    # Format datetime columns as readable strings (not nanosecond timestamps)
                    if df[col].dtype == 'datetime64[ns]':
                        df[col] = df[col].dt.strftime('%Y-%m-%d')
                except:
                    pass

        else:
            # case B: fallback flatten
            fallback_rows = non_tabular_to_rows(report_dict)
            df = pd.DataFrame(fallback_rows)

            if "value" in df.columns:
                df["value"] = pd.to_numeric(df["value"], errors="ignore")


    # -----------------------------------------------
    # FIX NEGATIVE VALUES FROM ERP XML (Stock Value)
    # COMMENTED OUT - Stock items should preserve original signs
    # -----------------------------------------------
    # if "DSPSTKINFO_DSPSTKCL_DSPCLAMTA" in df.columns:
    #     try:
    #         df["DSPSTKINFO_DSPSTKCL_DSPCLAMTA"] = (
    #             pd.to_numeric(df["DSPSTKINFO_DSPSTKCL_DSPCLAMTA"], errors="coerce") * -1
    #         )
    #     except:
    #         pass


    # ----------------------------------------------------
    #  UNIVERSAL FIX: Convert ALL numeric columns to abs()
    # ----------------------------------------------------
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="ignore")

    for col in df.select_dtypes(include=["number"]).columns:
        # Preserve original sign of numeric values so negative amounts remain negative
        # Previously we converted all numbers to absolute values which hid debit/credit signs.
        # Commenting out the universal abs() conversion so plots reflect original signed values.
        # df[col] = df[col].abs()
        pass


    #  STEP 4 — Build summary
    summary = build_df_summary(df)

    #  STEP 5 — Unique df_id
    df_id = f"df_{uuid.uuid4().hex[:8]}"

    return {
        "summary": summary,
        "dataframe_id": df_id,
        "dataframe_dict": df.to_dict(orient="list")
    }
