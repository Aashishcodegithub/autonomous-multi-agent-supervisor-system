# AWS / Lambda (Day 14)

This folder contains the minimum scaffolding needed to run the **Day 13 unified research LangGraph workflow** on **AWS Lambda**.

## What you get
- `lambda_handler.py`: API-Gateway compatible handler that accepts `{ "query": "...", "thread_id": "..." }`.
- Uses the Day 13 workflow code to produce `{ "answer": "...", "thread_id": "..." }`.

## Environment variables
Set these for Lambda (or local simulation):

- `GOOGLE_API_KEY` — Gemini API key
- `LLM_MODEL` (optional, default: `gemini-2.5-flash`)
- `THREAD_ID_DEFAULT` (optional, default: `day14-lambda`)

## Local test (simulated API Gateway event)
From repo root:

```bash
python -c "from aws.lambda_handler import lambda_handler; import json; \
event={'body': json.dumps({'query': 'Research: Newton\'s first law of motion (What is it? main concepts?)', 'thread_id': 'local-day14'})}; \
print(lambda_handler(event, None))"
```

## Deploy notes (high-level)
1. Package with dependencies (requirements recommended to be centralized later).
2. Configure Lambda memory/timeout based on network calls.
   - Start with **512MB / 60s timeout** for dev.
3. Set `GOOGLE_API_KEY` and `LLM_MODEL` in Lambda environment.

## Next steps (recommended)
- Add a real persistence backend (DynamoDB checkpointer) to replace `MemorySaver`.
- Add structured logging + correlation ids.
- Add retry/backoff for HTTP + LLM throttling at the boundary.

