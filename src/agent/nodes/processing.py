import time
import hashlib
import logging
from typing import Dict, List
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response, get_depth_profile

logger = logging.getLogger(__name__)


def chunking_node(state: ResearchState) -> Dict:
    """CHUNKING NODE: Split all scraped content into manageable chunks."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)
    chunk_size = profile["chunk_size"]
    chunk_overlap = profile.get("chunk_overlap", chunk_size // 5)
    max_chunks = profile["max_chunks"]

    logger.info("=" * 60)
    logger.info("[CHUNKING] Splitting content [size=%d, overlap=%d, max=%d]", chunk_size, chunk_overlap, max_chunks)
    logger.info("=" * 60)

    start_time = time.time()

    search_results = state["search_results"]
    chunks = []

    for idx, result in enumerate(search_results):
        content = result.get("content", "")
        if not content:
            continue

        content_chunks = []
        for i in range(0, len(content), chunk_size - chunk_overlap):
            chunk = content[i:i + chunk_size]
            if len(chunk) > 100:
                content_chunks.append(chunk)

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

            if len(chunks) >= max_chunks:
                break
        if len(chunks) >= max_chunks:
            break

    elapsed = time.time() - start_time

    logger.info("[CHUNKING] Created %d chunks from %d sources in %.2fs", len(chunks), len(search_results), elapsed)

    timestamps = state.get("timestamps", {})
    timestamps["chunking"] = elapsed
    return {
        "raw_content_chunks": [c["content"] for c in chunks],
        "processed_chunks": chunks,
        "status": "chunking_complete",
        "timestamps": timestamps,
    }


def ranking_node(state: ResearchState) -> Dict:
    """RANKING NODE: Rank and filter chunks using two-stage approach."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)
    max_chunks = profile["max_chunks"]

    logger.info("=" * 60)
    logger.info("[RANKING] Multi-stage relevance scoring [depth=%s]", depth)
    logger.info("=" * 60)

    start_time = time.time()

    user_query = state["user_query"]
    chunks = state["processed_chunks"]

    if not chunks:
        return {"ranked_chunks": [], "status": "ranking_complete", "timestamps": {}}

    logger.info("Ranking %d chunks...", len(chunks))

    # Stage 1: Fast Keyword Matching
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
    top_for_rerank = min(100, max_chunks)
    top_candidates = scored_chunks[:top_for_rerank]

    # Stage 2: LLM-based Reranking
    logger.info("Reranking top %d candidates using LLM...", len(top_candidates))
    llm = get_llm()

    batch_size = 10
    for i in range(0, len(top_candidates), batch_size):
        batch = top_candidates[i:i + batch_size]
        batch_text = "\n\n".join([f"ID {j}: {c['content'][:500]}" for j, c in enumerate(batch)])

        system_prompt = """You are a relevance judge. Rate how relevant the provided chunks are to the user's query.
        Return ONLY a JSON list of scores [0.0 to 1.0] corresponding to the chunk IDs.
        Example: {"scores": [0.9, 0.1, 0.5]}"""

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {user_query}\n\nChunks:\n{batch_text}")
        ])

        parsed = extract_json_from_response(response.content)
        scores = parsed.get("scores", [])
        for idx, score in enumerate(scores):
            if idx < len(batch):
                batch[idx]["relevance_score"] = score

    # Final sort and filter
    top_candidates.sort(key=lambda x: x["relevance_score"], reverse=True)
    ranked_chunks = top_candidates[:max_chunks]

    elapsed = time.time() - start_time
    logger.info("[RANKING] Kept top %d chunks in %.2fs", len(ranked_chunks), elapsed)

    timestamps = state.get("timestamps", {})
    timestamps["ranking"] = elapsed
    return {
        "ranked_chunks": ranked_chunks,
        "status": "ranking_complete",
        "timestamps": timestamps,
    }
