# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

- **Setup**: `uv sync`
- **Embedding Model Setup**: `ollama pull qwen3-embeddings:8b`
- **Run Server**: `uv run python server.py` (Starts FastAPI server at http://localhost:8000)
- **Run Research (CLI)**: `uv run python -m Agent.agent`
- **Run System Tests**: `uv run python test_system.py`

## Architecture & Structure

### High-Level Pipeline
The system implements a multi-stage deep research pipeline orchestrated by **LangGraph**:
1. **Planner**: Decomposes user query into sub-questions.
2. **Query Generation**: Creates optimized search queries.
3. **Web Search**: Uses Tavily API to fetch results.
4. **Scraping**: Extracts clean content from sources.
5. **Chunking**: Splits content into manageable segments.
6. **Ranking**: Scores and filters chunks by relevance.
7. **Vector DB**: Stores embeddings using Ollama (`qwen3-embeddings:8b`) and ChromaDB.
8. **Reasoning Loop**: Performs deep analysis by querying the vector database.
9. **Final Answer**: Synthesizes the final comprehensive response with citations.

### Key Components
- `Agent/agent.py`: Core LangGraph implementation containing the state and all pipeline nodes.
- `Agent/embeddings.py`: Wrapper for Ollama embedding model.
- `Agent/vector_db.py`: Interface for ChromaDB persistent storage.
- `tools/web_scrapper.py`: Logic for advanced web scraping and content extraction.
- `server.py`: FastAPI backend providing endpoints for the Web UI and API access.
- `web/`: Vanilla HTML/CSS/JS frontend for real-time research tracking.

### Tech Stack
- **LLM**: Google Gemini 2.5 Flash
- **Orchestration**: LangGraph
- **Search**: Tavily API
- **Embeddings**: Ollama
- **Vector DB**: ChromaDB
- **Backend**: FastAPI / Uvicorn
- **Frontend**: HTML, CSS, JavaScript
