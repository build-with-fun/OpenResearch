import time
import logging
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response, get_depth_profile

logger = logging.getLogger(__name__)


def planner_node(state: ResearchState) -> Dict:
    """PLANNER NODE: Decompose user query into sub-questions based on depth."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)

    # Determine target sub-questions based on depth
    if depth == "quick":
        min_q, max_q = 5, 10
    elif depth == "deep":
        min_q, max_q = 20, 50
    elif depth == "deeper":
        min_q, max_q = 50, 100
    else:
        min_q, max_q = 10, 25

    logger.info("=" * 60)
    logger.info("[PLANNER] Decomposing query [depth=%s, %d-%d questions]", depth, min_q, max_q)
    logger.info("=" * 60)

    start_time = time.time()

    llm = get_llm()

    system_prompt = f"""You are an expert research planner. Your task is to decompose a user's research query into sub-questions that comprehensively cover the topic.

Guidelines:
- Generate between {min_q} and {max_q} specific sub-questions
- Cover different angles: definitions, history, current state, future trends, pros/cons, comparisons
- Make questions specific and answerable
- Ensure questions are diverse and non-overlapping

Return ONLY a JSON object with this structure:
{{
  "sub_questions": [
    "question 1",
    ...
  ],
  "depth_reasoning": "Brief explanation of why these questions were chosen"
}}

Do NOT include any other text or explanation."""

    user_query = state["user_query"]

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Decompose this research query into {min_q}-{max_q} sub-questions: {user_query}")
    ])

    parsed = extract_json_from_response(response.content)
    sub_questions = parsed.get("sub_questions", [])

    if not sub_questions:
        sub_questions = [
            f"What is {user_query}?",
            f"How does {user_query} work?",
            f"Why is {user_query} important?",
            f"What are the benefits of {user_query}?",
            f"What are the challenges of {user_query}?",
            f"What is the current state of {user_query}?",
            f"What is the future of {user_query}?",
        ]

    elapsed = time.time() - start_time

    logger.info("[PLANNER] Generated %d sub-questions in %.2fs", len(sub_questions), elapsed)

    timestamps = state.get("timestamps", {})
    timestamps["planning"] = elapsed
    return {
        "sub_questions": sub_questions,
        "status": "planning_complete",
        "timestamps": timestamps,
    }
