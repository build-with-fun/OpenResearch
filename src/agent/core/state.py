from typing import TypedDict, Annotated, List, Dict, Any, Optional, Sequence
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ResearchState(TypedDict):
    """State for the deep research agent."""
    # Input
    user_query: str
    research_depth: str  # "quick", "standard", or "deep"

    # Planning phase
    sub_questions: List[str]  # Decomposed questions

    # Search phase
    search_queries: List[str]  # Generated search queries
    search_results: List[Dict]  # All search results from Tavily

    # Processing phase
    raw_content_chunks: List[str]  # All scraped content chunks
    processed_chunks: List[Dict]  # Chunked and enriched data
    ranked_chunks: List[Dict]  # Ranked and filtered chunks

    # Vector DB phase
    embeddings: List[List[float]]  # All embeddings
    vector_db_stats: Dict  # Vector database statistics

    # Reasoning phase
    reasoning_queries: List[str]  # Reasoning questions for embeddings
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
