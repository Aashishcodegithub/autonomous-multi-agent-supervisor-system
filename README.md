# Autonomous Multi-Agent Supervisor System

A production-grade LangGraph multi-agent system where a supervisor agent 
autonomously decomposes tasks and routes them to specialized worker agents — 
built from scratch, deployed on AWS. No shortcuts.

## Current Status
🔨 **In Progress — Day 3/30**

## Build Progress
See [ASCENSION_LOG(Devlog).md](./ASCENSION_LOG(Devlog).md) for daily build log.

| Day | What Was Built |
|-----|---------------|
| Day 1 | First LLM call via Gemini + LangChain |
| Day 2 | Dynamic prompt templates + LangChain pipe operator |
| Day 3 | Tools and Agents using LangGraph |

## Tech Stack
- **Framework:** LangChain, LangGraph
- **LLM:** Google Gemini (gemini-3.5-flash)
- **Cloud:** AWS (upcoming — Lambda, S3, DynamoDB)
- **Language:** Python 3.9+

## Project Structure
- `Learning/day1_llm_call.py` — first LLM call via LangChain
- `Learning/day2_prompt_template.py` — dynamic prompt templates
- `Learning/day3_tools_and_agents.py` — tool calling and react agents using LangGraph
- `ASCENSION_LOG(Devlog).md` — daily build log
- `Learning/.env` — local API key (not committed)

## Setup
1. Create virtual environment:
```bash
   python3 -m venv .venv
   source .venv/bin/activate
```
2. Install dependencies:
```bash
   pip install langchain langchain-google-genai langgraph python-dotenv
```
3. Add Gemini API key to `Learning/.env`:
```env
   GOOGLE_API_KEY=your_key_here
```

## Run
```bash
python Learning/day3_tools_and_agents.py
```

## Notes
- `Learning/.env` is git-ignored — never committed
- LLM-agnostic design — can swap Gemini for Claude or GPT in one line

## Build Progress
See [ASCENSION_LOG(Devlog).md](./ASCENSION_LOG(Devlog).md) for daily build log.

## Current Status
🔨 **In Progress — Day 3/30**

### What's been built so far:
- Day 1: First LLM call via Gemini + LangChain
- Day 2: Dynamic prompt templates + LangChain pipe operator
- Day 3: Tools and React Agents using LangGraph