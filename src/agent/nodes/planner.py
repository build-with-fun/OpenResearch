import time
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, extract_json_from_response

def planner_node(state: ResearchState) -> Dict:
    """
    PLANNER NODE: Decompose user query into an optimal number of sub-questions.
    """
    print("\n" + "="*80)
    print("[PHASE 1] PLANNING - Decomposing query into sub-questions")
    print("="*80)

    start_time = time.time()

    llm = get_llm()

    system_prompt = """You are an expert research planner. Your task is to decompose a user's research query into a set of specific sub-questions that comprehensively cover all aspects of the topic.

Guidelines:
- Determine the optimal number of sub-questions (typically between 10 and 50) based on the complexity and breadth of the query.
- For simple queries, 10-15 questions are sufficient. For extremely complex or broad topics, aim for 30-50.
- Cover different angles: definitions, history, current state, future trends, pros/cons, comparisons.
- Make questions specific and answerable.
- Include technical, practical, and theoretical aspects.
- Ensure questions are diverse and non-overlapping.
- Order questions logically from basic to advanced.

Return ONLY a JSON object with this structure:
{
  "sub_questions": [
    "question 1",
    "question 2",
    ...
  ],
  "depth_reasoning": "Brief explanation of why this many questions were chosen"
}

Do NOT include any other text or explanation."""

    user_query = state["user_query"]

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Decompose this research query into an optimal number of sub-questions: {user_query}")
    ])

    # Parse response
    parsed = extract_json_from_response(response.content)
    sub_questions = parsed.get("sub_questions", [])

    # Fallback: generate some basic questions if LLM failed
    if not sub_questions:
        sub_questions = [
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

    elapsed = time.time() - start_time

    print(f"[OK] Generated {len(sub_questions)} sub-questions in {elapsed:.2f}s")
    if "depth_reasoning" in parsed:
        print(f"Reasoning: {parsed['depth_reasoning']}")

    timestamps = state.get("timestamps", {})
    timestamps["planning"] = elapsed
    return {
        "sub_questions": sub_questions,
        "status": "planning_complete",
        "timestamps": timestamps,
    }
