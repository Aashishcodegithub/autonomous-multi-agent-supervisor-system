# Day 15 (Fallback): Basic RAG with simple retrieval (no Gemini embeddings)
# Goal: Provide a basic RAG demo that actually runs even when embedding models are unavailable.
#
# This uses:
# - Local in-memory corpus
# - Retrieval by lexical similarity (token overlap + a simple BM25-like scoring)
# - LLM generation conditioned on retrieved context
#
# Retrieval is intentionally lightweight so this day always runs.

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path
import os
import re
from collections import Counter

from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage


load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODEL_NAME = os.getenv("LLM_MODEL", "gemini-2.5-flash")


# ----------------------------
# Mini document store (local)
# ----------------------------
@dataclass
class DocChunk:
    chunk_id: str
    text: str


def simple_chunk_text(text: str, chunk_size: int = 600, overlap: int = 80) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


CORPUS: List[Tuple[str, str]] = [
    (
        "newton_first_law",
        """Newton's First Law of Motion (Law of Inertia) states that an object will remain at rest,
        or continue moving at constant velocity in a straight line, unless acted upon by an external
        unbalanced force.""",
    ),
    (
        "rag_intro",
        """Retrieval-Augmented Generation (RAG) combines information retrieval with text generation.
        The system retrieves relevant passages and uses them as context for the LLM to answer questions.""",
    ),
    (
        "langgraph_intro",
        """LangGraph builds stateful multi-step agent workflows as graphs, enabling explicit control
        flow, retries, and persistence across steps.""",
    ),
]


def build_chunks() -> List[DocChunk]:
    chunks: List[DocChunk] = []
    for doc_name, doc_text in CORPUS:
        for i, ch in enumerate(simple_chunk_text(doc_text)):
            chunks.append(DocChunk(chunk_id=f"{doc_name}__{i}", text=ch))
    return chunks


# ----------------------------
# Simple lexical retrieval
# ----------------------------
_WORD_RE = re.compile(r"[a-zA-Z0-9']+")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text)]


def bm25_like_score(query_tokens: List[str], doc_tokens: List[str]) -> float:
    # tiny, approximate scoring: overlap weighted by doc term frequency
    if not query_tokens or not doc_tokens:
        return 0.0

    q_counts = Counter(query_tokens)
    d_counts = Counter(doc_tokens)

    score = 0.0
    for term, q_tf in q_counts.items():
        if term in d_counts:
            tf = d_counts[term]
            score += q_tf * (1.0 + (tf / (tf + 1.0)))
    return score


def retrieve(chunks: List[DocChunk], question: str, top_k: int = 3) -> List[Tuple[DocChunk, float]]:
    q_tokens = tokenize(question)
    scored: List[Tuple[int, float]] = []
    doc_tokens_cache = [tokenize(c.text) for c in chunks]

    for i, tokens in enumerate(doc_tokens_cache):
        s = bm25_like_score(q_tokens, tokens)
        scored.append((i, s))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]
    return [(chunks[i], s) for i, s in top]


# ----------------------------
# RAG Pipeline
# ----------------------------

def run_rag(question: str):
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)

    chunks = build_chunks()
    retrieved = retrieve(chunks, question, top_k=3)

    context = "\n\n".join([f"[{c.chunk_id}]\n{c.text}" for c, _s in retrieved])

    prompt = (
        "You are a QA assistant. Answer the user's question using ONLY the retrieved context.\n"
        "If the context is insufficient, say exactly: [INSUFFICIENT CONTEXT].\n\n"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        f"USER QUESTION: {question}"
    )

    response = llm.invoke(
        [SystemMessage(content="Answer using the provided context."), HumanMessage(content=prompt)]
    )

    answer = getattr(response, "content", str(response))
    return answer, retrieved


if __name__ == "__main__":
    q = os.getenv(
        "RAG_QUESTION",
        "What does Newton's First Law of Motion say in simple terms?",
    )

    answer, retrieved = run_rag(q)

    print("\n=== RAG ANSWER ===")
    print(answer)

    print("\n=== TOP RETRIEVED CHUNKS ===")
    for chunk, score in retrieved:
        print(f"- {chunk.chunk_id} (score={score:.4f})")

