# vector_store.py
"""
Vector Database using FAISS for semantic report resolution.
Uses SentenceTransformer embeddings + FAISS for fast similarity search.
"""

import os
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from report_config import REPORT_DEFINITIONS, VALID_REPORTS

# ============================================================
# FAISS Setup
# ============================================================
MODEL_NAME = "all-MiniLM-L6-v2"
DB_DIR = "./faiss_db"
INDEX_PATH = os.path.join(DB_DIR, "faiss_index.bin")
METADATA_PATH = os.path.join(DB_DIR, "metadata.pkl")

# Load embedding model once
embedding_model = SentenceTransformer(MODEL_NAME)

# Create DB directory if missing
os.makedirs(DB_DIR, exist_ok=True)


def setup_vector_db(force_reset: bool = False):
    """
    Build FAISS index from report definitions.
    Saves embeddings + metadata locally.
    Run once at startup (idempotent).
    """
    # Check if already exists and not forcing reset
    if os.path.exists(INDEX_PATH) and not force_reset:
        print(f"✅ FAISS DB already exists ({INDEX_PATH})")
        return

    # Build knowledge base from report_config
    documents = []
    report_names = []
    
    for report_name, config in REPORT_DEFINITIONS.items():
        documents.append(config["description"])
        report_names.append(report_name)

    # Generate embeddings
    print(f"📊 Generating embeddings for {len(documents)} reports...")
    embeddings = embedding_model.encode(documents, convert_to_numpy=True)
    
    # Create FAISS index
    import faiss
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings.astype(np.float32))

    # Save index
    faiss.write_index(index, INDEX_PATH)
    
    # Save metadata
    metadata = {
        "report_names": report_names,
        "embeddings_shape": embeddings.shape
    }
    with open(METADATA_PATH, "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ FAISS DB setup complete! {len(documents)} reports indexed.")


def get_best_report(query: str) -> str:
    """
    Semantic search using FAISS.
    
    Args:
        query: User's natural language query
        
    Returns:
        Report name (from REPORT_DEFINITIONS keys)
        
    Raises:
        ValueError: If no good match found (ask user to clarify)
    """
    import faiss
    
    # Load index and metadata
    if not os.path.exists(INDEX_PATH):
        raise ValueError("FAISS index not found. Call setup_vector_db() first.")
    
    index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "rb") as f:
        metadata = pickle.load(f)
    
    report_names = metadata["report_names"]

    # Encode query
    query_embedding = embedding_model.encode([query], convert_to_numpy=True).astype(np.float32)

    # Search (k=3 to get top 3 candidates)
    distances, indices = index.search(query_embedding, k=3)

    if len(indices[0]) == 0:
        available = ", ".join(VALID_REPORTS)
        raise ValueError(f"No report match found. Available: {available}")

    # Get best match
    best_idx = indices[0][0]
    best_distance = distances[0][0]
    best_report = report_names[best_idx]

    # Accept best match (no threshold check for now)
    print(f"🔍 Vector Search: '{query}' → {best_report} (distance: {best_distance:.3f})")
    return best_report


# Auto-initialize when imported
setup_vector_db()


if __name__ == "__main__":
    setup_vector_db(force_reset=True)
    
    test_queries = [
        "How much money do we have?",
        "What was our net profit last month?",
        "How many units of item X?",
        "Show me all transactions today",
        "What are our sales?",
        "Who owes us money?"
        "visualize debit vs credit"
        "visualize the closing balance"
    ]
    
    print("\n🧪 Testing Vector DB:")
    for q in test_queries:
        try:
            result = get_best_report(q)
            print(f"  ✓ '{q}' → {result}")
        except ValueError as e:
            print(f"  ✗ '{q}' → {e}")