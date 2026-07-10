# Day 9: Multimodal (Agent) - Web Fetch + Summarize (text-first)
# Goal: Implement a worker that can fetch text from a URL and summarize it.
# Note: This is a production-style LangGraph supervisor/workers build that you can
# later extend to multimodal inputs (images) and richer extraction.

from __future__ import annotations

from typing import TypedDict, Annotated, Sequence, Literal, Optional
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

import requests
from bs4 import BeautifulSoup


load_dotenv(dotenv_path=Path(__file__).with_name('.env'))


class RateLimitedChatGoogleGenerativeAI(ChatGoogleGenerativeAI):
    """Simple rate-limit / retry wrapper for local development."""

    def invoke(self, *args, **kwargs):
        # small delay to reduce bursty traffic
        time.sleep(4)
        for attempt in range(4):
            try:
                return super().invoke(*args, **kwargs)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg:
                    wait_time = 15 + (attempt * 10)
                    print(f"\n⚠️  [LLM Rate Limit] Waiting {wait_time}s before retrying...")
                    time.sleep(wait_time)
                else:
                    raise
        return super().invoke(*args, **kwargs)


llm = RateLimitedChatGoogleGenerativeAI(model="gemini-2.5-flash")


# ----------------------------
# Tools
# ----------------------------
@tool
def fetch_url_text(url: str, max_chars: int = 12000) -> str:
    """Fetch a URL and return cleaned, readable text.

    Use this when the user provides a URL and you need to summarize its content.

    Args:
        url: www.Linkdin.com.
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


# NOTE: create_react_agent import path may vary by langgraph/langchain versions
web_agent = create_react_agent(llm, [fetch_url_text])


# ----------------------------
# Graph schemas
# ----------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str


class RouteResponse(BaseModel):
    next: Literal["web_worker", "writer_worker", "FINISH"] = Field(
        description="Next agent to act"
    )
    reasoning: str = Field(description="Why this route was chosen")


structured_llm = llm.with_structured_output(RouteResponse)


# ----------------------------
# Nodes
# ----------------------------

def supervisor_node(state: AgentState):
    print("\n🕵️  [Supervisor] Deciding next action...")
    system_prompt = (
        "You are a supervisor agent orchestrating workers.\n"
        "Workers:\n"
        "1) web_worker: fetches URL content and prepares a summary.\n"
        "2) writer_worker: finalizes/rewrites the answer for the user.\n\n"
        "Routing rules:\n"
        "- If the user provides a URL or clearly asks to summarize web content, choose web_worker.\n"
        "- Otherwise, choose writer_worker to write directly.\n"
        "- Choose FINISH if the user request is already fully answered."
    )

    decision = structured_llm.invoke([SystemMessage(content=system_prompt)] + list(state["messages"]))
    print(f"🕵️  [Supervisor Decision] Next: {decision.next} | Reasoning: {decision.reasoning}")
    return {"next": decision.next}


def web_worker_node(state: AgentState):
    print("🌐 [Web Worker] Fetching & summarizing...")

    last_user = state["messages"][-1].content
    prompt = (
        "You are a web summarizer.\n"
        "If the user message contains a URL, call the fetch_url_text tool to retrieve content, "
        "then summarize it clearly.\n"
        "If no URL is present, ask for one.\n\n"
        f"User request: {last_user}"
    )

    result = web_agent.invoke({"messages": [HumanMessage(content=prompt)]})
    # The ReAct agent returns a state-like output; extract final assistant text
    # Commonly result is dict with 'messages'
    final_msg = result["messages"][-1]
    if isinstance(final_msg, AIMessage):
        content = final_msg.content
    else:
        content = str(getattr(final_msg, "content", final_msg))

    return {"messages": [AIMessage(content=f"[Web Worker Output]\n{content}")], "next": "writer_worker"}


def writer_worker_node(state: AgentState):
    print("✍️  [Writer Worker] Producing final answer...")

    history = "\n".join([f"{type(m).__name__}: {m.content}" for m in state["messages"]])
    prompt = (
        "You are a helpful assistant. Based on the supervisor workflow outputs below, "
        "produce the final user-facing response.\n"
        "Constraints:\n"
        "- Be concise but complete.\n"
        "- If the web content was summarized, include a short bullet list of key points.\n"
        "- Do not invent facts not present in the fetched text.\n\n"
        f"Conversation history and worker output:\n{history}"
    )

    response = llm.invoke([SystemMessage(content="You write high-quality summaries."), HumanMessage(content=prompt)])

    return {"messages": [AIMessage(content=response.content)], "next": "FINISH"}


# ----------------------------
# Build graph
# ----------------------------
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("web_worker", web_worker_node)
workflow.add_node("writer_worker", writer_worker_node)

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda state: state["next"],
    {
        "web_worker": "web_worker",
        "writer_worker": "writer_worker",
        "FINISH": END,
    },
)

workflow.add_edge("web_worker", "writer_worker")
workflow.add_edge("writer_worker", END)

checkpointer = MemorySaver()
# (Optional) Add HITL gate later; for now run directly.
app = workflow.compile(checkpointer=checkpointer)


# ----------------------------
# Demo
# ----------------------------
if __name__ == "__main__":
    # Use an example URL; replace with your own.
    # Example: a blog post or documentation page.
    # Change this query to your desired URL/task.
    # Example: query = "Summarize https://www.wikipedia.org and give 5 key points."
    query = "Summarize https://medium.com/pythoneers/building-ai-agent-systems-with-langgraph-9d85537a6326 give 5 key points."

    config = {"configurable": {"thread_id": "day9-web-summarizer"}}
    print(f"🚀 User: {query}")

    final = app.invoke({"messages": [HumanMessage(content=query)], "next": "supervisor"}, config)

    print("\n--- FINAL ANSWER ---")
    for msg in final["messages"]:
        if isinstance(msg, AIMessage):
            print(msg.content)

