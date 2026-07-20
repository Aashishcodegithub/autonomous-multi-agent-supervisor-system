# agents/summarization_agent.py

from dotenv import load_dotenv
import os
import json

from gemini_wrapper import GeminiLLM

# This tool is still imported in case you want generic text summarization later.
from tools.summarization_tool import summarize_text

# 🔹 NEW IMPORTS – to fetch ERP report data
from tools.get_report_tool import get_report

load_dotenv()

llm = GeminiLLM(
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
    temperature=0.0,
)

# --------------------------------------------------------
# OPTION A — FIX NEGATIVE VALUES BEFORE PROCESSING
# --------------------------------------------------------
def fix_negative_values(raw_dict):
    """
    Fix negative values in ERP extracts for categories that should
    NEVER be negative (common in P&L and BS conversions).

    Rules:
    - For P&L (PLSUBAMT, BSMAINAMT):
        Negative Opening Stock, Closing Stock, Purchase Accounts,
        Indirect Incomes, Indirect Expenses → convert to positive.
    - For Balance Sheet:
        If an item contains the word 'asset' and has negative value,
        convert to positive.
    """

    # -------------------- Fix P&L values --------------------
    pl_names = raw_dict.get("DSPACCNAME", [])
    pl_amts = raw_dict.get("PLAMT", [])

    PNL_KEYWORDS = [
        "opening stock",
        "closing stock",
        "purchase",
        "indirect income",
        "indirect incomes",
        "indirect expense",
        "indirect expenses",
    ]

    for i, nblock in enumerate(pl_names):
        try:
            disp = nblock.get("DSPDISPNAME", "").lower()
            if any(k in disp for k in PNL_KEYWORDS):

                amtblock = pl_amts[i]

                # Fix PLSUBAMT
                if "PLSUBAMT" in amtblock:
                    try:
                        v = float(amtblock["PLSUBAMT"])
                        if v < 0:
                            amtblock["PLSUBAMT"] = str(abs(v))
                    except:
                        pass

                # Fix BSMAINAMT
                if "BSMAINAMT" in amtblock:
                    try:
                        v = float(amtblock["BSMAINAMT"])
                        if v < 0:
                            amtblock["BSMAINAMT"] = str(abs(v))
                    except:
                        pass
        except:
            continue

    # -------------------- Fix Balance Sheet "Assets" negativity --------------------
    bs_names = raw_dict.get("BSNAME", [])
    bs_amts = raw_dict.get("BSAMT", [])

    for i, nblock in enumerate(bs_names):
        try:
            disp = (
                nblock.get("DSPACCNAME", {})
                .get("DSPDISPNAME", "")
                .lower()
            )
            if "asset" in disp:
                amtblock = bs_amts[i]
                if "BSMAINAMT" in amtblock:
                    try:
                        v = float(amtblock["BSMAINAMT"])
                        if v < 0:
                            amtblock["BSMAINAMT"] = str(abs(v))
                    except:
                        pass
        except:
            continue

    return raw_dict


# --------------------------------------------------------
# Convert raw XML→dict into readable lines
# --------------------------------------------------------
def convert_raw_dict_to_text(raw_dict):
    """
    Convert the XML→dict structure into readable text with corrected sign logic.
    This is especially tuned for Balance Sheet (BSNAME / BSAMT), but will still
    fall back gracefully for other reports.
    """
    lines = []

    names = raw_dict.get("BSNAME", [])
    amts = raw_dict.get("BSAMT", [])

    for name_block, amt_block in zip(names, amts):
        try:
            name = (
                name_block.get("DSPACCNAME", {})
                .get("DSPDISPNAME", "")
            )
            amount_raw = amt_block.get("BSMAINAMT", "")

            # Convert string to float safely
            try:
                amount = float(amount_raw)
            except Exception:
                amount = amount_raw

            # Correct negative values for Asset categories
            if name and isinstance(amount, float):
                if "asset" in name.lower() and amount < 0:
                    amount = abs(amount)

            if name:
                lines.append(f"{name} has a balance of {amount}.")
        except Exception:
            continue

    full_text = "\n".join(lines)

    if not full_text.strip():
        full_text = str(raw_dict)

    return full_text


# --------------------------------------------------------
# Main entry used by the supervisor Tool
# --------------------------------------------------------
def run_summarization_agent(user_input: str) -> str:

    data = None
    user_query = None

    # Try to interpret input as JSON
    if isinstance(user_input, dict):
        data = user_input
    else:
        try:
            data = json.loads(user_input)
        except Exception:
            data = None

    # Extract query if present (for query-aware summaries)
    if isinstance(data, dict):
        user_query = data.get("query")

    # --------------------------------------
    # MODE 1 – Summarize a ERP report
    # --------------------------------------
    if isinstance(data, dict) and data.get("company") and data.get("report"):
        company = data.get("company")
        report = data.get("report")

        try:
            raw_dict = get_report.func(company, report)
        except Exception as e:
            return f"Failed to fetch report for summary: {str(e)}"

        #  APPLY OPTION A FIX HERE
        raw_dict = fix_negative_values(raw_dict)

        # Convert dict → human-readable lines
        nl_text = convert_raw_dict_to_text(raw_dict)

        # Build prompt with optional query-specific section
        prompt_for_paragraph = (
            "You are a professional financial analyst summarizing a ERP financial report.\n"
            "Your task: Create a PROFESSIONAL, STRUCTURED financial summary with the following format:\n\n"
            "## EXECUTIVE SUMMARY\n"
            "[One concise paragraph highlighting key financial position and major figures]\n\n"
            "## KEY ACCOUNTS & BALANCES\n"
            "[List 3-5 most significant accounts with their balances in tabular format]\n\n"
            "## FINANCIAL INSIGHTS\n"
            "[2-3 brief observations about the financial health, trends, or areas of concern]\n\n"
        )
        
        # Add query-specific section if user provided a query
        if user_query:
            prompt_for_paragraph += (
                f"[Focused analysis addressing: {user_query}]\n"
                "[Extract data and insights directly related to this query]\n\n"
            )
        
        prompt_for_paragraph += (
            "## IMPORTANT NOTES\n"
            "[Any critical observations or items requiring attention]\n\n"
            "REQUIREMENTS:\n"
            "- Use INR (₹) for all currency values - DO NOT convert to any other currency\n"
            "- Format large numbers with commas for readability (e.g., ₹1,50,00,000)\n"
            "- Be precise with account names as they appear in the report\n"
            "- Use professional financial terminology\n"
            "- Provide actionable insights, not just raw data\n"
            "- Maintain a formal, business-appropriate tone\n"
            + ("- In Query-Specific Analysis, focus heavily on data relevant to the user's query\n" if user_query else "")
            + f"\nFINANCIAL DATA:\n{nl_text}"
        )

        try:
            summary_text = llm(prompt_for_paragraph).strip()
        except Exception as e:
            summary_text = f"Summary generation failed: {str(e)}"

        return summary_text

    # --------------------------------------
    # MODE 2 – Generic free-text summary
    # --------------------------------------
    prompt_generic = (
        "You are a professional business analyst. Provide a COMPREHENSIVE summary of the following text.\n"
        "Use this format:\n\n"
        "## OVERVIEW\n"
        "[One concise paragraph with the main idea and key takeaways]\n\n"
        "## KEY POINTS\n"
        "[3-5 most important points in bullet format]\n\n"
        "## SIGNIFICANCE\n"
        "[Why this matters and any recommended actions]\n\n"
        "REQUIREMENTS:\n"
        "- Be professional and business-appropriate\n"
        "- Extract and highlight the most valuable information\n"
        "- Use clear, accessible language\n"
        "- Provide actionable insights where applicable\n\n"
        f"TEXT TO SUMMARIZE:\n{user_input}"
    )

    try:
        return llm(prompt_generic).strip()
    except Exception as e:
        return f"Summary generation failed: {str(e)}"


def react_summarization_agent(json_str: str) -> str:
    """
    Wrapper tool called by supervisor.
    Accepts JSON string OR plain text → returns structured JSON output.
    """
    try:
        data = json.loads(json_str)
        # If it's JSON, it should have company/report
        if isinstance(data, dict) and "company" in data and "report" in data:
            summary_text = run_summarization_agent(json_str)
        else:
            # Plain JSON object that's not structured
            summary_text = run_summarization_agent(json_str)
    except Exception:
        # It's plain text, not JSON
        summary_text = run_summarization_agent(json_str)
    
    # Always return JSON with summary_text key
    output = {
        "summary_text": summary_text,
        "type": "summary"
    }
    
    return json.dumps(output)
