"""
Deep Research Agent using LangGraph, Google Gemini, and Tavily search.
Implements a full pipeline: Query -> Planner -> Search Generator -> Web Search ->
Scraping -> Chunking -> Ranking -> Reasoning Loop -> Final Answer
"""

from __future__ import annotations

import sys
import os
import time
import json
import hashlib
import logging
from typing import TypedDict, Annotated, List, Dict, Any, Optional

# Force UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from typing import Sequence
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Add parent directory to path (fallback for non-editable installs)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from tools.web_scrapper import AdvancedWebScraper
from Agent.embeddings import get_embedding_model
from Agent.vector_db import get_vector_db

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION CONSTANTS
# ============================================================

MAX_SEARCH_QUERIES = 60
MAX_RESULTS_PER_QUERY = 35
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_CHUNKS = 500
MAX_REASONING_QUERIES = 60
VECTOR_DB_QUERY_RESULTS = 30
TOP_INSIGHTS = 100
TOP_SOURCES = 50
GEMINI_API_KEY_COUNT = 8

load_dotenv()

# ============================================================
# STATE DEFINITION
# ============================================================

class ResearchState(TypedDict):
    """State for the deep research agent."""
    # Input
    user_query: str
    
    # Planning phase
    sub_questions: List[str]  # 35 decomposed questions
    
    # Search phase
    search_queries: List[str]  # Generated search queries (120+)
    search_results: List[Dict]  # All search results from Tavily
    
    # Processing phase
    raw_content_chunks: List[str]  # All scraped content chunks
    processed_chunks: List[Dict]  # Chunked and enriched data
    ranked_chunks: List[Dict]  # Ranked and filtered chunks
    
    # Vector DB phase
    embeddings: List[List[float]]  # All embeddings
    vector_db_stats: Dict  # Vector database statistics
    
    # Reasoning phase
    reasoning_queries: List[str]  # 120 reasoning questions for embeddings
    reasoning_results: List[Dict]  # Results from vector DB queries
    reasoning_passes: int  # Current reasoning pass count
    max_reasoning_passes: int  # Maximum reasoning passes
    
    # Output phase
    final_answer: str  # Final comprehensive answer
    sources: List[Dict]  # Source URLs and references
    confidence_score: float  # Confidence in the answer
    
    # Metadata
    messages: Annotated[Sequence[BaseMessage], add_messages]
    status: str  # Current status
    errors: List[str]  # Error messages
    timestamps: Dict  # Timing information


# ============================================================
# LLM INITIALIZATION
# ============================================================

# Module-level API key rotation counter (simple round-robin)
_api_key_index = 0
_api_key_lock = __import__("threading").Lock()


def _get_gemini_api_key() -> str:
    """Get next API key using round-robin rotation (thread-safe)."""
    global _api_key_index
    keys = []
    for i in range(GEMINI_API_KEY_COUNT):
        env_var = "GEMINI_API_KEY" if i == 0 else f"GEMINI_API_KEY_{i}"
        key = os.getenv(env_var)
        if key:
            keys.append(key)

    if not keys:
        raise ValueError(
            "No GEMINI_API_KEY found in environment. "
            "Set GEMINI_API_KEY (and optionally GEMINI_API_KEY_1..7) in your .env file."
        )

    with _api_key_lock:
        key = keys[_api_key_index % len(keys)]
        _api_key_index += 1
    return key


def extract_json_from_response(content: str) -> dict:
    """Extract JSON object from LLM response text."""
    try:
        if "{" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            json_str = content[json_start:json_end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return {}


def get_llm(model: str = "gemini-2.5-flash", temperature: float = 0.7):
    """Get Gemini LLM instance with configuration."""
    api_key = _get_gemini_api_key()

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        max_tokens=8192,
    )


# ============================================================
# NODE FUNCTIONS
# ============================================================

def planner_node(state: ResearchState) -> Dict:
    """
    PLANNER NODE: Decompose user query into 35 sub-questions.
    """
    print("\n" + "="*80)
    print("[PHASE 1] PLANNING - Decomposing query into sub-questions")
    print("="*80)
    
    start_time = time.time()
    
    llm = get_llm()
    
    system_prompt = """You are an expert research planner. Your task is to decompose a user's research query into exactly 35 specific sub-questions that comprehensively cover all aspects of the topic.

Guidelines:
- Generate EXACTLY 35 sub-questions
- Cover different angles: definitions, history, current state, future trends, pros/cons, comparisons
- Make questions specific and answerable
- Include technical, practical, and theoretical aspects
- Ensure questions are diverse and non-overlapping
- Order questions logically from basic to advanced

Return ONLY a JSON object with this structure:
{
  "sub_questions": [
    "question 1",
    "question 2",
    ...
    "question 35"
  ]
}

Do NOT include any other text or explanation."""

    user_query = state["user_query"]
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Decompose this research query into 35 sub-questions: {user_query}")
    ])
    
    # Parse response
    parsed = extract_json_from_response(response.content)
    sub_questions = parsed.get("sub_questions", [])

    # Ensure we have 35 questions
    if len(sub_questions) < 35:
        # Generate fallback questions
        base_questions = [
            f"What is {user_query}?",
            f"How does {user_query} work?",
            f"Why is {user_query} important?",
            f"What are the benefits of {user_query}?",
            f"What are the challenges of {user_query}?",
            f"What is the history of {user_query}?",
            f"What is the current state of {user_query}?",
            f"What is the future of {user_query}?",
            f"Who are the key players in {user_query}?",
            f"What are examples of {user_query}?",
        ]
        sub_questions.extend(base_questions)
        sub_questions = sub_questions[:35]
    
    elapsed = time.time() - start_time

    print(f"[OK] Generated {len(sub_questions)} sub-questions in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["planning"] = elapsed
    return {
        "sub_questions": sub_questions,
        "status": "planning_complete",
        "timestamps": timestamps,
    }


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


def web_search_node(state: ResearchState) -> Dict:
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

    for idx, query in enumerate(search_queries[:max_queries]):
        print(f"\n[{idx+1}/{max_queries}] Searching: {query[:80]}...")
        result = scraper.search_tavily(query, max_results=MAX_RESULTS_PER_QUERY, search_depth="advanced")
        
        if result.get("results"):
            all_results.extend(result["results"])
            total_websites += len(result["results"])
            print(f"  -> Found {len(result['results'])} results")
        
        # Progress update every 10 queries
        if (idx + 1) % 10 == 0:
            print(f"\n  [PROGRESS] {idx+1}/{max_queries} queries completed")
            print(f"  [STATS] Total websites collected: {total_websites}")
    
    elapsed = time.time() - start_time

    print(f"\n[OK] Web search complete: {total_websites} websites in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["web_search"] = elapsed
    return {
        "search_results": all_results,
        "status": "web_search_complete",
        "timestamps": timestamps,
    }


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
    RANKING NODE: Rank and filter chunks based on relevance.
    Uses keyword matching with optional LLM enhancement.
    """
    print("\n" + "="*80)
    print("[PHASE 5] RANKING - Scoring chunk relevance")
    print("="*80)

    start_time = time.time()

    user_query = state["user_query"]
    chunks = state["processed_chunks"]

    print(f"Ranking {len(chunks)} chunks for relevance...\n")

    # Score chunks using keyword relevance matching
    scored_chunks = []
    batch_size = 20

    for batch_start in range(0, len(chunks), batch_size):
        batch_end = min(batch_start + batch_size, len(chunks))
        batch = chunks[batch_start:batch_end]

        print(f"  Scoring batch [{batch_start+1}-{batch_end}/{len(chunks)}]...")

        for chunk in batch:
            content = chunk["content"].lower()
            query_words = user_query.lower().split()

            # Count query word matches
            score = sum(1 for word in query_words if word in content)
            score /= max(len(query_words), 1)

            # Bonus for title match
            if any(word in chunk.get("title", "").lower() for word in query_words):
                score += 0.3

            chunk["relevance_score"] = min(score, 1.0)
            scored_chunks.append(chunk)

    # Sort by relevance score
    scored_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Keep top chunks
    ranked_chunks = scored_chunks[:MAX_CHUNKS]

    elapsed = time.time() - start_time

    print(f"[OK] Ranked chunks: kept top {len(ranked_chunks)} from {len(chunks)} in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["ranking"] = elapsed
    return {
        "ranked_chunks": ranked_chunks,
        "status": "ranking_complete",
        "timestamps": timestamps,
    }


def vector_db_node(state: ResearchState) -> Dict:
    """
    VECTOR DB NODE: Convert ranked chunks to embeddings and store in ChromaDB.
    """
    print("\n" + "="*80)
    print("[PHASE 6] VECTOR DATABASE - Creating embeddings with Ollama")
    print("="*80)
    
    start_time = time.time()
    
    embedding_model = get_embedding_model()
    vector_db = get_vector_db()
    
    # Reset collection for fresh research
    vector_db.reset_collection()
    vector_db.create_collection()
    
    ranked_chunks = state["ranked_chunks"]
    
    print(f"\nCreating embeddings for {len(ranked_chunks)} chunks...")
    
    # Extract content and create embeddings
    contents = [chunk["content"] for chunk in ranked_chunks]
    embeddings = embedding_model.embed_texts(contents)
    
    # Add to vector DB with metadata
    metadatas = []
    for chunk in ranked_chunks:
        metadatas.append({
            "source": chunk.get("source", ""),
            "title": chunk.get("title", ""),
            "query": chunk.get("query", ""),
            "relevance_score": str(chunk.get("relevance_score", 0)),
            "chunk_index": str(chunk.get("chunk_index", 0))
        })
    
    vector_db.batch_add_with_embeddings(contents, embeddings, metadatas)
    
    stats = vector_db.get_collection_stats()
    
    elapsed = time.time() - start_time

    print(f"[OK] Stored {stats['count']} documents in vector DB in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["vector_db"] = elapsed
    return {
        "embeddings": embeddings,
        "vector_db_stats": stats,
        "status": "vector_db_complete",
        "timestamps": timestamps,
    }


def reasoning_loop_node(state: ResearchState) -> Dict:
    """
    REASONING LOOP NODE: Generate 120 reasoning queries and search vector DB.
    """
    print("\n" + "="*80)
    print("[PHASE 7] REASONING LOOP - Deep analysis with vector DB")
    print("="*80)
    
    start_time = time.time()
    
    llm = get_llm()
    embedding_model = get_embedding_model()
    vector_db = get_vector_db()
    
    user_query = state["user_query"]
    sub_questions = state["sub_questions"]
    ranked_chunks = state["ranked_chunks"]
    
    # Generate 60 reasoning queries
    print("\nGenerating 60 reasoning queries...")

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
        HumanMessage(content=f"Generate 60 deep reasoning queries for: {user_query}")
    ])

    # Parse response using shared helper
    parsed = extract_json_from_response(response.content)
    reasoning_queries = parsed.get("reasoning_queries", [])

    # Fallback: replicate sub-questions
    if not reasoning_queries:
        reasoning_queries = sub_questions.copy() * 4

    # Query vector DB with each reasoning query
    print(f"\nQuerying vector DB with {len(reasoning_queries)} reasoning queries...")

    reasoning_results = []
    for idx, query in enumerate(reasoning_queries[:MAX_REASONING_QUERIES]):
        if idx % 5 == 0:
            print(f"  Processing reasoning query [{idx+1}/{MAX_REASONING_QUERIES}]: {query[:60]}...")

        # Get embedding for query
        query_embedding = embedding_model.embed_text(query)

        # Search vector DB
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
                    "reasoning_pass": 1,
                })

    elapsed = time.time() - start_time

    print(f"[OK] Completed reasoning loop: {len(reasoning_results)} insights in {elapsed:.2f}s")

    timestamps = state.get("timestamps", {})
    timestamps["reasoning"] = elapsed
    return {
        "reasoning_queries": reasoning_queries[:MAX_REASONING_QUERIES],
        "reasoning_results": reasoning_results,
        "reasoning_passes": 1,
        "max_reasoning_passes": 3,
        "status": "reasoning_complete",
        "timestamps": timestamps,
    }


def final_answer_node(state: ResearchState) -> Dict:
    """
    FINAL ANSWER NODE: Generate comprehensive final answer with sources.
    """
    print("\n" + "="*80)
    print("[PHASE 8] FINAL ANSWER - Synthesizing comprehensive response")
    print("="*80)
    
    start_time = time.time()
    
    llm = get_llm(temperature=0.7)
    
    user_query = state["user_query"]
    reasoning_results = state["reasoning_results"]
    search_results = state["search_results"]
    
    # Compile key insights from reasoning results
    insights = reasoning_results[:TOP_INSIGHTS * 2]
    insights_text = "\n\n".join([
        f"Insight {i+1} (relevance: {insight.get('similarity', 0):.2f}):\n{insight['content'][:500]}"
        for i, insight in enumerate(insights[:TOP_INSIGHTS])
    ])

    # Collect unique sources
    unique_sources = {}
    for result in search_results:
        url = result.get("url", "")
        if url and url not in unique_sources:
            unique_sources[url] = {
                "url": url,
                "title": result.get("title", ""),
                "snippet": result.get("content", "")[:200],
            }

    sources_list = list(unique_sources.values())[:TOP_SOURCES]
    
    system_prompt = """You are an elite research analyst and subject matter expert. Your task is to synthesize extensive research findings into a comprehensive, well-structured final answer.

Guidelines:
- Provide a thorough, in-depth analysis
- Structure with clear headings and sections
- Include key findings, evidence, and examples
- Address multiple perspectives and counterarguments
- Draw clear conclusions based on evidence
- Cite sources throughout
- Maintain academic rigor and clarity
- Be objective and balanced

Structure your response:
1. Executive Summary
2. Key Findings
3. Detailed Analysis (with subsections)
4. Comparisons and Contrasts
5. Implications and Future Outlook
6. Conclusion
7. Sources Referenced"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""
USER QUERY: {user_query}

RESEARCH INSIGHTS (from {len(reasoning_results)} reasoning queries across {len(search_results)} sources):

{insights_text}

SYNTHESIZE A COMPREHENSIVE FINAL ANSWER:
""")
    ])
    
    final_answer = response.content
    
    # Calculate confidence score based on data quality
    confidence = min(0.95, 0.5 + (len(reasoning_results) / 1000) + (len(sources_list) / 100))
    
    elapsed = time.time() - start_time

    print(f"[OK] Final answer generated in {elapsed:.2f}s")
    print(f"[STATS] Confidence score: {confidence:.2%}")
    print(f"[STATS] Sources referenced: {len(sources_list)}")

    timestamps = state.get("timestamps", {})
    timestamps["final_answer"] = elapsed
    return {
        "final_answer": final_answer,
        "sources": sources_list,
        "confidence_score": confidence,
        "status": "complete",
        "timestamps": timestamps,
    }


# ============================================================
# GRAPH CONSTRUCTION
# ============================================================

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
    workflow.add_node("final_answer", final_answer_node)
    
    # Add edges (sequential flow)
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "query_generator")
    workflow.add_edge("query_generator", "web_search")
    workflow.add_edge("web_search", "chunking")
    workflow.add_edge("chunking", "ranking")
    workflow.add_edge("ranking", "vector_db")
    workflow.add_edge("vector_db", "reasoning")
    workflow.add_edge("reasoning", "final_answer")
    workflow.add_edge("final_answer", END)
    
    return workflow.compile()


# ============================================================
# MAIN EXECUTION
# ============================================================

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


if __name__ == "__main__":
    # Test with sample query
    query = "What are the latest advances in artificial intelligence and their impact on society?"
    result = run_deep_research_sync(query)
    print("\n\nFINAL ANSWER:\n")
    print(result.get("final_answer", "No answer generated"))
