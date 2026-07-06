# ASCENSION LOG — Autonomous Multi-Agent Supervisor System
> 30 days. One project. Real impact.
> Built from scratch. Deployed on AWS. No shortcuts.
## The Goal
A production-grade LangGraph multi-agent system where a supervisor agent 
autonomously decomposes tasks and routes them to specialized workers — 
callable via API, deployed on AWS, battle-tested with real use cases.
## The Rule
Every session = a commit. Every day = an entry. 
No zero days.

## Day 1 - Gemini API Debugging [1 JULY]
- Set up `Learning/day1_llm_call.py` to call Gemini from Python.
- Learned that the correct import is `import google.genai as genai`, and the `google-genai` package must be installed in the active `.venv`.
- Verified `.env` loading from the script folder so the key is read from `Learning/.env`.
- Reached the API, but Google returned `401 UNAUTHENTICATED`, so the remaining issue is the credential type, not the Python syntax.
## Day 2 — July 2, 2026
**What I built:**
- Dynamic prompt templates using ChatPromptTemplate
- LangChain pipe operator (prompt | llm)
- Handled response.content edge cases for thinking models
- Switched to gemini-3.5-flash for faster responses

**What I learned:**
- ChatPromptTemplate structures prompts with variables
- The | operator chains components together
- .env path handling relative to file location

## Day 3 — July 3, 2026
> **Quote of the Day:** "Motivation, Pain, Failure is a temporary variable in life. Replace that with hard work it becomes a const variable assigned to Success."
> `const success = hardWork;` — no reassignment possible.
> *— Aashish Kumar Singh*

**What I built:**
- First LangGraph Agent using `create_react_agent`
- Created `@tool` decorated functions for math and mock APIs
- Attached tools to the LLM so it can execute them
- Streamed multi-step reasoning logs to the terminal

**What I learned:**
- Agents can reason about whether to call a tool or answer normally
- LangGraph is the modern framework for orchestrating LLM tool calling
- Tools require good docstrings because that's how the LLM knows when to use them
## Day 4 — July 4, 2026
**What I built:**
- Interactive calculator agent that runs until "calculation done"
- 4 arithmetic tools: add, subtract, multiply, divide
- Agent maintains conversation history across turns
- Handled Gemini rate limits (429 error) — switched models

**What I learned:**
- ReAct loop: Reason → Act → Observe → Reason again
- create_react_agent builds a 3-node graph internally (agent → tool → agent)
- Streaming loop yields each step as it happens
- Free tier limits: gemini-3.5-flash = 20 requests/day
- messages list grows with each turn = agent memory

**Tomorrow's plan:**
- Learn LangGraph state management
- Build first custom graph manually (no create_react_agent shortcut)

> **Quote of the Day:** "Today I didn't bring everything I had. The fire was low, the focus scattered, and I know it. But I showed up anyway — gym done, agent built, quests logged. Some days the grind isn't glorious. This was one of them. I'm writing this so future me remembers: even bad days got done. That's the standard. No zeros, no excuses — just forward."
> *— Aashish Kumar Singh*

## Day 5 — July 6, 2026
**What I built:**
- First custom state graph using LangGraph's `StateGraph`
- Manual workflow with `drafter` and `reviewer` nodes
- Defined a `TypedDict` to pass state (`topic`, `draft`, `review`) between nodes

**What I learned:**
- `StateGraph` requires a typed dictionary to define the state schema.
- Nodes are just Python functions that return a dict to update the state.
- Workflows must be compiled into a runnable application before invoking.

**Tomorrow's plan:**
- Build a Supervisor agent that routes tasks to different workers
- Combine multiple agents into a single graph

> **Quote of the Day:** "Small steps every day. The state graph is the foundation of complex reasoning loops."
> *— Aashish Kumar Singh*