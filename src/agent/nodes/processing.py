import time
import hashlib
from typing import Dict, List
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, CHUNK_SIZE, CHUNK_OVERLAP, MAX_CHUNKS

def chunking_node(state: ResearchState) -> Dict:
    """
    CHUNKING NODE: Split all scraped content into manageable chunks.
    """
    print("\n" + "="*80)
    print("[PHASE 4] CHUNKING - Splitting content into segments")
    print("="*80)

    start_time = time.time()

    search_results = state["search_results"]
    chunks = []

    for idx, result in enumerate(search_results):
        content = result.get("content", "")
        if not content:
            continue

        # Split content into overlapping chunks
        content_chunks = []
        for i in range(0, len(content), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk = content[i:i + CHUNK_SIZE]
            if len(chunk) > 100:  # Minimum chunk size
                content_chunks.append(chunk)

        # Add metadata to each chunk
        for chunk_idx, chunk in enumerate(content_chunks):
            chunks.append({
                "content": chunk,
                "source": result.get("url", "unknown"),
                "title": result.get("title", ""),
                "query": result.get("query", ""),
                "chunk_index": chunk_idx,
                "total_chunks": len(content_chunks),
                "result_index": idx,
                "content_hash": hashlib.sha256(chunk.encode()).hexdigest(),
            })

    elapsed = time.time() - start_time

    print(f"[OK] Created {len(chunks)} chunks from {len(search_results)} sources in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["chunking"] = elapsed
    return {
        "raw_content_chunks": [c["content"] for c in chunks],
        "processed_chunks": chunks,
        "status": "chunking_complete",
        "timestamps": timestamps,
    }

def ranking_node(state: ResearchState) -> Dict:
    """
    RANKING NODE: Rank and filter chunks using a two-stage approach.
    Stage 1: Fast keyword match.
    Stage 2: Advanced LLM-based reranking.
    """
    print("\n" + "="*80)
    print("[PHASE 5] RANKING - Multi-stage relevance scoring")
    print("="*80)

    start_time = time.time()

    user_query = state["user_query"]
    chunks = state["processed_chunks"]

    if not chunks:
        return {"ranked_chunks": [], "status": "ranking_complete", "timestamps": {}}

    print(f"Ranking {len(chunks)} chunks...")

    # --- Stage 1: Fast Keyword Matching ---
    scored_chunks = []
    for chunk in chunks:
        content = chunk["content"].lower()
        query_words = user_query.lower().split()
        score = sum(1 for word in query_words if word in content)
        score /= max(len(query_words), 1)
        if any(word in chunk.get("title", "").lower() for word in query_words):
            score += 0.3
        chunk["relevance_score"] = min(score, 1.0)
        scored_chunks.append(chunk)

    scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)
    top_candidates = scored_chunks[:100] # Take top 100 for reranking

    # --- Stage 2: LLM-based Reranking (Cross-Encoder Proxy) ---
    print(f"Reranking top 100 candidates using LLM...")
    llm = get_llm()
    final_ranked = []

    # Process in batches to avoid too many LLM calls
    batch_size = 10
    for i in range(0, len(top_candidates), batch_size):
        batch = top_candidates[i:i+batch_size]

        batch_text = "\n\n".join([f"ID {j}: {c['content'][:500]}" for j, c in enumerate(batch)])

        system_prompt = """You are a relevance judge. Rate how relevant the provided chunks are to the user's query.
        Return ONLY a JSON list of scores [0.0 to 1.0] corresponding to the chunk IDs.
        Example: {"scores": [0.9, 0.1, 0.5]}"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {user_query}\n\nChunks:\n{batch_text}")
        ])

        import json
        try:
            # Basic JSON extraction
            content = response.content
            if "{" in content:
                start = content.index("{")
                end = content.rindex("}") + 1
                scores = json.loads(content[start:end]).get("scores", [])
                for idx, score in enumerate(scores):
                    if idx < len(batch):
                        batch[idx]["relevance_score"] = score
        except Exception as e:
            print(f"  Reranking error in batch: {e}")

    # Final sort and filter
    top_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
    ranked_chunks = top_candidates[:MAX_CHUNKS]

    elapsed = time.time() - start_time
    print(f"[OK] Ranked chunks: kept top {len(ranked_chunks)} in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["ranking"] = elapsed
    return {
        "ranked_chunks": ranked_chunks,
        "status": "ranking_complete",
        "timestamps": timestamps,
    }
