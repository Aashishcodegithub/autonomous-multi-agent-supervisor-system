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

**Tomorrow's plan:**
- Tools — give the LLM the ability to actually DO something
