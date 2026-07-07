import time
import logging
from typing import Dict
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_depth_profile
from src.agent.tools.scraper import AdvancedWebScraper

logger = logging.getLogger(__name__)


async def web_search_node(state: ResearchState) -> Dict:
    """WEB SEARCH NODE: Execute all search queries using Tavily."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)
    max_queries = profile["max_search_queries"]
    max_results = profile["max_results_per_query"]

    logger.info("=" * 60)
    logger.info("[WEB SEARCH] Searching with Tavily [%d queries, %d results each]", max_queries, max_results)
    logger.info("=" * 60)

    start_time = time.time()

    scraper = AdvancedWebScraper()
    search_queries = state["search_queries"]

    max_q = min(len(search_queries), max_queries)

    all_results = []
    total_websites = 0

    logger.info("Executing %d search queries with %d results each...", max_q, max_results)
    logger.info("Expected: ~%d website results", max_q * max_results)

    batch_results = await scraper.batch_search(search_queries[:max_q], max_results=max_results)

    for res in batch_results:
        if res.get("results"):
            all_results.extend(res["results"])
            total_websites += len(res["results"])

    elapsed = time.time() - start_time

    logger.info("[WEB SEARCH] Complete: %d websites in %.2fs", total_websites, elapsed)

    timestamps = state.get("timestamps", {})
    timestamps["web_search"] = elapsed
    return {
        "search_results": all_results,
        "status": "web_search_complete",
        "timestamps": timestamps,
    }
