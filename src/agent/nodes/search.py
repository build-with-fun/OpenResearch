import time
from typing import Dict
from src.agent.core.state import ResearchState
from src.agent.core.llm import MAX_SEARCH_QUERIES, MAX_RESULTS_PER_QUERY
from src.agent.tools.scraper import AdvancedWebScraper

async def web_search_node(state: ResearchState) -> Dict:
    """
    WEB SEARCH NODE: Execute all search queries using Tavily (35 results each).
    """
    print("\n" + "="*80)
    print("[PHASE 3] WEB SEARCH - Searching with Tavily (35 results per query)")
    print("="*80)

    start_time = time.time()

    scraper = AdvancedWebScraper()
    search_queries = state["search_queries"]

    # Limit queries to avoid extremely long execution (adjust as needed)
    max_queries = min(len(search_queries), MAX_SEARCH_QUERIES)

    all_results = []
    total_websites = 0

    print(f"\nExecuting {max_queries} search queries with {MAX_RESULTS_PER_QUERY} results each...")
    print(f"Expected: ~{max_queries * MAX_RESULTS_PER_QUERY} website results\n")

    # Use batch search for concurrency
    batch_results = await scraper.batch_search(search_queries[:max_queries], max_results=MAX_RESULTS_PER_QUERY)

    for res in batch_results:
        if res.get("results"):
            all_results.extend(res["results"])
            total_websites += len(res["results"])

    elapsed = time.time() - start_time

    print(f"\n[OK] Web search complete: {total_websites} websites in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["web_search"] = elapsed
    return {
        "search_results": all_results,
        "status": "web_search_complete",
        "timestamps": timestamps,
    }
