# Day 10: Internet research (easy version)
# Goal: Search the web (simple approach), fetch multiple pages, then summarize.
#
# INPUT:
#   - user asks for a topic
# OUTPUT:
#   - consolidated summary + key points
#
# Notes:
# - This is intentionally “easy-to-read” code.
# - It uses Wikipedia as a lightweight “searchable” source.
# - If you want true web search later (Tavily/SerpAPI), we can swap the search tool.

from __future__ import annotations

from typing import TypedDict, Annotated, Sequence, Literal
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

import requests
from bs4 import BeautifulSoup


load_dotenv(dotenv_path=Path(__file__).with_name('.env'))


class RateLimitedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    def invoke(self, *args, **kwargs):
        # Simple retry/backoff to handle 429 / rate limits in dev.
        time.sleep(2)
        for attempt in range(4):
            try:
                return super().invoke(*args, **kwargs)
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err:
                    wait_time = 20 + attempt * 15
                    print(f"\n⚠️  [LLM Rate limit] Waiting {wait_time}s (attempt {attempt+1}/4)...")
                    time.sleep(wait_time)
                    continue
                raise
        return super().invoke(*args, **kwargs)



llm = RateLimitedChatGoogleGenerativeAI(model="gemini-2.5-flash")


# ----------------------------
# Tools
# ----------------------------
@tool
def wiki_search(query: str, top_k: int = 3) -> list[dict]:
    """Search Wikipedia for a query and return top results.

    Returns a list of dicts with keys: title, url, snippet.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "srlimit": top_k,
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
    }
    r = requests.get(url, params=params, headers=headers, timeout=20)
    # Wikipedia may return 403 without a UA/header (or rate-limit); surface a readable error.
    r.raise_for_status()
    data = r.json()


    results: list[dict] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title")
        page_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        results.append(
            {
                "title": title,
                "url": page_url,
                "snippet": item.get("snippet", ""),
            }
        )
    return results


@tool
def fetch_url_text(url: str, max_chars: int = 12000) -> str:
    """Fetch URL and extract readable plain text (best-effort)."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n\n[TRUNCATED]"

    return cleaned or "[NO TEXT EXTRACTED]"


# ----------------------------
# Graph state + routing
# ----------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str


class RouteResponse(BaseModel):
    next: Literal["research_worker", "writer_worker", "FINISH"] = Field(
        description="Which worker to run next."
    )
    reasoning: str


structured_llm = llm.with_structured_output(RouteResponse)


# ----------------------------
# Nodes
# ----------------------------
def supervisor_node(state: AgentState):
    system_prompt = (
        "You are a supervisor. Workers:\n"
        "1) research_worker: searches the internet (Wikipedia in this easy version), "
        "fetches multiple pages, and prepares notes.\n"
        "2) writer_worker: writes a final consolidated summary.\n\n"
        "If the user asked for internet research, choose research_worker first. "
        "Otherwise choose writer_worker."
    )
    decision = structured_llm.invoke(
        [SystemMessage(content=system_prompt)] + list(state["messages"])
    )
    return {"next": decision.next}


def research_worker_node(state: AgentState):
    user_msg = state["messages"][-1].content

    # Easy version: turn “Research: <topic>” into just “<topic>”
    query = user_msg.replace("Research:", "").strip()

    # 1) Search top pages
    search_results = wiki_search.invoke({"query": query, "top_k": 3})

    # 2) Fetch each page
    fetched: list[dict] = []
    for r in search_results:
        page_text = fetch_url_text.invoke(
            {"url": r["url"], "max_chars": 6000}
        )
        fetched.append({"title": r["title"], "url": r["url"], "text": page_text})

    # 3) Make notes (so writer can be simpler)
    context_parts = []
    for i, item in enumerate(fetched, start=1):
        context_parts.append(
            f"SOURCE {i}: {item['title']} ({item['url']})\n\n{item['text']}"
        )

    notes_prompt = (
        "You are collecting notes for a final answer.\n"
        "Based on these sources, extract:\n"
        "(1) main points\n"
        "(2) 5 key facts\n"
        "(3) any dates/definitions if present\n\n"
        "Return in this format:\n"
        "- Main points: ...\n"
        "- Key facts (5): ...\n"
        "- Notes: ...\n\n"
        f"USER QUESTION: {user_msg}\n\n"
        + "\n\n".join(context_parts)
    )

    notes = llm.invoke([HumanMessage(content=notes_prompt)])

    return {
        "messages": [
            AIMessage(
                content=(
                    "[Research Notes]\n"
                    + getattr(notes, "content", str(notes))
                    + "\n\n[Source URLs]\n"
                    + "\n".join([x["url"] for x in fetched])
                )
            )
        ],
        "next": "writer_worker",
    }


def writer_worker_node(state: AgentState):
    history = "\n".join([f"{type(m).__name__}: {m.content}" for m in state["messages"]])
    prompt = (
        "You are a helpful assistant.\n"
        "Using the research notes below, write a concise final answer.\n"
        "Constraints:\n"
        "- Do not invent facts not supported by the sources.\n"
        "- Include 5 key points.\n"
        "- Add a short 'Sources' section with the URLs.\n\n"
        f"RESEARCH HISTORY:\n{history}"
    )

    response = llm.invoke([SystemMessage(content="Write clearly."), HumanMessage(content=prompt)])
    return {"messages": [AIMessage(content=response.content)], "next": "FINISH"}


# ----------------------------
# Build graph
# ----------------------------
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("research_worker", research_worker_node)
workflow.add_node("writer_worker", writer_worker_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],
    {
        "research_worker": "research_worker",
        "writer_worker": "writer_worker",
        "FINISH": END,
    },
)
workflow.add_edge("research_worker", "writer_worker")
workflow.add_edge("writer_worker", END)

app = workflow.compile(checkpointer=MemorySaver())


# ----------------------------
# Demo
# ----------------------------
if __name__ == "__main__":
    # Change this topic as you want.
    query = "Research: ronnie coleman bodybuilder (What is it? main concepts?)"

    config = {"configurable": {"thread_id": "day10-internet-research"}}
    print(f"🚀 User: {query}")

    final = app.invoke(
        {"messages": [HumanMessage(content=query)], "next": "supervisor"},
        config,
    )

    print("\n--- FINAL ANSWER ---")
    for msg in final["messages"]:
        if isinstance(msg, AIMessage):
            print(msg.content)
