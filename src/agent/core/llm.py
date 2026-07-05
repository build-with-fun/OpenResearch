import os
import json
import threading
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

def get_llm(model: str = "gemini-3.1-flash-lite", temperature: float = 0.7):
    """Get Gemini LLM instance with configuration."""
    api_key = _get_gemini_api_key()

    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        api_key=api_key,
        max_tokens=8192,
    )
