import os
import re
import json
import threading
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

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

# Research depth profiles
DEPTH_PROFILES = {
    "quick": {
        "max_search_queries": 15,
        "max_results_per_query": 10,
        "chunk_size": 2000,
        "chunk_overlap": 100,
        "max_chunks": 100,
        "max_reasoning_queries": 20,
        "vector_db_query_results": 15,
        "top_insights": 30,
        "top_sources": 20,
        "max_reasoning_passes": 1,
        "label": "Quick",
        "description": "Fast overview (~4 sources)",
    },
    "standard": {
        "max_search_queries": 60,
        "max_results_per_query": 35,
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "max_chunks": 500,
        "max_reasoning_queries": 60,
        "vector_db_query_results": 30,
        "top_insights": 100,
        "top_sources": 50,
        "max_reasoning_passes": 3,
        "label": "Standard",
        "description": "Balanced depth (~15 sources)",
    },
    "deep": {
        "max_search_queries": 120,
        "max_results_per_query": 50,
        "chunk_size": 500,
        "chunk_overlap": 100,
        "max_chunks": 1000,
        "max_reasoning_queries": 100,
        "vector_db_query_results": 50,
        "top_insights": 200,
        "top_sources": 100,
        "max_reasoning_passes": 5,
        "label": "Deep",
        "description": "Maximum thoroughness (~30 sources)",
    },
    "deeper": {
        "max_search_queries": 120,
        "max_results_per_query": 50,
        "chunk_size": 250,
        "chunk_overlap": 50,
        "max_chunks": 9999,
        "max_reasoning_queries": 300,
        "vector_db_query_results": 100,
        "top_insights": 500,
        "top_sources": 300,
        "max_reasoning_passes": 10,
        "label": "Deeper",
        "description": "Extreme depth — uses full potential (~100+ sources)",
    },
}


def get_depth_profile(depth: str = "standard") -> dict:
    """Get the config profile for a given research depth."""
    profile = DEPTH_PROFILES.get(depth)
    if not profile:
        profile = DEPTH_PROFILES["standard"]
    return profile


# Module-level API key rotation counter (simple round-robin)
_api_key_index = 0
_api_key_lock = threading.Lock()


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


def extract_json_from_response(content) -> dict:
    """Extract JSON object from LLM response text.

    Handles markdown code fences, nested braces, trailing commas,
    and truncated responses gracefully.
    """
    if not content:
        return {}

    if isinstance(content, list):
        content = "".join(
            part.text if hasattr(part, "text") else str(part)
            for part in content
        )

    # Remove markdown code fences (```json ... ```)
    cleaned = re.sub(r'```(?:json)?\s*', '', content)

    # Try to find JSON object boundaries
    brace_depth = 0
    json_start = -1
    json_end = -1

    for i, ch in enumerate(cleaned):
        if ch == '{':
            if brace_depth == 0:
                json_start = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and json_start >= 0:
                json_end = i + 1
                break

    if json_start < 0 or json_end <= json_start:
        # Fallback: try to find any {...} block
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            json_str = match.group()
        else:
            return {}
    else:
        json_str = cleaned[json_start:json_end]

    # Clean up common issues
    json_str = re.sub(r',\s*}', '}', json_str)  # trailing commas
    json_str = re.sub(r',\s*]', ']', json_str)   # trailing commas in arrays

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Final fallback: try lenient parsing with eval-style approach
    try:
        # Replace single quotes with double quotes for JSON-like strings
        relaxed = re.sub(r"(?<!\\)'", '"', json_str)
        relaxed = re.sub(r'"\s*:\s*"', '": "', relaxed)
        return json.loads(relaxed)
    except (json.JSONDecodeError, ValueError):
        return {}


def get_llm(model: str = "gemini-3.1-flash-lite", temperature: float = 0.7):
    """Get Gemini LLM instance with configuration."""
    api_key = _get_gemini_api_key()

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        max_tokens=8192,
    )
