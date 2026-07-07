import time
import logging
from typing import Dict
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.core.state import ResearchState
from src.agent.core.llm import get_llm, get_depth_profile

logger = logging.getLogger(__name__)


def final_answer_node(state: ResearchState) -> Dict:
    """FINAL ANSWER NODE: Generate comprehensive final answer with sources."""
    depth = state.get("research_depth", "standard")
    profile = get_depth_profile(depth)
    top_insights = profile["top_insights"]
    top_sources = profile["top_sources"]

    logger.info("=" * 60)
    logger.info("[SYNTHESIS] Generating final answer [depth=%s]", depth)
    logger.info("=" * 60)

    start_time = time.time()

    llm = get_llm(temperature=0.7)

    user_query = state["user_query"]
    reasoning_results = state["reasoning_results"]
    search_results = state["search_results"]

    insights = reasoning_results[:top_insights * 2]
    insights_text = "\n\n".join([
        f"Insight {i+1} (relevance: {insight.get('similarity', 0):.2f}):\n{insight['content'][:500]}"
        for i, insight in enumerate(insights[:top_insights])
    ])

    unique_sources = {}
    for result in search_results:
        url = result.get("url", "")
        if url and url not in unique_sources:
            unique_sources[url] = {
                "url": url,
                "title": result.get("title", ""),
                "snippet": result.get("content", "")[:200],
            }

    sources_list = list(unique_sources.values())[:top_sources]

    system_prompt = """You are an elite research analyst and subject matter expert. Synthesize extensive research findings into a comprehensive, well-structured final answer.

Guidelines:
- Provide a thorough, in-depth analysis
- Structure with clear headings and sections
- Include key findings, evidence, and examples
- Address multiple perspectives and counterarguments
- Draw clear conclusions based on evidence
- Cite sources using [citation:X] format matching the source indices below
- Maintain academic rigor and clarity

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

SOURCES:
{chr(10).join([f"[{i+1}] {s['title']} - {s['url']}" for i, s in enumerate(sources_list)])}

SYNTHESIZE A COMPREHENSIVE FINAL ANSWER:
""")
    ])

    final_answer = response.content

    confidence = min(0.95, 0.5 + (len(reasoning_results) / 1000) + (len(sources_list) / 100))

    elapsed = time.time() - start_time

    logger.info("[SYNTHESIS] Final answer generated in %.2fs", elapsed)
    logger.info("[STATS] Confidence: %.2f%% | Sources: %d", confidence * 100, len(sources_list))

    timestamps = state.get("timestamps", {})
    timestamps["final_answer"] = elapsed
    return {
        "final_answer": final_answer,
        "sources": sources_list,
        "confidence_score": confidence,
        "status": "complete",
        "timestamps": timestamps,
    }
