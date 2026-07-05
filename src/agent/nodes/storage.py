import time
from typing import Dict
from src.agent.core.state import ResearchState
from src.database.embeddings import get_embedding_model
from src.database.vector_db import get_vector_db

def vector_db_node(state: ResearchState) -> Dict:
    """
    VECTOR DB NODE: Convert ranked chunks to embeddings and store in ChromaDB.
    """
    print("\n" + "="*80)
    print("[PHASE 6] VECTOR DATABASE - Creating embeddings with Ollama")
    print("="*80)

    start_time = time.time()

    embedding_model = get_embedding_model()
    vector_db = get_vector_db()

    # Reset collection for fresh research
    vector_db.reset_collection()
    vector_db.create_collection()

    ranked_chunks = state["ranked_chunks"]

    print(f"\nCreating embeddings for {len(ranked_chunks)} chunks...")

    # Extract content and create embeddings
    contents = [chunk["content"] for chunk in ranked_chunks]
    embeddings = embedding_model.embed_texts(contents)

    # Add to vector DB with metadata
    metadatas = []
    for chunk in ranked_chunks:
        metadatas.append({
            "source": chunk.get("source", ""),
            "title": chunk.get("title", ""),
            "query": chunk.get("query", ""),
            "relevance_score": str(chunk.get("relevance_score", 0)),
            "chunk_index": str(chunk.get("chunk_index", 0))
        })

    vector_db.batch_add_with_embeddings(contents, embeddings, metadatas)

    stats = vector_db.get_collection_stats()

    elapsed = time.time() - start_time

    print(f"[OK] Stored {stats['count']} documents in vector DB in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["vector_db"] = elapsed
    return {
        "embeddings": embeddings,
        "vector_db_stats": stats,
        "status": "vector_db_complete",
        "timestamps": timestamps,
    }
