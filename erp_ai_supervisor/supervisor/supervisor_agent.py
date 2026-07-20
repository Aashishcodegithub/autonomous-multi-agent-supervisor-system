# supervisor/supervisor_agent.py
from dotenv import load_dotenv
import os
import json
import logging
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool

from agents.report_agent import run_report_agent
from agents.summarization_agent import run_summarization_agent, react_summarization_agent
from agents.graph_agent import react_graph_agent
from agents.dashboard_agent import react_dashboard_agent



#  ADDITION — TABLE AGENT IMPORT
from agents.table_agent import react_table_agent

#  VECTOR DB IMPORTS
from report_lookup import lookup_erp_report
from vector_store import get_best_report

#  SWITCHED TO GEMINI WRAPPER (minimal change)
from gemini_wrapper import GeminiLLM

logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================
# HARDCODED COMPANY FOR FRONTEND INTEGRATION
# ============================================================
# Set this to your company name. When set, all requests will use this company
# without asking the user. This allows multiple pipelines to run with different
# payloads but the same company.
# To use: Uncomment and set to your company name
HARDCODED_COMPANY = "Modi Chemplast Materials Pvt Ltd"

# Example - uncomment and set:
# HARDCODED_COMPANY = "Modi Chemplast Materials Pvt Ltd"

# ============================================================
# LLM – Gemini backend (minimal change)
# ============================================================
llm = GeminiLLM(
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
    temperature=0.0,
)

# ------------------------------------------------------------
#  INTERNAL MEMORY FOR COMPANY (MINIMAL ADDITION)
# ------------------------------------------------------------
supervisor_state = {"last_company": None}

# ============================================================
# VECTOR DB-BASED REPORT RESOLVER
# ============================================================

def extract_graph_type(text: str) -> str:
    """Extract graph visualization type from user query."""
    t = text.lower()
    if "pie" in t:
        return "pie"
    if "bar" in t:
        return "bar"
    if "line" in t or "linear" in t:
        return "line"
    return "auto"


def resolve_with_vector_db(input_payload):
    """
    Use Vector DB to resolve report name from query.
    Returns enriched JSON with report, graph_type, etc.
    """
    if not isinstance(input_payload, dict):
        try:
            input_payload = json.loads(input_payload)
        except:
            return input_payload

    query = input_payload.get("query", "")

    # Try vector DB lookup
    try:
        report_name = get_best_report(query)
        input_payload["report"] = report_name
    except ValueError as e:
        # Vector DB couldn't confidently match - ask user to clarify
        input_payload["error"] = str(e)
        return input_payload

    # Extract graph type from query
    gt = extract_graph_type(query)
    if gt != "auto":
        input_payload["graph_type"] = gt

    return input_payload


# ------------------------------------------------------------
# Supervisor tools
# ------------------------------------------------------------
supervisor_tools = [
    Tool(
        name="lookup_erp_report",
        func=lookup_erp_report,
        description=(
            "Resolve the best ERP report to use based on user query. "
            "Input: natural languag  question. Output: exact report name. "
            "Use this FIRST to determine which report to fetch."
        )
    ),
    Tool(
        name="report_agent",
        func=lambda x: run_report_agent(x),
        description="Fetch ERP reports or list companies. Input is a plain user query string."
    ),
    Tool(
        name="summary_agent",
        func=react_summarization_agent,
        description=(
            "Summarize any text or ERP report and return structured JSON. "
            "Input can be plain text OR a JSON string with 'company', 'report', and optional 'query'. "
            "If 'query' is provided, the summary will include query-specific analysis focused on the user's question."
        )
    ),
    Tool(
        name="graph_agent",
        func=react_graph_agent,
        description=(
            "Generate graphs from a ERP report. "
            "Input must be JSON containing: company, report, and optional graph_type & title."
        )
    ),
    #  ADDITION — TABLE AGENT TOOL (TERMINAL)
    Tool(
        name="table_agent",
        func=react_table_agent,
        description=(
            "Return report data strictly as a table. "
            "Input must be JSON containing: company, report, optional max_rows."
        )
    ),
    #  ADDITION — DASHBOARD AGENT TOOL (for trends, tiles)
    Tool(
        name="dashboard_agent",
        func=react_dashboard_agent,
        description=(
            "Fetch and visualize dashboard tiles like sales/purchase trends. "
            "Input must be JSON containing: company, tile_type (trend/trading/assets). "
            "Optional: query, voucher_type (Sales/Purchase), from_date, to_date, current_date."
        )
    ),
]

# ------------------------------------------------------------
# UPDATED SUPERVISOR PROMPT (ONLY THIS SECTION CHANGED)
# ------------------------------------------------------------
SUPERVISOR_PROMPT = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="""
You are a ReAct Supervisor Agent capable of MULTI-TOOL CHAINING.

Your job:
1. Understand the user's complete request (may have multiple intents)
2. Route to appropriate tool(s) in correct sequence
3. Use tool results to make next decision
4. Chain tools if needed (e.g., table_agent THEN graph_agent)
5. Return Final Answer with all results merged

DO NOT ask follow-up questions. Execute the user's request.

Use internal Chain-of-Thought (CoT) reasoning but NEVER reveal it.  
Your output must follow the ReAct format: Thought → Action → Action Input.

The user input may be:
- A plain natural-language question, OR
- A JSON object string containing:
  - "query": the natural-language question
  - "company": the selected company
  - "report": the ERP report name (may be missing before resolution)
  - "graph_type": optional ("bar", "line", "pie", "auto")


AVAILABLE TOOLS:
{tools}

TOOL NAMES:
{tool_names}

=================================================
STEP 0 — REPORT RESOLUTION LAYER (CRITICAL)
=================================================
Before routing begins, the system automatically runs an external 
report_resolver_agent *if the input contains only "query" and "company"*
and DOES NOT contain "report".

The resolver produces a structured JSON:

{{
  "query": "...",
  "company": "...",
  "report": "...",         
  "graph_type": "auto"     
}}

Therefore:
- You ALWAYS receive a fully preprocessed and resolved JSON input.
- You NEVER need to infer the report yourself.
- If resolver cannot determine the report → "report" may be missing.
Your ONLY responsibility is routing.

=================================================
STEP 1 — EXTRACT USER QUESTION
=================================================
If input JSON contains "query" → treat that as the user’s question.  
Otherwise → treat the entire input string as the question.

=================================================
STEP 2 — REPORT IDENTIFICATION (LEGACY FALLBACK)
=================================================
These rules exist ONLY for backward compatibility.
Use them ONLY when the resolved input does NOT include "report".

--------------- BALANCE SHEET ----------------
Keywords:
- capital account, capital
- loan, loans, liability, liabilities
- current liabilities
- fixed assets, current assets
- opening balance, current period
- difference in opening balances
- assets, liabilities

--------------- PROFIT & LOSS ----------------
Keywords:
- opening stock, closing stock
- purchase accounts, purchases
- sales accounts, sales
- gross profit, net profit, nett profit
- indirect expenses, indirect incomes

--------------- STOCK SUMMARY ----------------
Keywords:
- quantity, qty
- rate, value
- pcs, pieces

PRIORITY:
1. Explicit report (from resolver) ALWAYS wins.
2. If resolver did not find a report → infer using keywords.
3. If multiple matches → Balance Sheet > Profit & Loss > Stock Summary.

=================================================
STEP 3 — INTELLIGENT SEMANTIC INTENT CLASSIFICATION
=================================================
DO NOT use keyword matching. Use SEMANTIC UNDERSTANDING.

Analyze what the user ACTUALLY WANTS based on their goal:

1. GRAPH/VISUALIZATION INTENT: User wants to UNDERSTAND PATTERNS or COMPARE visually
   - Questions: "show/visualize/compare/plot?" → Does this need a chart to see patterns?
   - Examples: trends over time, comparisons, distributions, breakdowns
   → Call graph_agent
   
   CONCRETE EXAMPLES (GRAPH INTENT):
   - "Show me sales for FY 2024-25" (needs visualization to compare)
   - "Visualize monthly profit trend" (needs chart to see pattern)
   - "Compare closing balance vs credit revenue" (needs graph for comparison)
   - "Plot inventory levels" (needs chart)
   - "show outstanding receivables per month" (needs pie/bar chart)
   - "show y stock items based on quantity" (needs bar chart)"

2. TABLE/DETAILED DATA INTENT: User wants SPECIFIC ITEMS or COMPLETE BREAKDOWN
   - Questions: "List/itemize/all items/breakdown?" → Does this need a detailed list?
   - Examples: all accounts, all transactions, line-by-line details
   → Call table_agent
   
   CONCRETE EXAMPLES (TABLE INTENT):
   - "List all customers" (needs complete item list)
   - "itemize all transactions for January" (needs detailed line-by-line data)
   - "breakdown the complete stock summary" (needs full breakdown table)
   - "list all the accounts in balance sheet?" (needs itemized list)
   - "list every purchase order" (needs detailed listing)

3. SUMMARY/ANALYSIS INTENT: User wants KEY METRICS, INSIGHTS, or INTERPRETATION
   - Questions: "What is/how much/analyze/explain?" → Does this need a summary or analysis?
   - Examples: total values, key figures, financial analysis, insights
   → Call summary_agent
   
   CONCRETE EXAMPLES (SUMMARY INTENT):
   - "What is my total revenue?" (needs key metric)
   - "How much profit did I make?" (needs single calculated value)
   - "Analyze my financial performance" (needs interpretation/analysis)
   - "What are the key findings from balance sheet?" (needs insights)
   - "Give me an overview of the business" (needs summary)
   - "What's the current inventory value?" (needs calculated summary)



DECISION PROCESS:
- Don't look for specific keywords
- Understand the USER'S TRUE OBJECTIVE
- Determine if they need 1 or multiple outputs
- If unclear, prioritize: SUMMARY first (safest choice)
- Execute exactly what user asked for, nothing extra

=================================================
STEP 4 — TOOL ROUTING
=================================================

=================================================
CATEGORY T — TABLE-ONLY REQUESTS → table_agent
=================================================
Triggered by STEP 3 intent classification showing TABLE intent.
Call table_agent and STOP after execution.

=================================================
CATEGORY A — GRAPH REQUESTS → graph_agent
=================================================
Triggered by STEP 3 intent classification showing GRAPH/VISUALIZATION intent.
Call graph_agent and STOP after execution.

=================================================
CATEGORY B — SUMMARY REQUESTS → summary_agent
=================================================
Triggered by STEP 3 intent classification showing SUMMARY/ANALYSIS intent.
Call summary_agent and STOP after execution.

INPUT FORMAT:
- Pass JSON with: {{"company": "...", "report": "...", "query": "<original user question>"}}
- The 'query' field enables query-aware summarization with targeted insights
- summary_agent will return both general summary AND query-specific analysis

=================================================
CATEGORY C — REPORT FETCH → report_agent
=================================================
Use ONLY for:
- "open balance sheet"
- "show stock summary"
- "fetch day book"
- "list companies"

Not for graphs or summaries.

=================================================
CATEGORY D — DASHBOARD TILES → dashboard_agent
=================================================
Use for dashboard visualization queries:

1. TREND TILES (Periodic Sales/Purchase Analysis):
   Keywords:
   - sales trend
   - purchase trend
   - monthly trend
   Examples:
   - "show me sales trend"
   - "give me purchase trend analysis"
   - "visualize sales trend"
   Rules:
   - Set tile_type = "trend"
   - Auto-detect voucher_type from query (Sales/Purchase)

2. TRADING TILE (Sales, Purchases, Profit Summary):
   Keywords:
   - trading details
   - trading tile
   Examples:
   - "show trading details"
   - "analyze trading performance"
   Rules:
   - Set tile_type = "trading"
   - Shows overall sales, purchases, and profit breakdown


All dashboard queries:
- Call dashboard_agent with company + tile_type
- dashboard_agent handles ERP API calls internally
- Auto-fill dates if not provided (defaults to last 90 days)

=================================================
CRITICAL RULES FOR MULTI-INTENT HANDLING
=================================================
1. DETECT ALL INTENTS FIRST:
   - Multiple intents (e.g., "graph AND table", "table AND summary")
   - Single intent (e.g., only graph, only summary)

2. FOR MULTIPLE INTENTS - SEQUENTIAL EXECUTION:
   - Graph + Table: First call table_agent, then call graph_agent
   - Table + Summary: First call table_agent, then call summary_agent
   - Graph + Summary: First call graph_agent, then call summary_agent
   - Table + Graph + Summary: Call in order → table, graph, summary

3. FOR SINGLE INTENT:
   - TABLE-ONLY → table_agent only
   - GRAPH-ONLY → graph_agent only
   - SUMMARY-ONLY → summary_agent only
   - FETCH REPORT → report_agent only

4. AFTER EACH TOOL CALL:
   - Analyze the result
   - Decide if another tool is needed
   - If yes → call next tool with same company/report
   - If no → proceed to Final Answer

5. STOPPING CONDITION:
   - Once you have ALL requested outputs
   - Merge results into a single response
   - Output Final Answer with ALL results
   - NEVER call a tool twice for the same request

=================================================
EXPLICIT STOPPING LOGIC (CRITICAL TO PREVENT LOOPS)
=================================================
SINGLE INTENT REQUESTS — STOP IMMEDIATELY AFTER FIRST TOOL:
- "visualize balance sheet" → Call graph_agent → STOP (output result)
- "show table for stock summary" → Call table_agent → STOP (output result)
- "what is my total assets" → Call summary_agent → STOP (output result)

MULTIPLE INTENT REQUESTS — STOP AFTER ALL TOOLS CALLED:
- "graph and table for balance sheet" → Call table_agent → Call graph_agent → STOP
- "give me summary and graph" → Call graph_agent → Call summary_agent → STOP

ABSOLUTE RULE: 
- Count how many tools the user requested
- Call exactly that many tools, no more, no less
- After the last tool result → Output Final Answer immediately
- DO NOT call the same tool twice
- DO NOT generate extra observations between tools

=================================================
NEVER call a tool twice for the same request

=================================================
CRITICAL ANTI-LOOP MECHANISM:
=================================================
MOST IMPORTANT RULE - READ THIS CAREFULLY:

If ANY tool returns a response containing an "error" key:
1. STOP IMMEDIATELY
2. DO NOT retry the tool
3. DO NOT call any other tool  
4. Output: Final Answer: <paste the tool's response JSON exactly>

This is not optional. This is REQUIRED to prevent infinite loops.

Examples:
- Tool returns: {{"error": "No data", "summary": {{...}}}}
  → Output EXACTLY: Final Answer: {{"error": "No data", "summary": {{...}}}}
  
- Tool returns: {{"error": "Connection failed"}}
  → Output EXACTLY: Final Answer: {{"error": "Connection failed"}}

When you see "error" in tool output → ALWAYS output Final Answer IMMEDIATELY.
Do not think. Do not reason. Just output Final Answer with the exact JSON.

=================================================
ACTION FORMAT (STRICT)
=================================================
Thought: <private reasoning — NEVER reveal>
Action: <tool_name>
Action Input: <string or JSON>

OR (when you have all results):

Final Answer: <RAW JSON OUTPUT FROM TOOLS - NO TEXT WRAPPER>

CRITICAL: Final Answer MUST be valid JSON that the backend can parse.
Examples of CORRECT Final Answer:
- {{"image_path": "generated_graphs/xyz.png", "summary": {{...}}}}
- {{"table": "...", "dataframe_id": "...", "summary": {{...}}}}
- {{"summary_text": "...", "stats": {{...}}}}

Examples of WRONG Final Answer:
- "The graph is located at generated_graphs/xyz.png"  ❌ TEXT NOT JSON
- "Here is your result: {{...}}"  ❌ TEXT WRAPPER AROUND JSON
- "Graph attached: image.png"  ❌ NOT STRUCTURED

WHEN TO OUTPUT FINAL ANSWER:
- After you have called all required tools
- Never before calling all tools
- Merge the results from all tool calls
- Include all outputs in the Final Answer as a single valid JSON object
- Do NOT wrap the JSON in text

NEVER reveal your Chain-of-Thought  
NEVER include observations between tools  

User Input:
{input}

{agent_scratchpad}
"""
)

# ------------------------------------------------------------
# Build supervisor
# ------------------------------------------------------------
react_supervisor = create_react_agent(
    llm=llm,
    tools=supervisor_tools,
    prompt=SUPERVISOR_PROMPT,
)

supervisor_agent = AgentExecutor(
    agent=react_supervisor,
    tools=supervisor_tools,
    verbose=True,
    handle_parsing_errors=True,
    return_intermediate_steps=True,
    max_iterations=8  # Allow up to 8 iterations for multi-intent (graph + table + summary = 3 tools)
)

# ------------------------------------------------------------
# ENTRY POINT (only keeps dict support)
# ------------------------------------------------------------
def run_supervisor(user_input):

    #  1. If structured JSON → remember company
    if isinstance(user_input, dict):
        # ⭐ HARDCODED COMPANY SUPPORT
        if HARDCODED_COMPANY:
            # If hardcoded company is set, always use it (overrides user input)
            user_input["company"] = HARDCODED_COMPANY
            logger.info(f"✅ Using HARDCODED_COMPANY: {HARDCODED_COMPANY}")
        
        # ⭐ OLD LOGIC (commented out for backward compatibility)
        # elif "company" in user_input and user_input["company"]:
        #     supervisor_state["last_company"] = user_input["company"]
        # 
        # #  2. If company missing → autofill from memory
        # elif supervisor_state.get("last_company"):
        #     user_input["company"] = supervisor_state["last_company"]
        
        # NEW: Vector DB-based report resolution
        user_input = resolve_with_vector_db(user_input)

        # Convert to JSON string AFTER resolution
        user_input = json.dumps(user_input)

    logger.info(f"🎬 Supervisor starting with input: {user_input}")
    
    response = supervisor_agent.invoke({"input": user_input})
    
    logger.info(f"📊 Agent response type: {type(response)}")
    logger.info(f"📊 Agent response keys: {response.keys() if isinstance(response, dict) else 'not a dict'}")
    
    output_text = response.get("output", "")
    intermediate_steps = response.get("intermediate_steps", [])
    
    logger.info(f"📊 Agent output: {str(output_text)[:500]}")
    logger.info(f"📊 Intermediate steps count: {len(intermediate_steps)}")
    
    # ✅ EXTRACT TOOL OUTPUTS FROM INTERMEDIATE STEPS
    # intermediate_steps is a list of (action, observation) tuples
    # action is an AgentAction, observation is the tool's output string
    if intermediate_steps:
        logger.info(f"🔍 Found {len(intermediate_steps)} intermediate steps")
        
        # Count tool calls by name
        tool_call_counts = {}
        for action, _ in intermediate_steps:
            tool_name = action.tool if hasattr(action, 'tool') else str(action).split('\n')[0]
            tool_call_counts[tool_name] = tool_call_counts.get(tool_name, 0) + 1
        
        #  CHECK FOR DUPLICATE TOOL CALLS (BUG FIX FOR DOUBLE GRAPH GENERATION)
        for tool_name, count in tool_call_counts.items():
            if count > 1:
                logger.warning(f" DUPLICATE TOOL CALL DETECTED: {tool_name} was called {count} times!")
        
        # Collect all tool outputs
        merged_result = {}
        for i, (action, observation) in enumerate(intermediate_steps):
            tool_name = action.tool if hasattr(action, 'tool') else str(action).split('\n')[0]
            
            # Try to parse observation as JSON
            try:
                if isinstance(observation, str):
                    tool_data = json.loads(observation)
                else:
                    tool_data = observation
                
                logger.debug(f"  [{i}] Tool: {tool_name} - keys: {list(tool_data.keys())}")
                # Merge all tool outputs
                merged_result.update(tool_data)
            except Exception as e:
                logger.warning(f"  [{i}] Failed to parse as JSON: {e}")
        
        # If we successfully collected tool outputs, return them
        if merged_result:
            logger.debug(f"Returning merged tool outputs with keys: {list(merged_result.keys())}")
            return merged_result
    
    #  ATTEMPT: Try to parse output as JSON if it looks like JSON
    if isinstance(output_text, str) and output_text.strip().startswith("{"):
        try:
            parsed = json.loads(output_text)
            logger.debug(f"Output is valid JSON")
            return parsed
        except Exception as e:
            logger.warning(f"Output looks like JSON but failed to parse: {e}")
    
    #  ATTEMPT: Extract structured data from tool-returned JSON within text
    import re
    json_matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', output_text)
    if json_matches:
        logger.debug(f"Found {len(json_matches)} JSON objects in output text")
        for i, json_str in enumerate(json_matches):
            try:
                parsed = json.loads(json_str)
                # Prefer JSON with priority keys
                if "image_path" in parsed or "table" in parsed or "summary_text" in parsed:
                    return parsed
            except Exception as e:
                logger.warning(f"Failed to parse JSON: {e}")
        
        # If we found JSON objects but none had priority keys, return first one
        if json_matches:
            try:
                parsed = json.loads(json_matches[0])
                return parsed
            except Exception:
                pass
    
    # ⚠️ FALLBACK: Return agent text output as-is
    logger.warning(f"Returning raw text output (not JSON)")
    return output_text