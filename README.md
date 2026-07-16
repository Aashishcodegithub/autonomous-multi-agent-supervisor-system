# Autonomous Multi-Agent Supervisor System

A production-grade LangGraph multi-agent system where a supervisor agent autonomously decomposes tasks and routes them to specialized worker agents — built from scratch, deployed on AWS. No shortcuts.

## Current Status
🔨 **Day 15 / 30 Completed**

## Build Progress
See [ASCENSION_LOG(Devlog).md](./ASCENSION_LOG(Devlog).md) for daily build log.

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

## Tech Stack
- **Framework:** LangChain, LangGraph
- **LLM:** Google Gemini (gemini-2.5-flash / gemini-3.5-flash)
- **Cloud:** AWS (upcoming — Lambda, S3, DynamoDB)
- **Language:** Python 3.9+

## Project Structure
- `Learning/day1_llm_call.py` — first LLM call via LangChain
- `Learning/day2_prompt_template.py` — dynamic prompt templates
- `Learning/day3_tools_and_agents.py` — tool calling and react agents using LangGraph
- `Learning/day4_interative_agent.py` — interactive calculator agent
- `Learning/day5_manual_state_graph.py` — custom manual state graph with drafter and reviewer nodes
- `Learning/day6_supervisor_agent.py` — supervisor multi-agent graph
- `Learning/day7_persistent_memory.py` — supervisor agent with persistent thread memory
- `Learning/day8_supervisor_agent.py` — Human-in-the-Loop safety gating
- `Learning/day9_implementation_of_project_web_summarizer_agent.py` — web summarizer agent
- `Learning/day10_internet_research_summarizer_agent.py` — internet research agent
- `Learning/day11_error_handling.py` — error handling & resilience (TBD)
- `Learning/day12_unified_web_research_supervisor_agent.py` — unified web research supervisor
- `Learning/day13_unified_web_research_supervisor_agent.py` — unified research quality fix (prompt tuning)
- `draw_architecture.py` — Python script to render the architecture diagram
- `architecture.png` — rendered supervisor multi-agent architecture diagram
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
pip install langchain langchain-google-genai langgraph python-dotenv pydantic beautifulsoup4 requests wikipedia
```
3. Add Gemini API key to `Learning/.env`:
```env
GOOGLE_API_KEY=your_key_here
```

## Run
To run the Day 6 supervisor agent:
```bash
python Learning/day6_supervisor_agent.py
```

To run the Day 7 memory test:
```bash
python Learning/day7_persistent_memory.py
```

To run the Day 8 HITL supervisor test:
```bash
python Learning/day8_supervisor_agent.py
```

To run the Day 9 web summarizer agent:
```bash
python Learning/day9_implementation_of_project_web_summarizer_agent.py
```

To run the Day 10 internet research agent:
```bash
python Learning/day10_internet_research_summarizer_agent.py
```

To run the Day 12 unified web research supervisor:
```bash
python Learning/day12_unified_web_research_supervisor_agent.py
```

To run the Day 13 unified research quality fix supervisor:
```bash
python Learning/day13_unified_web_research_supervisor_agent.py
```

To run the Day 14 AWS Lambda handler locally (simulated API Gateway event):
```bash
python -c "from aws.lambda_handler import lambda_handler; import json; event={'body': json.dumps({'query': \"Research: Newton's first law of motion (What is it? main concepts?)\", 'thread_id': 'local-day14'})}; print(lambda_handler(event, None))"
```

## Notes
- `Learning/.env` is git-ignored — never committed
- LLM-agnostic design — can swap Gemini for Claude or GPT in one line
- Daily commits enforced — no zero days

