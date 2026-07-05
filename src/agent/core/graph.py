import time
from typing import Dict
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage

from src.agent.core.state import ResearchState
from src.agent.nodes.planner import planner_node
from src.agent.nodes.query_gen import search_query_generator_node
from src.agent.nodes.search import web_search_node
from src.agent.nodes.processing import chunking_node, ranking_node
from src.agent.nodes.storage import vector_db_node
from src.agent.nodes.reasoning import reasoning_loop_node, gap_detection_node
from src.agent.nodes.synthesis import final_answer_node

def decide_to_continue(state: ResearchState):
    """Conditional edge to decide if we need more research."""
    if state.get("status") == "gap_found_searching" and state.get("reasoning_passes", 0) < state.get("max_reasoning_passes", 3):
        return "query_generator"
    return "final_answer"

def build_research_graph():
    """Build the complete research workflow graph.

    Returns:
        CompiledStateGraph: The compiled LangGraph workflow.
    """

    workflow = StateGraph(ResearchState)

    # Add nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("query_generator", search_query_generator_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("chunking", chunking_node)
    workflow.add_node("ranking", ranking_node)
    workflow.add_node("vector_db", vector_db_node)
    workflow.add_node("reasoning", reasoning_loop_node)
    workflow.add_node("gap_detection", gap_detection_node)
    workflow.add_node("final_answer", final_answer_node)

    # Add edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "query_generator")
    workflow.add_edge("query_generator", "web_search")
    workflow.add_edge("web_search", "chunking")
    workflow.add_edge("chunking", "ranking")
    workflow.add_edge("ranking", "vector_db")
    workflow.add_edge("vector_db", "reasoning")
    workflow.add_edge("reasoning", "gap_detection")

    # Conditional edge from gap_detection
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

async def run_deep_research(user_query: str):
    """
    Execute the complete deep research pipeline.

    Args:
        user_query: User's research query

    Returns:
        Dictionary with final answer and metadata
    """
    print("\n" + "="*80)
    print("DEEP RESEARCH AI - INITIATED")
    print("="*80)
    print(f"\nQuery: {user_query}\n")

    total_start = time.time()

    # Build graph
    graph = build_research_graph()

    # Initial state
    initial_state = {
        "user_query": user_query,
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
        "max_reasoning_passes": 3,
        "final_answer": "",
        "sources": [],
        "confidence_score": 0.0,
        "messages": [HumanMessage(content=user_query)],
        "status": "started",
        "errors": [],
        "timestamps": {}
    }

    # Execute graph
    print("Executing research pipeline...\n")

    result = await graph.ainvoke(initial_state)

    total_elapsed = time.time() - total_start

    # Print summary
    print("\n" + "="*80)
    print("RESEARCH COMPLETE")
    print("="*80)
    print(f"\nTotal time: {total_elapsed:.2f}s")
    print(f"Sub-questions: {len(result.get('sub_questions', []))}")
    print(f"Search queries: {len(result.get('search_queries', []))}")
    print(f"Websites searched: {len(result.get('search_results', []))}")
    print(f"Content chunks: {len(result.get('processed_chunks', []))}")
    print(f"Ranked chunks: {len(result.get('ranked_chunks', []))}")
    print(f"Vector DB size: {result.get('vector_db_stats', {}).get('count', 0)}")
    print(f"Reasoning insights: {len(result.get('reasoning_results', []))}")
    print(f"Confidence: {result.get('confidence_score', 0):.2%}")
    print(f"Sources: {len(result.get('sources', []))}")
    print("\n" + "="*80)

    return result

def run_deep_research_sync(user_query: str):
    """Synchronous wrapper for async research execution."""
    import asyncio
    return asyncio.run(run_deep_research(user_query))
