# Day 15: RAG run mode notes

`day15_basic_rag.py` uses `GoogleGenerativeAIEmbeddings`.

If Gemini embedding models are unavailable for your API key/account (common error: `404 NOT_FOUND` for the embedding model name),
use:

- `day15_basic_rag_simple_retrieval.py`

This fallback implements retrieval via lexical overlap scoring (no embeddings / no vector DB), so it always runs.

