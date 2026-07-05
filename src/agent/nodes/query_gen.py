import time
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response, MAX_SEARCH_QUERIES

def search_query_generator_node(state: ResearchState) -> Dict:
    """
    SEARCH QUERY GENERATOR NODE: Generate 120+ optimized search queries from sub-questions.
    """
    print("\n" + "="*80)
    print("[PHASE 2] SEARCH QUERY GENERATION - Creating optimized search queries")
    print("="*80)

    start_time = time.time()

    llm = get_llm()

    sub_questions = state["sub_questions"]
    user_query = state["user_query"]

    system_prompt = """You are a search query optimization expert. Generate highly effective search queries for web research.

Given sub-questions, generate MULTIPLE optimized search queries for EACH sub-question (at least 3-4 variations per question).

Guidelines:
- Generate at least 120 total search queries
- Include keyword variations, synonyms, and related terms
- Use different query formats: "what is", "how to", "best", "vs", "review", etc.
- Include technical terms and layman terms
- Add site-specific queries when relevant (e.g., "site:arxiv.org")
- Make queries specific and targeted

Return ONLY a JSON object:
{
  "search_queries": [
    "query 1",
    "query 2",
    ...
  ]
}"""

    sub_questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(sub_questions)])

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query: {user_query}\n\nSub-questions:\n{sub_questions_text}\n\nGenerate 120+ optimized search queries.")
    ])

    # Parse response using shared helper
    parsed = extract_json_from_response(response.content)
    search_queries = parsed.get("search_queries", [])

    # Fallback: use sub-questions as search queries, capped at MAX_SEARCH_QUERIES
    if len(search_queries) < MAX_SEARCH_QUERIES:
        search_queries = sub_questions.copy()
        # Add targeted variations until we hit the cap
        prefixes = ["what is", "how does", "best", "top", "guide to"]
        for q in sub_questions:
            if len(search_queries) >= MAX_SEARCH_QUERIES:
                break
            for prefix in prefixes:
                if len(search_queries) >= MAX_SEARCH_QUERIES:
                    break
                search_queries.append(f"{prefix} {q}")

    elapsed = time.time() - start_time

    print(f"[OK] Generated {len(search_queries)} search queries in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["query_generation"] = elapsed
    return {
        "search_queries": search_queries,
        "status": "query_generation_complete",
        "timestamps": timestamps,
    }
