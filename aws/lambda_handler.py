"""AWS Lambda handler (Day 14)

API Gateway payload contract (JSON):
{
  "query": "...",
  "thread_id": "optional"
}

Response contract:
{
  "answer": "...",
  "thread_id": "..."
}

This handler uses the existing Day 13 LangGraph workflow as the core engine.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage


def _load_graph_app():
    # Import inside function so Lambda cold-start can be optimized later.
    # Day 13 script builds and compiles the graph at import-time and exposes `app`.
    from Learning.day13_unified_web_research_supervisor_agent import app

    return app


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")

    if body is None:
        return {}

    if isinstance(body, str):
        return json.loads(body)

    # API Gateway sometimes provides parsed body already
    if isinstance(body, dict):
        return body

    raise ValueError("Unsupported event.body type")


def _make_response(status_code: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload),
    }


def lambda_handler(event: Dict[str, Any], context: Optional[Any] = None) -> Dict[str, Any]:
    try:
        data = _parse_body(event)
        query = (data.get("query") or "").strip()
        if not query:
            return _make_response(400, {"error": "Missing required field: query"})

        thread_id = (data.get("thread_id") or os.getenv("THREAD_ID_DEFAULT") or "day14-lambda").strip()

        # Optional: allow overriding model via env var without changing Day 13 code.
        # (Day 13 currently hardcodes model='gemini-2.5-flash'. A follow-up refactor can wire this through.)
        _ = os.getenv("LLM_MODEL")

        app = _load_graph_app()

        # Use Day 13 graph state schema: {messages: [...], next: "supervisor"}
        final = app.invoke(
            {"messages": [HumanMessage(content=query)], "next": "supervisor"},
            {"configurable": {"thread_id": thread_id}},
        )

        answer = ""
        for msg in final.get("messages", []):
            # Day 13 uses AIMessage as final output
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content.strip():
                answer = content

        if not answer:
            answer = "[No answer generated]"

        return _make_response(200, {"answer": answer, "thread_id": thread_id})

    except Exception as e:
        return _make_response(500, {"error": str(e)})

