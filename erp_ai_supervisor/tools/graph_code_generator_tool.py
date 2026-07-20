# tools/graph_code_generator_tool.py

from langchain_core.tools import tool   
import google.generativeai as genai     
from dotenv import load_dotenv
import os
import json
from typing import Optional

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")     
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")  


@tool("graph_code_generator")
def graph_code_generator(
    summary: dict,
    user_graph_preference: Optional[str] = None,
    title: Optional[str] = None,
    report: Optional[str] = None,
) -> str:
    """
    Generates SAFE matplotlib code from a DataFrame summary.
    Accepts optional report name for report-specific constraints.
    """

    if not API_KEY:
        return "Missing GEMINI_API_KEY in .env"   

    #  Initialize Gemini client
    genai.configure(api_key=API_KEY)
    client = genai.GenerativeModel(MODEL_NAME)

    summary_json = json.dumps(summary, indent=2)

    # ⭐ NEW: Analyze which columns have actual data (non-null values)
    columns = summary.get("columns", [])
    sample_rows = summary.get("sample_rows", [])
    
    # Find columns that are NOT empty (have at least some non-null values)
    has_data = {}
    for col in columns:
        has_non_null = any(
            row.get(col) is not None and str(row.get(col)).lower() != "nan"
            for row in sample_rows
        )
        has_data[col] = has_non_null
    
    # Create a list of usable columns
    usable_columns = [col for col, has_val in has_data.items() if has_val]
    non_usable_columns = [col for col, has_val in has_data.items() if not has_val]
    
    column_info = f"""
AVAILABLE COLUMNS:
- Columns with data: {usable_columns}
- Columns that are EMPTY (all NULL): {non_usable_columns}

IMPORTANT: NEVER try to plot empty columns. Only use columns from the "with data" list.
If a column is in the empty list, do NOT reference it in the code.
"""

    preference_text = (
        f"The user requested a {user_graph_preference} chart."
        if user_graph_preference
        else "The user did not specify a chart type. Choose the most appropriate one."
    )

    title_text = (
        f'Use this as the chart title: "{title}".'
        if title
        else "If a title is appropriate, choose a clear, short title."
    )

    # 🎯 LARGE DATASET CONSTRAINT (applies to all reports with many parties)
    large_dataset_constraint = ""
    row_count = summary.get("row_count", 0)
    has_party_column = any("party" in col.lower() or "customer" in col.lower() for col in columns)
    
    if row_count > 50 and has_party_column:
        large_dataset_constraint = """
=================================================
⭐ IMPORTANT: LARGE DATASET DETECTED ⭐
=================================================
The dataset has many rows with a Party/Customer column. For readability:
1. FILTER the dataframe to show ONLY the TOP 20 parties by frequency
2. Use this code before plotting:
   party_col = [col for col in df.columns if 'party' in col.lower() or 'customer' in col.lower()][0]
   top_20_parties = df[party_col].value_counts().head(20).index.tolist()
   df_plot = df[df[party_col].isin(top_20_parties)].copy()
3. Use df_plot instead of df in all plotting commands
4. The visualization will show the TOP 20 parties/companies, making it clean and readable
"""


    # 🎯 BILLS RECEIVABLE-SPECIFIC CONSTRAINT
    bills_receivable_constraint = ""
    if report and report.lower().strip() == "bills receivable":
        bills_receivable_constraint = """
=================================================
⭐ SPECIAL RULE FOR BILLS RECEIVABLE ⭐
=================================================
If the data has string columns like BillParty, Party, BillRef, BillDate (NO numeric amount columns):
1. Count the number of bills/transactions per party using: df.groupby('Party').size() or df.groupby('BillParty').size()
2. Create a BAR CHART with Party names on X-axis and bill count on Y-axis
3. Use blue bars (#6FAFE8) with a light grid background
4. Set figure size to (14, 6) to accommodate many party names
5. Rotate X-axis labels 45 degrees for readability
6. Add value labels on top of each bar showing the count
7. Use bold font for labels
8. Title should be "Number of Bills by Party" or similar
"""

    # 🎯 SALES REGISTER-SPECIFIC CONSTRAINT
    sales_register_constraint = ""
    if report and report.lower().strip() == "sales register":
        sales_register_constraint = """
=================================================
⭐ SPECIAL RULE FOR SALES REGISTER ⭐
=================================================
If the data appears to be from a Sales Register (has multiple amount columns like Credit and ClosingBalance):
1. Generate EXACTLY 2 subplots (stacked vertically using plt.subplots(2, 1))
2. Top subplot: First amount column by Month (line chartor bar chart as per instruction given by user with markers, blue color)
3. Bottom subplot: Second amount column by Month (line chart with markers, blue color)
4. Both use consistent styling with grid, bold labels, and figure size (12, 8)
5. Use plt.suptitle() for overall title
6. Call plt.tight_layout() at the end
"""

    # 🎯 CASH FLOW-SPECIFIC CONSTRAINT
    cash_flow_constraint = ""
    if report and report.lower().strip() == "cash flow":
        cash_flow_constraint = """
=================================================
⭐ SPECIAL RULE FOR CASH FLOW ⭐
=================================================
If the data appears to be from Cash Flow (has Inflow, Outflow, and NetFlow columns):

CRITICAL: NetFlow can have NEGATIVE values. Handle as follows:
- Inflow: Always positive, plot as-is (blue #1f77b4), ADD VALUE LABELS ON TOP OF BARS
- Outflow: Always positive, plot as-is (green #2ca02c), ADD VALUE LABELS ON TOP OF BARS
- NetFlow: Can be positive or NEGATIVE
  * Use ABSOLUTE value for bar HEIGHT (so negative bars are VISIBLE and point upward)
  * For bar color: Use red (#d62728) for ALL NetFlow values (both positive and negative)
  * For bar ANNOTATION/LABEL: Show the ORIGINAL SIGNED value (e.g., "-500000" for negative)
  * This ensures: (1) all bars visible upward, (2) negatives clearly marked in red, (3) original values shown

IMPLEMENTATION DETAILS:
1. Generate a GROUPED BAR CHART showing all three values together by Month
2. Bar width: 0.25 per group
3. Spacing: x_pos = np.arange(len(months))
   - Inflow: x_pos - 0.25 (blue)
   - Outflow: x_pos + 0.0 (green)
   - NetFlow: x_pos + 0.25 (red, use np.abs() for heights)

4. PLOT ALL THREE BAR GROUPS:
   plt.bar(x_pos - 0.25, df['Inflow'], width=0.25, label='Inflow', color='#1f77b4')
   plt.bar(x_pos + 0.0, df['Outflow'], width=0.25, label='Outflow', color='#2ca02c')
   netflow_heights = np.abs(df['NetFlow'])
   plt.bar(x_pos + 0.25, netflow_heights, width=0.25, label='NetFlow', color='#d62728')

5. ADD VALUE LABELS FOR ALL THREE METRICS (MANDATORY - do not skip):
   # Inflow labels (on top of blue bars)
   for i, (pos, val) in enumerate(zip(x_pos - 0.25, df['Inflow'])):
       offset = max(df['Inflow'].max(), df['Outflow'].max(), np.abs(df['NetFlow']).max()) * 0.02
       plt.text(pos, val + offset, f"{val:.0f}", ha='center', va='bottom', fontsize=8)
   
   # Outflow labels (on top of green bars)
   for i, (pos, val) in enumerate(zip(x_pos + 0.0, df['Outflow'])):
       offset = max(df['Inflow'].max(), df['Outflow'].max(), np.abs(df['NetFlow']).max()) * 0.02
       plt.text(pos, val + offset, f"{val:.0f}", ha='center', va='bottom', fontsize=8)
   
   # NetFlow labels (on top of red bars, use SIGNED original values)
   max_val = max(df['Inflow'].max(), df['Outflow'].max(), np.abs(df['NetFlow']).max())
   offset = max_val * 0.02
   for i, (pos, height, signed_val) in enumerate(zip(x_pos + 0.25, netflow_heights, df['NetFlow'])):
       plt.text(pos, height + offset, f"{signed_val:.0f}", ha='center', va='bottom', fontsize=8)

6. Grid: Horizontal lines only (axis='y') with alpha=0.3
7. Legend: Upper-right, fontsize=10, with clear labels "Inflow", "Outflow", "NetFlow"
8. Font styling:
   - X-axis labels: 11pt, regular weight
   - Y-axis labels: 10pt, regular weight
   - Title: 14pt, bold weight
   - Value labels: 8pt, dark color
9. Title: "Cash Flow Analysis by Month"
10. Figure size: (14, 7)
11. Margins: Add plt.tight_layout() to prevent label cutoff
12. Y-axis: Dynamic range based on maximum value
13. RESULT: All three metrics clearly visible with value labels, negative NetFlow shown in red with negative labels.
"""

    prompt = f"""
You are a Python matplotlib code generator for FINANCIAL DATA VISUALIZATION.
Generate PROFESSIONAL, PUBLICATION-READY charts that are visually appealing and easy to understand.

{large_dataset_constraint}



{bills_receivable_constraint}

{sales_register_constraint}

{cash_flow_constraint}

CORE RULES:
- NEVER output the word "python".
- NEVER output markdown or backticks.
- You MAY import numpy (import numpy as np) — this is REQUIRED for grouped bar charts
- NEVER import anything else beyond numpy and matplotlib.
- NEVER use pandas or 'pd'.
- NEVER write df = pd...
- NEVER call df.dropna(), df.astype(), or df.to_numeric().
- You may ONLY use 'df' (DataFrame already cleaned), 'np' (numpy), and 'plt'.
- The dataframe is already preprocessed—do NOT clean or convert anything.

ALLOWED MATPLOTLIB FUNCTIONS:
- df['col'], df.groupby(), df.sum(), df.sort_values()
- np.arange(), np.array() — for creating array positions and manipulations
- plt.figure(), plt.subplot(), plt.plot(), plt.bar(), plt.pie(), plt.scatter()
- plt.xlabel(), plt.ylabel(), plt.title(), plt.legend(), plt.grid()
- plt.xticks(), plt.yticks(), plt.tight_layout(), plt.text()
- plt.bar_label() — for adding value labels on bars

STYLING REQUIREMENTS (MUST INCLUDE):
1. FIGURE SIZE: Always start with plt.figure(figsize=(12, 6))
2. STYLE: Use plt.style.use('seaborn-v0_8-darkgrid') for professional look
3. TITLES & LABELS:
   - Make all titles BOLD and large (fontsize=16, fontweight='bold')
   - Make axis labels clear and bold (fontsize=12, fontweight='bold')
   - CRITICAL: Always set plt.xlabel() and plt.ylabel() with proper, human-readable names derived from the column names. Examples: if column is 'Month' or 'BSNAME_...', use 'Month' for X-axis; if column is 'Amount' or 'BSAMT_BSMAINAMT', use 'Amount' for Y-axis.
4. GRIDLINES: Add plt.grid(True, alpha=0.3) for readability
5. BAR DIRECTION (CRITICAL FOR ALL BAR CHARTS):
   - ALL BAR CHARTS MUST FACE UPWARD (positive direction)
   - NEVER use barh() for horizontal bars
   - Even if the value is negative the bars should be displayed as upward-facing bars
   - NO negative bars extending downward
   - If data contains negative values, display them as positive (use absolute value)
6. COLORS (use context-appropriate coloring):
   - For GROUPED BAR CHARTS (multiple series): Use distinct, professional colors (blue, green, red for different metrics - NOT based on positive/negative)
     Examples: Inflow (#1f77b4 blue), Outflow (#2ca02c green), NetFlow (#d62728 red)
   - For SINGLE SERIES or stacked bars (positive values only): use light blue `#6FAFE8`
   - For TWO POSITIVE SERIES: use two distinguishable blue shades: `#6FAFE8` (lighter) and `#3E92D1` (darker)
   - For SINGLE NEGATIVE SERIES: use red `#E24A4A`
   - For CHARTS WITH BOTH POSITIVE AND NEGATIVE (not grouped bars): positive=blue shades, negative=red shades
   - Do NOT use any other hues or colors in the plotted data (axes, grid, and text may remain default styling)
7. VALUE ANNOTATIONS (MANDATORY FOR ALL CHARTS):
   - For BAR CHARTS: Use plt.bar_label() OR loop: [plt.text(i, v + offset, str(round(v, 2)), ha='center', va='bottom', fontsize=12) for i, v in enumerate(y_data)]
   - For LINE CHARTS: for i, (x, y) in enumerate(zip(x_data, y_data)): plt.text(x, y + max(y_data)*0.03, str(round(y, 2)), ha='center', va='bottom', fontsize=11)
   - For PIE CHARTS: Add autopct='%1.1f%%' to plt.pie()
   - CRITICAL: Use actual data values from loops/arrays, NOT undefined variable names like "value"
   - Calculate offset as: max_value * 0.02 to 0.05 for line charts
7. LEGEND (MANDATORY - NEVER SKIP):
   - ALWAYS include plt.legend() in every chart without exception
   - For bar/line charts with multiple series: Add label parameter to each plt.plot() or plt.bar() call
   - For pie charts: Add labels parameter to plt.pie() with plt.legend()
   - For single series: Still add legend to identify the metric (e.g., label='Credit' or label='Amount')
   - Position: Use loc='upper right' or 'best' for automatic optimal placement
   - Font size: fontsize=10
   - CRITICAL: If you plotted data, you MUST have plt.legend() to explain what's being shown
   - Example: plt.plot(x, y, label='Revenue', color='blue'); plt.legend(loc='upper right', fontsize=10)
8. LAYOUT: Always end with plt.tight_layout() to prevent label cutoff

FINANCIAL DATA SPECIFICS:
- This is financial/accounting data
- Use colors meaningfully: GREEN for profits/assets, RED for losses/liabilities
- For time series: Use line charts with markers
- For composition: Use stacked bars or pie charts
- For comparison: Use grouped or side-by-side bars

{column_info}

DATA SUMMARY:
{summary_json}

USER PREFERENCE:
{preference_text}

TITLE INSTRUCTIONS:
{title_text}

TASK:
Generate ONLY the matplotlib code needed to produce a PROFESSIONAL chart.
- Only use columns that have data (from the "with data" list above)
- Skip any empty columns
- Include ALL styling requirements above
- Make the chart visually appealing and easy to interpret
- Do NOT add comments
- Do NOT explain
- Do NOT wrap in quotes

SPECIAL PLOTTING RULE FOR NEGATIVE VALUES:
- If a numeric series contains negative values, apply the SAME rule for both bar and line charts: plot using ABSOLUTE VALUES (so negative bars/points appear in the same positive quadrant as positives), color them RED, and annotate with original SIGNED values.
- For BAR CHARTS: Plot using ABSOLUTE VALUES for heights (so negative bars point upward), color them RED, annotate with original SIGNED values.
  Example:
        vals = df['Col']
        plot_vals = vals.abs()
        colors = ["#6FAFE8" if v >= 0 else "#E24A4A" for v in vals]
        plt.bar(df['Month'], plot_vals, color=colors)
        for x, y, orig in zip(df['Month'], plot_vals, vals):
            plt.text(x, y, f"{{orig}}", ha='center', va='bottom')

- For LINE CHARTS: Plot using ABSOLUTE VALUES for heights (so negative points appear in the positive axis), color segments/points RED for negatives and BLUE for positives, annotate with original SIGNED values.
  CRITICAL: Create TWO legend entries (one for Positive=blue, one for Negative=red) in 'upper right' corner WITHOUT importing matplotlib.lines. Use dummy plt.plot lines instead.
  CRITICAL: Derive human-readable X and Y labels from column names. For X-axis (category column): if name contains 'BSNAME', use 'Item'; if 'DSPPERIOD', use 'Month'; if 'DSPDISPNAME', use 'Name'. For Y-axis (amount column): if name contains 'AMT' or 'BSMAINAMT', use 'Amount'; if 'DSPCLAMTA', use 'Amount'.
  Example:
        vals = df['Col']
        plot_vals = vals.abs()
        x_vals = df['Month']
        # Humanize labels from column names
        y_label = 'Amount'  # or derive from column name
        x_label = 'Month'   # or 'Item', 'Name', etc., derived from column name
        has_positive = (vals >= 0).any()
        has_negative = (vals < 0).any()
        for i in range(len(vals) - 1):
            color = "#6FAFE8" if vals.iloc[i] >= 0 else "#E24A4A"
            plt.plot(x_vals.iloc[i:i+2], plot_vals.iloc[i:i+2], color=color, marker='o', linewidth=2)
        for x, y, orig in zip(x_vals, plot_vals, vals):
            offset = y * 0.02
            plt.text(x, y + offset, f"{{orig}}", ha='center', va='bottom', fontsize=10)
        # Create legend using dummy lines (no import needed)
        legend_lines = []
        if has_positive:
            legend_lines.append(plt.Line2D([0], [0], color='#6FAFE8', lw=2, label='Positive'))
        if has_negative:
            legend_lines.append(plt.Line2D([0], [0], color='#E24A4A', lw=2, label='Negative'))
        if legend_lines:
            plt.legend(handles=legend_lines, loc='upper right')
        plt.xlabel(x_label, fontsize=12, fontweight='bold')
        plt.ylabel(y_label, fontsize=12, fontweight='bold')
"""

    try:
    
        response = client.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )

        code = response.text or ""
        code = code.replace("\r", "").strip()

        # Remove accidental "python"
        lines = code.split("\n")
        if lines and lines[0].strip().lower() == "python":
            lines = lines[1:]
        code = "\n".join(lines).strip()

        # Remove fenced blocks
        if code.startswith("```"):
            code = code.split("```")[1].strip()
        if code.endswith("```"):
            code = code.replace("```", "").strip()

        return code.strip()

    except Exception as e:
        return f"Graph code generation failed: {str(e)}"
