"""
FastAPI backend server for OpenResearch.
Serves the web UI and provides API endpoints for research.
"""

import os
import time
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# APP
# ============================================================

app = FastAPI(title="OpenResearch", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STORAGE
# ============================================================

research_tasks: Dict[str, Dict[str, Any]] = {}

# ============================================================
# MODELS
# ============================================================


class ResearchRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


# ============================================================
# STATIC FILES
# ============================================================

WEB_DIR = Path(__file__).parent.parent.parent / "web"

# ============================================================
# API ROUTES (defined FIRST, before any catch-all)
# ============================================================


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "service": "OpenResearch",
        "active_tasks": len(research_tasks),
    }


@app.post("/api/research")
async def start_research(req: ResearchRequest):
    rid = str(uuid.uuid4())
    research_tasks[rid] = {
        "status": "started",
        "query": req.query,
        "progress": 0,
        "current_step": "initializing",
        "final_answer": None,
        "sources": [],
        "confidence_score": 0.0,
        "timestamps": {},
        "search_results": [],
        "error": None,
        "start_time": time.time(),
    }

    async def _run() -> None:
        try:
            from src.agent.core.graph import run_deep_research

            result = await run_deep_research(req.query)
            t = research_tasks[rid]
            t["status"] = "complete"
            t["current_step"] = "final_answer"
            t["progress"] = 100
            t["final_answer"] = result.get("final_answer", "")
            t["sources"] = result.get("sources", [])
            t["confidence_score"] = result.get("confidence_score", 0.0)
            t["timestamps"] = result.get("timestamps", {})
            t["search_results"] = result.get("search_results", [])[:100]
        except Exception as e:
            logger.exception("Research failed for %s", rid)
            if rid in research_tasks:
                research_tasks[rid]["status"] = "error"
                research_tasks[rid]["error"] = str(e)

    asyncio.create_task(_run())
    logger.info("Started research %s for query: %s", rid, req.query[:80])
    return {"research_id": rid, "status": "started", "message": "Research started"}


@app.get("/api/research/{rid}/status")
async def get_status(rid: str):
    if rid not in research_tasks:
        raise HTTPException(404, "Research task not found")
    t = research_tasks[rid]
    return {
        "status": t["status"],
        "progress": t["progress"],
        "current_step": t["current_step"],
        "final_answer": t["final_answer"],
        "sources": t["sources"],
        "confidence_score": t["confidence_score"],
        "timestamps": t["timestamps"],
        "search_results": t["search_results"],
        "error": t["error"],
    }


@app.get("/api/research/{rid}")
async def get_result(rid: str):
    if rid not in research_tasks:
        raise HTTPException(404, "Research task not found")
    t = research_tasks[rid]
    if t["status"] != "complete":
        raise HTTPException(400, f"Not complete: {t['status']}")
    return {
        "research_id": rid,
        "query": t["query"],
        "final_answer": t["final_answer"],
        "sources": t["sources"],
        "confidence_score": t["confidence_score"],
        "timestamps": t["timestamps"],
        "total_time": time.time() - t["start_time"],
    }


# ============================================================
# STATIC ROUTES (must be AFTER API routes)
# ============================================================

# StaticFiles with html=True serves index.html at "/" and handles all other files
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")


# ============================================================
# RUN
# ============================================================


def main():
    print("\n" + "=" * 60)
    print("  DEEP RESEARCH AI")
    print("  http://localhost:8000")
    print("=" * 60 + "\n")
    import uvicorn

    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
