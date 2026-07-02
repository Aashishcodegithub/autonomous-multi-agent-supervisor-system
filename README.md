# Autonomous Multi-Agent Supervisor System

A learning project for building a multi-agent system where a supervisor coordinates specialized workers.

## Current Scope
- Day 1 learning notes
- Basic Gemini LLM call from Python
- Environment-based API key loading

## Project Structure
- `Learning/day1_llm_call.py` - simple Gemini API call
- `Learning/.env` - local API key file, not committed to Git
- `ASCENSION_LOG(Devlog).md` - session log

## Setup
1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install python-dotenv google-genai
   ```
3. Add your Gemini API key to `Learning/.env`:
   ```env
   GOOGLE_API_KEY=your_key_here
   ```

## Run
```bash
python Learning/day1_llm_call.py
```

## Notes
- `Learning/.env` is ignored by Git.
- The script loads `.env` from the `Learning` folder, so it can run from the repo root.
