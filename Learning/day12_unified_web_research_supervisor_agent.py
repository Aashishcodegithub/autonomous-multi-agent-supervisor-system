# Day 12: Unified Web Research Supervisor (Web Summarize + Internet Research)
# Goal: Unify Day 9 (URL fetch + summarize) and Day 10 (Wikipedia search + fetch + research notes)
# into a single LangGraph supervisor with specialized workers.

from __future__ import annotations

from typing import TypedDict, Annotated, Sequence, Literal
import time
from pathlib import Path
import re

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


load_dotenv(dotenv_path=Path(__file__).with_name(".env"))


class RateLimitedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    """Simple rate-limit / retry wrapper for local development."""

    def invoke(self, *args, **kwargs):
        # small delay to reduce bursty traffic
        time.sleep(2)
        for attempt in range(4):
            try:
                return super().invoke(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    wait_time = 15 + (attempt * 10)
                    print(f"\n⚠️  [LLM Rate Limit] Waiting {wait_time}s before retrying...")
                    time.sleep(wait_time)
                    continue
                raise
        return super().invoke(*args, **kwargs)


llm = RateLimitedChatGoogleGenerativeAI(model="gemini-2.5-flash")


# ----------------------------
# Tools (reused from Day 9 / Day 10 concepts)
# ----------------------------
@tool
def fetch_url_text(url: str, max_chars: int = 12000) -> str:
    """Fetch a URL and return cleaned, readable text.

    Use this when you need to summarize web content from a URL.

    Args:
        url: The URL to fetch.
        max_chars: Maximum characters of extracted text to return.

    Returns:
        Cleaned plain text extracted from the HTML.
    """
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

    # Remove noisy elements
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text("\n")

    # Normalize whitespace
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    cleaned = "\n".join(lines)

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars] + "\n\n[TRUNCATED]"

    return cleaned or "[NO TEXT EXTRACTED]"


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


# ----------------------------
# Graph schemas
# ----------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str


class RouteResponse(BaseModel):
    next: Literal["web_worker", "research_worker", "writer_worker", "FINISH"] = Field(
        description="Next worker to run."
    )
    reasoning: str = Field(description="Why this route was chosen.")


structured_llm = llm.with_structured_output(RouteResponse)


# ----------------------------
# Helpers
# ----------------------------
_URL_REGEX = re.compile(r"https?://\S+")


def user_contains_url(user_text: str) -> bool:
    return bool(_URL_REGEX.search(user_text.strip()))


def normalize_research_query(user_text: str) -> str:
    # Easy compatibility with Day 10: "Research: <topic> ..."
    lowered = user_text.strip()
    lowered = lowered.replace("Research:", "").strip()
    return lowered


# ----------------------------
# Nodes
# ----------------------------
def supervisor_node(state: AgentState):
    print("\n🕵️  [Supervisor] Deciding next action...")

    last_user = state["messages"][-1].content or ""

    system_prompt = (
        "You are a supervisor agent orchestrating workers:\n"
        "1) web_worker: fetches and summarizes content from a specific URL.\n"
        "2) research_worker: performs lightweight internet research (Wikipedia search + fetches) and prepares research notes.\n"
        "3) writer_worker: writes the final consolidated user-facing response.\n\n"
        "Routing rules:\n"
        "- If the user provides a URL or clearly asks to summarize web content from a URL => web_worker.\n"
        "- If the user asks for internet research / topic research (and no clear URL is provided) => research_worker.\n"
        "- If the request is already fully answered => FINISH.\n"
        "Always end up at writer_worker after worker steps.\n"
    )

    decision = structured_llm.invoke([SystemMessage(content=system_prompt)] + list(state["messages"]))
    # Small safety: if the model chooses FINISH too early, force writer_worker
    if decision.next == "FINISH":
        # if we don't have worker outputs yet, writer_worker should still run
        # (the writer will use the entire conversation history)
        decision.next = "writer_worker"
        decision.reasoning += " (forced writer_worker to generate final output)"

    print(f"🕵️  [Supervisor Decision] Next: {decision.next} | Reasoning: {decision.reasoning}")
    return {"next": decision.next}


def web_worker_node(state: AgentState):
    print("🌐 [Web Worker] Fetching & summarizing...")

    last_user = state["messages"][-1].content or ""

    urls = _URL_REGEX.findall(last_user)
    target_url = urls[0] if urls else None

    if not target_url:
        # If no URL was detected, ask for one via writer path.
        note = "No URL detected in the user's message. Please provide a URL to summarize."
        return {
            "messages": [AIMessage(content=f"[Web Worker Output]\n{note}")],
            "next": "writer_worker",
        }

    extracted = fetch_url_text.invoke({"url": target_url, "max_chars": 12000})

    summarize_prompt = (
        "You are a web summarizer.\n"
        "Summarize the extracted web text clearly.\n"
        "Rules:\n"
        "- Use only information from the extracted text.\n"
        "- Provide 5 key points.\n"
        "- If the extracted text is [NO TEXT EXTRACTED], say so.\n\n"
        f"USER REQUEST: {last_user}\n"
        f"URL: {target_url}\n\n"
        f"EXTRACTED TEXT:\n{extracted}"
    )

    summary = llm.invoke([SystemMessage(content="Write clear summaries."), HumanMessage(content=summarize_prompt)])
    return {
        "messages": [AIMessage(content=f"[Web Worker Output]\n{summary.content}")],
        "next": "writer_worker",
    }


def research_worker_node(state: AgentState):
    print("🧭 [Research Worker] Searching, fetching, and preparing notes...")

    last_user = state["messages"][-1].content or ""
    query = normalize_research_query(last_user)

    # 1) Search top pages
    search_results = wiki_search.invoke({"query": query, "top_k": 3})

    # 2) Fetch each page
    fetched: list[dict] = []
    for r in search_results:
        page_text = fetch_url_text.invoke({"url": r["url"], "max_chars": 6000})
        fetched.append({"title": r["title"], "url": r["url"], "text": page_text})

    # 3) Make notes (so writer can synthesize reliably)
    context_parts: list[str] = []
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
        f"USER QUESTION: {last_user}\n\n"
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
    print("✍️  [Writer Worker] Producing final answer...")

    history = "\n".join([f"{type(m).__name__}: {getattr(m, 'content', '')}" for m in state["messages"]])

    prompt = (
        "You are a helpful assistant.\n"
        "Using the worker outputs below, produce the final user-facing response.\n\n"
        "Constraints:\n"
        "- Do not invent facts not supported by the extracted/fetched text.\n"
        "- If worker outputs contain no usable extracted content, say so clearly.\n"
        "- Include 5 key points.\n"
        "- If research sources are present, add a short 'Sources' section with URLs.\n\n"
        f"WORKFLOW HISTORY:\n{history}"
    )

    response = llm.invoke([SystemMessage(content="Write clearly and concisely."), HumanMessage(content=prompt)])

    return {"messages": [AIMessage(content=response.content)], "next": "FINISH"}


# ----------------------------
# Build graph
# ----------------------------
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("web_worker", web_worker_node)
workflow.add_node("research_worker", research_worker_node)
workflow.add_node("writer_worker", writer_worker_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],
    {
        "web_worker": "web_worker",
        "research_worker": "research_worker",
        "writer_worker": "writer_worker",
        "FINISH": END,
    },
)

workflow.add_edge("web_worker", "writer_worker")
workflow.add_edge("research_worker", "writer_worker")
workflow.add_edge("writer_worker", END)

checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)


# ----------------------------
# Demo
# ----------------------------
if __name__ == "__main__":
    # Example queries:
    # 1) URL summarization:
    # query = "Summarize https://www.wikipedia.org in 5 key points."
    # 2) Internet research:
    query = "Research: First Law of Motion (What is it? main concepts?)"

    config = {"configurable": {"thread_id": "day12-unified-web-research"}}
    print(f"🚀 User: {query}")

    final = app.invoke({"messages": [HumanMessage(content=query)], "next": "supervisor"}, config)

    print("\n--- FINAL ANSWER ---")
    for msg in final["messages"]:
        if isinstance(msg, AIMessage):
            print(msg.content)
