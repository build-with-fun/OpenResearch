import time
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, TOP_INSIGHTS, TOP_SOURCES

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
