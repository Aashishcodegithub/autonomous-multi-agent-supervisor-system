# Day 15: Basic RAG (Retrieval-Augmented Generation)
# Goal: Provide a minimal, actually-running RAG demo inside this repo.
#
# This implementation:
# - Uses a local in-repo document set (plain text files embedded below)
# - Builds embeddings with a lightweight approach
# - Retrieves top-k relevant chunks by cosine similarity
# - Feeds retrieved context into the LLM to answer
#
# Notes:
# - To keep it runnable in this environment without extra vector DB services,
#   we implement retrieval in pure Python (numpy) on top of embeddings.
# - Embeddings are produced via Gemini using LangChain's embedding wrapper.

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path
import os
import re

from dotenv import load_dotenv
import numpy as np

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings

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
        """
        Newton's First Law of Motion (Law of Inertia) states that an object will remain at rest,
        or continue moving at constant velocity in a straight line, unless acted upon by an external
        unbalanced force. If the net force on an object is zero, its velocity remains constant.
        """,
    ),
    (
        "rag_intro",
        """
        Retrieval-Augmented Generation (RAG) combines information retrieval with text generation.
        A system retrieves relevant documents or passages using embeddings, then conditions an LLM
        on that retrieved context to answer questions more accurately and with fewer hallucinations.
        """,
    ),
    (
        "langgraph_intro",
        """
        LangGraph is a framework for building stateful, multi-step agent workflows as graphs.
        It allows explicit control of execution flow, retries, and state persistence across steps.
        """,
    ),
]


def build_chunks() -> List[DocChunk]:
    chunks: List[DocChunk] = []
    for doc_name, doc_text in CORPUS:
        for i, ch in enumerate(simple_chunk_text(doc_text)):
            chunks.append(DocChunk(chunk_id=f"{doc_name}__{i}", text=ch))
    return chunks


# ----------------------------
# Retrieval (in-memory)
# ----------------------------
class InMemoryVectorStore:
    def __init__(self, chunks: List[DocChunk], embedding_fn):
        self.chunks = chunks
        self.embedding_fn = embedding_fn

        # Precompute embeddings once
        self.embeddings = self._embed([c.text for c in self.chunks])
        self.embeddings = self._normalize(self.embeddings)

    @staticmethod
    def _normalize(x: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
        return x / norms

    def _embed(self, texts: List[str]) -> np.ndarray:
        # LangChain embedding wrapper returns List[List[float]]
        vectors = self.embedding_fn.embed_documents(texts)
        return np.array(vectors, dtype=np.float32)

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        # both are normalized
        return float(np.dot(a, b))

    def query(self, q: str, top_k: int = 3) -> List[Tuple[DocChunk, float]]:
        q_vec = np.array(self.embedding_fn.embed_query(q), dtype=np.float32)
        q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-12)

        sims: List[Tuple[int, float]] = []
        for idx in range(len(self.chunks)):
            sims.append((idx, self._cosine_sim(self.embeddings[idx], q_vec)))

        sims.sort(key=lambda x: x[1], reverse=True)
        top = sims[:top_k]
        return [(self.chunks[i], s) for i, s in top]


# ----------------------------
# RAG Pipeline
# ----------------------------

def run_rag(question: str):
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0)
    # NOTE: embedding model name can vary by Gemini account / API version.
    # Try the default embedding model; if this fails, change EMBEDDING_MODEL.
    # Default to a widely-supported embedding model name; override via EMBEDDING_MODEL.
    embeddings = GoogleGenerativeAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "models/embedding-001"))

    try:
        # Force a tiny embed call early so we fail fast with a clear error.
        _ = embeddings.embed_query("test")
    except Exception as e:
        raise RuntimeError(
            "Embedding model call failed. Set EMBEDDING_MODEL to a valid Gemini embedding model for your API key. "
            f"Original error: {e}"
        )

    chunks = build_chunks()
    store = InMemoryVectorStore(chunks, embeddings)

    retrieved = store.query(question, top_k=3)

    context = "\n\n".join(
        [f"[{chunk.chunk_id}]\n{chunk.text}" for chunk, _score in retrieved]
    )

    prompt = (
        "You are a QA assistant. Answer the user's question using ONLY the retrieved context.\n"
        "If the context is insufficient, say exactly: [INSUFFICIENT CONTEXT].\n\n"
        f"RETRIEVED CONTEXT:\n{context}\n\n"
        f"USER QUESTION: {question}"
    )

    response = llm.invoke([SystemMessage(content="Answer using provided context."), HumanMessage(content=prompt)])

    answer = getattr(response, "content", str(response))
    return answer, retrieved


if __name__ == "__main__":
    q = os.getenv(
        "RAG_QUESTION",
        "What does Newton's First Law of Motion say? Explain in simple terms."
    )

    answer, retrieved = run_rag(q)
    print("\n=== RAG ANSWER ===")
    print(answer)

    print("\n=== TOP RETRIEVED CHUNKS ===")
    for chunk, score in retrieved:
        print(f"- {chunk.chunk_id} (score={score:.4f})")

