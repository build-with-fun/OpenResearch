import time
import asyncio
import logging
from typing import Dict, Optional, Callable, Awaitable, Any
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage

from src.agent.core.state import ResearchState
from src.agent.core.llm import get_depth_profile
from src.agent.nodes.planner import planner_node
from src.agent.nodes.query_gen import search_query_generator_node
from src.agent.nodes.search import web_search_node
from src.agent.nodes.processing import chunking_node, ranking_node
from src.agent.nodes.storage import vector_db_node
from src.agent.nodes.reasoning import reasoning_loop_node, gap_detection_node
from src.agent.nodes.synthesis import final_answer_node

logger = logging.getLogger(__name__)

# Optional async callback for progress events (set by server for SSE streaming)
_progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None


def set_progress_callback(callback: Optional[Callable[[str, dict], Awaitable[None]]]):
    """Set a global progress callback for SSE event streaming."""
    global _progress_callback
    _progress_callback = callback


async def _emit(step: str, data: dict):
    """Emit a progress event if a callback is registered."""
    if _progress_callback:
        try:
            await _progress_callback(step, data)
        except Exception:
            pass


def _emit_sync(step: str, data: dict):
    """Synchronous version of _emit for use in sync node functions."""
    if _progress_callback:
        try:
            asyncio.run(_progress_callback(step, data))
        except Exception:
            pass


# Node progress metadata: step key, progress %, message template
_NODE_PROGRESS = {
    "planner": ("planning", 10, "Analyzing query and generating plan..."),
    "query_generator": ("query_generation", 20, "Creating optimized search queries..."),
    "web_search": ("searching", 35, "Searching the web for sources..."),
    "chunking": ("chunking", 50, "Processing and chunking content..."),
    "ranking": ("ranking", 60, "Ranking content by relevance..."),
    "vector_db": ("vector_db", 70, "Storing embeddings in vector database..."),
    "reasoning": ("reasoning", 75, "Running deep reasoning passes..."),
    "gap_detection": ("gap_detection", 85, "Checking for knowledge gaps..."),
    "final_answer": ("synthesizing", 95, "Synthesizing final answer..."),
}


def _wrap_node(node_func, node_name: str) -> Callable:
    """Wrap a LangGraph node to emit progress events before and after execution."""
    step_key, progress, msg = _NODE_PROGRESS.get(node_name, (node_name, 0, f"Running {node_name}..."))

    async def async_wrapper(state: ResearchState) -> dict:
        await _emit("status", {"current_step": step_key, "progress": progress, "message": msg})
        result = await node_func(state)
        await _emit("status", {"current_step": f"{step_key}_complete", "progress": progress + 5, "message": f"{msg} Complete"})
        return result

    def sync_wrapper(state: ResearchState) -> dict:
        _emit_sync("status", {"current_step": step_key, "progress": progress, "message": msg})
        result = node_func(state)
        _emit_sync("status", {"current_step": f"{step_key}_complete", "progress": progress + 5, "message": f"{msg} Complete"})
        return result

    if asyncio.iscoroutinefunction(node_func):
        return async_wrapper
    return sync_wrapper


def decide_to_continue(state: ResearchState):
    """Conditional edge to decide if we need more research."""
    if state.get("status") == "gap_found_searching" and state.get("reasoning_passes", 0) < state.get("max_reasoning_passes", 3):
        return "query_generator"
    return "final_answer"


def build_research_graph():
    """Build the complete research workflow graph with progress emission."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("planner", _wrap_node(planner_node, "planner"))
    workflow.add_node("query_generator", _wrap_node(search_query_generator_node, "query_generator"))
    workflow.add_node("web_search", _wrap_node(web_search_node, "web_search"))
    workflow.add_node("chunking", _wrap_node(chunking_node, "chunking"))
    workflow.add_node("ranking", _wrap_node(ranking_node, "ranking"))
    workflow.add_node("vector_db", _wrap_node(vector_db_node, "vector_db"))
    workflow.add_node("reasoning", _wrap_node(reasoning_loop_node, "reasoning"))
    workflow.add_node("gap_detection", _wrap_node(gap_detection_node, "gap_detection"))
    workflow.add_node("final_answer", _wrap_node(final_answer_node, "final_answer"))

    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "query_generator")
    workflow.add_edge("query_generator", "web_search")
    workflow.add_edge("web_search", "chunking")
    workflow.add_edge("chunking", "ranking")
    workflow.add_edge("ranking", "vector_db")
    workflow.add_edge("vector_db", "reasoning")
    workflow.add_edge("reasoning", "gap_detection")

    workflow.add_conditional_edges(
        "gap_detection",
        decide_to_continue,
        {
            "query_generator": "query_generator",
            "final_answer": "final_answer"
        }
    )

    workflow.add_edge("final_answer", END)

    return workflow.compile()


async def run_deep_research(user_query: str, depth: str = "standard"):
    """Execute the complete deep research pipeline.

    Args:
        user_query: User's research query
        depth: Research depth - "quick", "standard", or "deep"

    Returns:
        Dictionary with final answer and metadata
    """
    profile = get_depth_profile(depth)

    logger.info("=" * 60)
    logger.info("DEEP RESEARCH AI - INITIATED  [depth=%s]", depth)
    logger.info("=" * 60)
    logger.info("Query: %s", user_query)
    logger.info("Profile: %s", profile["description"])

    total_start = time.time()

    await _emit("status", {
        "current_step": "initializing",
        "progress": 0,
        "message": f"Starting {depth} research...",
    })

    graph = build_research_graph()

    initial_state = {
        "user_query": user_query,
        "research_depth": depth,
        "sub_questions": [],
        "search_queries": [],
        "search_results": [],
        "raw_content_chunks": [],
        "processed_chunks": [],
        "ranked_chunks": [],
        "embeddings": [],
        "vector_db_stats": {},
        "reasoning_queries": [],
        "reasoning_results": [],
        "reasoning_passes": 0,
        "max_reasoning_passes": profile["max_reasoning_passes"],
        "final_answer": "",
        "sources": [],
        "confidence_score": 0.0,
        "messages": [HumanMessage(content=user_query)],
        "status": "started",
        "errors": [],
        "timestamps": {}
    }

    logger.info("Executing research pipeline...")
    result = await graph.ainvoke(initial_state)

    total_elapsed = time.time() - total_start

    logger.info("=" * 60)
    logger.info("RESEARCH COMPLETE  [depth=%s, %.2fs]", depth, total_elapsed)
    logger.info("Sub-questions: %d", len(result.get("sub_questions", [])))
    logger.info("Search queries: %d", len(result.get("search_queries", [])))
    logger.info("Websites searched: %d", len(result.get("search_results", [])))
    logger.info("Content chunks: %d", len(result.get("processed_chunks", [])))
    logger.info("Ranked chunks: %d", len(result.get("ranked_chunks", [])))
    logger.info("Confidence: %.2f%%", result.get("confidence_score", 0) * 100)
    logger.info("Sources: %d", len(result.get("sources", [])))
    logger.info("=" * 60)

    return result


def run_deep_research_sync(user_query: str, depth: str = "standard"):
    """Synchronous wrapper for async research execution."""
    return asyncio.run(run_deep_research(user_query, depth))
