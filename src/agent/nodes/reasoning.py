import time
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response, MAX_REASONING_QUERIES, VECTOR_DB_QUERY_RESULTS
from src.database.embeddings import get_embedding_model
from src.database.vector_db import get_vector_db

def reasoning_loop_node(state: ResearchState) -> Dict:
    """
    REASONING LOOP NODE: Generate reasoning queries and search vector DB.
    """
    current_pass = state.get("reasoning_passes", 0) + 1
    print("\n" + "="*80)
    print(f"[PHASE 7] REASONING LOOP - Pass {current_pass} Deep analysis")
    print("="*80)

    start_time = time.time()

    llm = get_llm()
    embedding_model = get_embedding_model()
    vector_db = get_vector_db()

    user_query = state["user_query"]
    sub_questions = state["sub_questions"]

    # Generate reasoning queries
    print(f"\nGenerating reasoning queries for pass {current_pass}...")

    system_prompt = """You are a deep reasoning expert. Generate exactly 60 analytical questions that will help synthesize research findings.

These questions should:
- Probe deeper connections between concepts
- Identify patterns and trends
- Challenge assumptions
- Explore implications and consequences
- Synthesize multiple perspectives
- Find gaps and contradictions

Return ONLY JSON:
{
  "reasoning_queries": [
    "query 1",
    "query 2",
    ...
    "query 60"
  ]
}"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Generate 60 deep reasoning queries for: {user_query}. Focus on deeper synthesis for pass {current_pass}.")
    ])

    parsed = extract_json_from_response(response.content)
    reasoning_queries = parsed.get("reasoning_queries", [])

    if not reasoning_queries:
        reasoning_queries = sub_questions.copy() * 4

    print(f"\nQuerying vector DB with {len(reasoning_queries)} reasoning queries...")

    reasoning_results = []
    for idx, query in enumerate(reasoning_queries[:MAX_REASONING_QUERIES]):
        if idx % 10 == 0:
            print(f"  Processing reasoning query [{idx+1}/{MAX_REASONING_QUERIES}]...")

        query_embedding = embedding_model.embed_text(query)
        results = vector_db.query_similar(query, query_embedding, n_results=VECTOR_DB_QUERY_RESULTS)

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

    elapsed = time.time() - start_time
    print(f"[OK] Completed reasoning pass {current_pass}: {len(reasoning_results)} insights in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps[f"reasoning_pass_{current_pass}"] = elapsed
    return {
        "reasoning_queries": reasoning_queries[:MAX_REASONING_QUERIES],
        "reasoning_results": state.get("reasoning_results", []) + reasoning_results,
        "reasoning_passes": current_pass,
        "max_reasoning_passes": 3,
        "status": f"reasoning_pass_{current_pass}_complete",
        "timestamps": timestamps,
    }

def gap_detection_node(state: ResearchState) -> Dict:
    """
    GAP DETECTION NODE: Analyze current results and decide if more search is needed.
    """
    print("\n" + "="*80)
    print("[PHASE 7.5] GAP DETECTION - Analyzing information coverage")
    print("="*80)

    llm = get_llm()
    user_query = state["user_query"]
    results = state["reasoning_results"]

    # Summarize current knowledge for the LLM
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
      "suggested_queries": ["query 1", "query 2", ...] // Only if gap_found is true
    }"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"USER QUERY: {user_query}\n\nCURRENT INSIGHTS:\n{knowledge_summary}")
    ])

    parsed = extract_json_from_response(response.content)
    gap_found = parsed.get("gap_found", False)
    suggested_queries = parsed.get("suggested_queries", [])

    print(f"[OK] Gap detection result: {'GAP FOUND' if gap_found else 'COMPLETE'}")
    print(f"Reasoning: {parsed.get('reasoning', 'No reasoning provided')}")

    if gap_found:
        return {
            "search_queries": suggested_queries,
            "status": "gap_found_searching",
            "reasoning_results": state["reasoning_results"] # Preserve
        }
    else:
        return {
            "status": "research_complete",
        }
