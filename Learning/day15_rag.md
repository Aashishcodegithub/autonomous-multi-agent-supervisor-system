# Day 15: Basic RAG model (learning + runnable demo)

## Files
- `Learning/day15_basic_rag.py`
  - RAG using Gemini embeddings + in-memory cosine similarity.
  - May fail if embedding models are not available for your Gemini key/account.

- `Learning/day15_basic_rag_simple_retrieval.py`
  - RAG demo that always runs.
  - Uses lexical/token-overlap retrieval (no embedding API, no vector DB).

## Run
1) Always-runs demo (recommended):
```bash
python Learning/day15_basic_rag_simple_retrieval.py
```

2) Embeddings-based demo (may require setting EMBEDDING_MODEL):
```bash
python Learning/day15_basic_rag.py
# optionally:
EMBEDDING_MODEL=YOUR_EMBED_MODEL python Learning/day15_basic_rag.py
```

## Example
Set question via env var:
```bash
RAG_QUESTION="What is RAG?" python Learning/day15_basic_rag_simple_retrieval.py
```

