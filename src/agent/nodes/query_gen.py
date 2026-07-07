import time
import logging
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response, get_depth_profile

logger = logging.getLogger(__name__)


def search_query_generator_node(state: ResearchState) -> Dict:
    """SEARCH QUERY GENERATOR: Generate optimized search queries from sub-questions."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)
    max_queries = profile["max_search_queries"]

    logger.info("=" * 60)
    logger.info("[QUERY GEN] Creating %d search queries [depth=%s]", max_queries, depth)
    logger.info("=" * 60)

    start_time = time.time()

    llm = get_llm()
    sub_questions = state["sub_questions"]
    user_query = state["user_query"]

    system_prompt = f"""You are a search query optimization expert. Generate highly effective search queries for web research.

Given sub-questions, generate multiple optimized search queries for each sub-question.

Guidelines:
- Generate at least {max_queries} total search queries
- Include keyword variations, synonyms, and related terms
- Use different query formats: "what is", "how to", "best", "vs", "review", etc.
- Include technical terms and layman terms
- Make queries specific and targeted

Return ONLY a JSON object:
{{
  "search_queries": [
    "query 1",
    ...
  ]
}}"""

    sub_questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(sub_questions)])

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query: {user_query}\n\nSub-questions:\n{sub_questions_text}\n\nGenerate {max_queries}+ optimized search queries.")
    ])

    parsed = extract_json_from_response(response.content)
    search_queries = parsed.get("search_queries", [])

    if len(search_queries) < max_queries:
        search_queries = sub_questions.copy()
        prefixes = ["what is", "how does", "best", "top", "guide to"]
        for q in sub_questions:
            if len(search_queries) >= max_queries:
                break
            for prefix in prefixes:
                if len(search_queries) >= max_queries:
                    break
                search_queries.append(f"{prefix} {q}")

    elapsed = time.time() - start_time

    logger.info("[QUERY GEN] Generated %d search queries in %.2fs", len(search_queries), elapsed)

    timestamps = state.get("timestamps", {})
    timestamps["query_generation"] = elapsed
    return {
        "search_queries": search_queries,
        "status": "query_generation_complete",
        "timestamps": timestamps,
    }
