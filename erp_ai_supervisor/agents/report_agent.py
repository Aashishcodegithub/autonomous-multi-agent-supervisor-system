# agents/report_agent.py
from dotenv import load_dotenv
import os
import json

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool

from gemini_wrapper import GeminiLLM

from tools.company_list_tool import get_company_list
from tools.get_report_tool import get_report
from tools.data_conversion_tool import data_conversion_tool

load_dotenv()

# ============================================================
# REPORT PROCESSOR - Manages state between tool calls
# ============================================================
class ReportProcessor:
    def __init__(self):
        self.last_report_name = None
        self.last_report_dict = None
    
    def get_companies(self, _):
        """Fetch list of companies"""
        return get_company_list.func()
    
    def fetch_report(self, json_str: str):
        """Fetch report and track the report name"""
        try:
            data = json.loads(json_str)
        except Exception:
            return 'Invalid JSON. Expected {"company":"ABC", "report":"Stock Summary"}'
        
        company = data.get("company")
        report = data.get("report")
        
        if not company:
            return "Missing required field: company"
        if not report:
            return "Missing required field: report"
        
        # Store report name for use by conversion tool
        self.last_report_name = report
        
        # Fetch and store the report
        report_dict = get_report.func(company, report)
        self.last_report_dict = report_dict
        
        print(f"DEBUG: Stored report_name='{self.last_report_name}'")
        return json.dumps(report_dict)
    
    def convert_report(self, json_str: str):
        """Convert report using stored report name"""
        try:
            data = json.loads(json_str)
        except Exception:
            return 'Invalid JSON'
        
        report_dict = data.get("report_dict", data)
        if not report_dict:
            return "Missing report data"
        
        # Use the stored report name
        report_name = self.last_report_name or ""
        print(f"DEBUG: convert_report using report_name='{report_name}'")
        
        # Call data_conversion_tool with report_name
        output = data_conversion_tool.func(report_dict, report_name)
        return json.dumps(output)


# Create global processor instance
processor = ReportProcessor()

# LLM
# ============================================================
llm = GeminiLLM(
    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
    temperature=0.0,
)

# TOOLS - Use processor methods
# ============================================================
report_tools = [
    Tool(
        name="get_company_list",
        func=processor.get_companies,
        description="Return list of companies. Input must be an empty string."
    ),
    Tool(
        name="get_report",
        func=processor.fetch_report,
        description='Fetch a ERP report. Input must be a JSON string: {"company":"ABC", "report":"Stock Summary"}.'
    ),
    Tool(
        name="data_conversion_tool",
        func=processor.convert_report,
        description='Convert a Dict report into a DataFrame summary. Input must be JSON: {"report_dict": {...}}.'
    ),
]

# ------------------------------------------------------------
# CUSTOM REACT PROMPT — FIXED TO ESCAPE JSON BRACES
# ------------------------------------------------------------
REPORT_AGENT_PROMPT = PromptTemplate(
    input_variables=["input", "agent_scratchpad", "tools", "tool_names"],
    template="""
You are a strict ReAct agent for ERP ERP.

AVAILABLE TOOLS:
{tools}

TOOL NAMES:
{tool_names}

=======================
RULES:
=======================
1. ALWAYS use ReAct format for tool calls:
   Thought:
   Action: <tool_name>
   Action Input: <valid JSON>

2. If required info is missing:
   - Missing company → Final Answer: Which company?
   - Missing report → Final Answer: Which report?

3. VALID TOOL INPUTS:
   - get_company_list → ""
   - get_report → {{ {{ "company": "ABC", "report": "Stock Summary" }} }}
   - data_conversion_tool → {{ {{ "report_dict": {{ ... }} }} }}

4. WHEN YOU ARE DONE USING TOOLS:
   Use:
   Final Answer: <your answer>

5. NEVER invent company names or report names.

=======================
User Query:
{input}

{agent_scratchpad}
"""
)

# ------------------------------------------------------------
# BUILD REACT AGENT
# ------------------------------------------------------------
react_agent = create_react_agent(
    llm=llm,
    tools=report_tools,
    prompt=REPORT_AGENT_PROMPT,
)

report_agent = AgentExecutor(
    agent=react_agent,
    tools=report_tools,
    verbose=True,
    handle_parsing_errors=True,
)

# ------------------------------------------------------------
# ENTRYPOINT FOR SUPERVISOR
# ------------------------------------------------------------
def run_report_agent(user_input: str):
    """Called by supervisor. user_input is ALWAYS a plain string."""
    response = report_agent.invoke({"input": user_input})
    return response["output"]
