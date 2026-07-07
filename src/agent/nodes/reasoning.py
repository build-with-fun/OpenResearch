import time
import logging
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response, get_depth_profile
from src.database.embeddings import get_embedding_model
from src.database.vector_db import get_vector_db

logger = logging.getLogger(__name__)


def reasoning_loop_node(state: ResearchState) -> Dict:
    """REASONING LOOP NODE: Generate reasoning queries and search vector DB."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)
    max_reasoning_queries = profile["max_reasoning_queries"]
    vector_db_results = profile["vector_db_query_results"]

    current_pass = state.get("reasoning_passes", 0) + 1

    logger.info("=" * 60)
    logger.info("[REASONING] Pass %d/%d [depth=%s]", current_pass, profile["max_reasoning_passes"], depth)
    logger.info("=" * 60)

    start_time = time.time()

    llm = get_llm()
    embedding_model = get_embedding_model()
    vector_db = get_vector_db()

    user_query = state["user_query"]

    logger.info("Generating %d reasoning queries for pass %d...", max_reasoning_queries, current_pass)

    system_prompt = f"""You are a deep reasoning expert. Generate exactly {max_reasoning_queries} analytical questions that will help synthesize research findings.

These questions should:
- Probe deeper connections between concepts
- Identify patterns and trends
- Challenge assumptions
- Explore implications and consequences
- Synthesize multiple perspectives
- Find gaps and contradictions

Return ONLY JSON:
{{
  "reasoning_queries": [
    "query 1",
    ...
  ]
}}"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate {max_reasoning_queries} deep reasoning queries for: {user_query}. Focus on deeper synthesis for pass {current_pass}.")
    ])

    parsed = extract_json_from_response(response.content)
    reasoning_queries = parsed.get("reasoning_queries", [])

    if not reasoning_queries:
        reasoning_queries = state.get("sub_questions", []) * 4

    logger.info("Querying vector DB with %d reasoning queries...", len(reasoning_queries))

    reasoning_results = []
    total_insights = 0
    for idx, query in enumerate(reasoning_queries[:max_reasoning_queries]):
        if idx % 10 == 0:
            logger.info("  Processing reasoning query [%d/%d]...", idx + 1, max_reasoning_queries)

        query_embedding = embedding_model.embed_text(query)
        results = vector_db.query_similar(query, query_embedding, n_results=vector_db_results)

        if results.get("documents") and results["documents"][0]:
            for doc, metadata, distance in zip(
                results["documents"][0],
                results.get("metadatas", [[]])[0],
                results.get("distances", [[]])[0]
            ):
                reasoning_results.append({
                    "query": query,
                    "content": doc,
                    "metadata": metadata,
                    "similarity": 1 - distance,
                    "reasoning_pass": current_pass,
                })
                total_insights += 1

    elapsed = time.time() - start_time
    logger.info("[REASONING] Pass %d complete: %d insights in %.2fs", current_pass, len(reasoning_results), elapsed)

    timestamps = state.get("timestamps", {})
    timestamps[f"reasoning_pass_{current_pass}"] = elapsed
    return {
        "reasoning_queries": reasoning_queries[:max_reasoning_queries],
        "reasoning_results": state.get("reasoning_results", []) + reasoning_results,
        "reasoning_passes": current_pass,
        "max_reasoning_passes": profile["max_reasoning_passes"],
        "status": f"reasoning_pass_{current_pass}_complete",
        "timestamps": timestamps,
    }


def gap_detection_node(state: ResearchState) -> Dict:
    """GAP DETECTION NODE: Analyze current results and decide if more search is needed."""
    current_pass = state.get("reasoning_passes", 0)
    max_passes = state.get("max_reasoning_passes", 3)

    logger.info("=" * 60)
    logger.info("[GAP DETECTION] Analyzing coverage [pass %d/%d]", current_pass, max_passes)
    logger.info("=" * 60)

    llm = get_llm()
    user_query = state["user_query"]
    results = state["reasoning_results"]

    knowledge_summary = "\n".join([
        f"- {r['content'][:200]}..." for r in results[-100:]
    ])

    system_prompt = """You are a research auditor. Your task is to identify "information gaps" in the current research results.

Compare the user's original query against the extracted insights.
Determine if there are critical missing pieces, contradictions that need resolving, or unexplored angles.

Return ONLY JSON:
{
  "gap_found": boolean,
  "reasoning": "Explain why a gap exists or why the research is complete",
  "suggested_queries": ["query 1", "query 2", ...]
}"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"USER QUERY: {user_query}\n\nCURRENT INSIGHTS:\n{knowledge_summary}")
    ])

    parsed = extract_json_from_response(response.content)
    gap_found = parsed.get("gap_found", False)
    suggested_queries = parsed.get("suggested_queries", [])

    logger.info("[GAP DETECTION] Result: %s", "GAP FOUND" if gap_found else "COMPLETE")
    logger.info("Reasoning: %s", parsed.get("reasoning", "No reasoning provided"))

    if gap_found and current_pass < max_passes:
        return {
            "search_queries": suggested_queries,
            "status": "gap_found_searching",
            "reasoning_results": state["reasoning_results"],
        }
    else:
        return {
            "status": "research_complete",
        }
