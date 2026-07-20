# Autonomous Multi-Agent Supervisor System

A production-grade LangGraph multi-agent system where a supervisor agent autonomously decomposes tasks and routes them to specialized worker agents — built from scratch, deployed on AWS. No shortcuts.

This project implements a complete agentic pipeline that takes natural language queries for financial reports or dashboard tiles, detects intent, routes to appropriate specialist agents, and generates data, graphs, and tables from ERP ERP.

---

## Table of Contents

1. [Current Status](#current-status)
2. [Architecture Overview](#architecture-overview)
3. [Build Progress](#build-progress)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Setup & Dependencies](#setup--dependencies)
7. [Running the Application](#running-the-application)
8. [Dashboard Integration](#dashboard-integration)
9. [Hardcoded Company Setup](#hardcoded-company-setup)

---

## Current Status
🔨 **Day 20 / 30 Completed** — Full production system live (ERP pipeline, agents, FAISS vector DB, FastAPI backend, Streamlit UI).

---

## Architecture Overview

The system is an agentic pipeline that:
1. Takes a user query (report or dashboard tile request)
2. Detects intent (report vs. dashboard, multi-intent vs single-intent) using FAISS semantic search and LLM routing
3. Routes to the appropriate specialist agent(s)
4. Generates data, graphs, and tables safely (via AST sandbox)
5. Returns a structured JSON response

### Query Flow

**For Dashboard Tiles:**
```text
User Query → intent_splitter.run_supervisor_multi_intent()
  ↓
detect_dashboard_intent(query) → tile_type found?
  ↓
YES → react_dashboard_agent({company, tile_type, query, ...})
  ↓
dashboard_agent.run_dashboard_agent()
  ↓
dashboard_tile_fetcher.fetch_and_parse_tile() → {summary, dataframe_dict, dataframe_id}
  ↓
graph_code_generator → matplotlib code
  ↓
graph_executor → PNG image
  ↓
table_agent → markdown table
  ↓
Return: {summary, dataframe_id, graph_code, image_path, table, tile_type}
```

**For Reports (Existing):**
```text
User Query → FAISS Vector DB Resolution (get_best_report)
  ↓
Supervisor Agent → Intent Classification (Graph / Table / Summary)
  ↓
Specialist Agent Execution (table_agent → graph_agent → summary_agent)
  ↓
Return: Merged structured JSON output
```

---

## Build Progress
See [ASCENSION_LOG(Devlog).md](./ASCENSION_LOG(Devlog).md) for the detailed daily build log.

| Day | What Was Built |
|-----|---------------|
| Day 1 | First LLM call via Gemini + LangChain |
| Day 2 | Dynamic prompt templates + LangChain pipe operator |
| Day 3 | Tools and Agents using LangGraph |
| Day 4 | Interactive calculator agent with conversation history |
| Day 5 | Custom manual state graph using LangGraph |
| Day 6 | Supervisor multi-agent graph with dynamic worker routing |
| Day 7 | Persistent conversational memory with thread checkpointer |
| Day 8 | Human-in-the-Loop (HITL) safety gating using breakpoints |
| Day 9 | Web summarizer agent (URL fetch + summarize) |
| Day 10 | Internet research agent (Wikipedia search + fetch + summarize) |
| Day 11 | Error handling & agent resilience patterns |
| Day 12 | Unified web research supervisor (URL summarize + wiki research) |
| Day 13 | Unified research quality fix (Newton’s 1st law + prompt tuning) |
| Day 14-15 | Basic RAG demo & AWS Lambda scaffolding |
| Day 17 | ERP Integration Layer (Tools & Data Pipeline) |
| Day 18 | AI Chart Generator + Sandboxed Executor |
| Day 19 | Specialist Agents (Report, Graph, Table, Summary, Dashboard) |
| Day 20 | Supervisor Agent + FastAPI + Streamlit Dashboard — Full System Live |

---

## Tech Stack
- **Framework:** LangChain, LangGraph
- **LLM:** Google Gemini (`gemini-2.5-flash` / `gemini-3.5-flash` / `gemini-2.0-flash-exp`)
- **Web/API:** FastAPI, Streamlit, Gradio
- **Vector DB:** FAISS (for semantic report resolution using `all-MiniLM-L6-v2`)
- **Data & Execution:** Pandas, Numpy, Matplotlib (sandboxed)
- **Language:** Python 3.9+

---

## Project Structure

```text
.
├── ASCENSION_LOG(Devlog).md     # Daily build log
├── Learning/                    # Initial learning prototypes (Days 1-15)
│   ├── day1_llm_call.py
│   ├── day6_supervisor_agent.py
│   └── ...
├── tools/                       # Core Production System
│   ├── agents/                  # Agent implementations
│   │   ├── dashboard_agent.py   # Dashboard tile pipeline agent
│   │   ├── graph_agent.py       # Graph generation agent
│   │   ├── report_agent.py      # Report generation agent
│   │   ├── summarization_agent.py 
│   │   └── table_agent.py       # Table formatting agent
│   ├── api/                     # FastAPI endpoints
│   │   ├── main.py              # API server
│   │   └── security.py          
│   ├── faiss_db/                # FAISS vector database files
│   ├── generated_graphs/        # Generated graph images (temp)
│   ├── supervisor/              
│   │   └── supervisor_agent.py  # Main supervisor routing logic
│   ├── erp/                   # ERP ERP integration layer
│   │   ├── client.py
│   │   ├── parser.py
│   │   └── xml_templates/       
│   ├── tools/                   # LangChain tools
│   │   ├── company_list_tool.py
│   │   ├── dashboard_tile_fetcher.py
│   │   ├── data_conversion_tool.py
│   │   ├── get_report_tool.py
│   │   ├── graph_code_generator_tool.py
│   │   ├── graph_executor_tool.py
│   │   ├── react_wrappers.py
│   │   ├── summarization_tool.py
│   │   └── table_tool.py
│   ├── ui/                      # UI applications
│   │   ├── gradio_app.py
│   │   └── new_dashboard.py     # Streamlit chat interface
│   ├── gemini_wrapper.py        # Gemini API wrapper
│   ├── report_config.py         # Report configuration
│   ├── report_lookup.py         # Report lookup utilities
│   ├── vector_store.py          # Vector store setup for semantic matching
│   └── requirements.txt         # Core dependencies
```

---

## Setup & Dependencies

1. **Create virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. **Install dependencies:**
The project dependencies are listed in `tools/requirements.txt` with pinned versions for reproducibility.
```bash
cd tools
pip install -r requirements.txt
```

3. **Environment Setup:**
Create a `.env` file in the `tools` directory (or root) with:
```env
GOOGLE_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
# Optional: Set this to bypass company selection entirely
# HARDCODED_COMPANY=Modi Chemplast Materials Pvt Ltd
```

---

## Running the Application

### 1. Start the FastAPI Backend
```bash
cd tools
uvicorn api.main:app --reload --port 8000
```

### 2. Start the Streamlit Dashboard
In a new terminal window:
```bash
cd tools
streamlit run ui/new_dashboard.py
```

### Running Learning Modules (Days 1-13)
To run the earlier architectural learning builds:
```bash
python Learning/day6_supervisor_agent.py
python Learning/day7_persistent_memory.py
python Learning/day8_supervisor_agent.py
```

---

## Dashboard Integration

Dashboard tile integration with the existing Agentic pipeline handles both **report queries** (existing) and **dashboard tile queries** (new) through intelligent intent detection and routing.

### Tile Types
| Tile Type | Query Examples | Output | Chart |
|-----------|---------------|--------|-------|
| **trend** | "sales trend", "purchase trend by month", "monthly sales" | Monthly periods → Amounts | Line/Bar chart |
| **trading** | "profit and loss", "p&l", "trading dashboard" | {name: amount} (P&L components) | Breakdown visualization |
| **cashflow** | "cashflow", "cash position", "inflow outflow" | Cash-related metrics | Trend or waterfall |
| **assets** | "assets", "liabilities", "balance sheet" | Asset/Liability values | Stacked bar or comparison |

### Key Design Decisions
1. **Separation of Concerns**: Dashboard pipeline separate from report pipeline
2. **Reuse Existing Code**: Leverages existing `graph_code_generator` and `graph_executor`
3. **Keyword-Based Routing**: Simple, fast detection without LLM overhead
4. **Auto-Fill Dates**: Sensible defaults (90 days back)
5. **Backward Compatible**: Existing report queries unaffected

---

## Hardcoded Company Setup

The pipeline supports hardcoding a company name so that different pipelines can be displayed side-by-side on a frontend without requiring company selection in each request.

### Usage

**Method 1: Environment Variable (Recommended)**
Add to your `.env` file:
```env
HARDCODED_COMPANY=Modi Chemplast Materials Pvt Ltd
```

**Method 2: Direct Code Configuration**
Edit `tools/supervisor/supervisor_agent.py` and set:
```python
HARDCODED_COMPANY = "Modi Chemplast Materials Pvt Ltd"
```

### Frontend Integration Use Case
If you have 3 different pipelines from 3 different organizations:
- **Pipeline 1 (.env):** `HARDCODED_COMPANY=Company A`
- **Pipeline 2 (.env):** `HARDCODED_COMPANY=Company B`

Each pipeline can now receive identical request payloads without company names, and each will process for their respective company automatically.

To revert to dynamic company selection, ensure `HARDCODED_COMPANY = None` in the `.env` or code.

---
*LLM-agnostic design — Daily commits enforced — No zero days*
