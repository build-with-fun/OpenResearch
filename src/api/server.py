"""
FastAPI backend server for OpenResearch.
Serves the web UI, REST API, SSE streaming, and PDF export.
"""

import os
import re
import time
import json
import uuid
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from sse_starlette.sse import EventSourceResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("openresearch")

# ============================================================
# EVENT BUS — real-time pipeline events for SSE
# ============================================================

class EventBus:
    """Simple pub/sub for pipeline events. Each research task has its own event queue."""

    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._lock = threading.Lock()

    def create_queue(self, rid: str):
        with self._lock:
            self._queues[rid] = asyncio.Queue(maxsize=500)

    def get_queue(self, rid: str) -> Optional[asyncio.Queue]:
        return self._queues.get(rid)

    async def publish(self, rid: str, event_type: str, data: dict):
        queue = self.get_queue(rid)
        if queue:
            try:
                await queue.put({"type": event_type, "data": data, "timestamp": time.time()})
            except asyncio.QueueFull:
                pass

    def remove_queue(self, rid: str):
        with self._lock:
            self._queues.pop(rid, None)


event_bus = EventBus()

# ============================================================
# APP
# ============================================================

APP_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — start background cleanup task."""
    cleanup_task = asyncio.create_task(_periodic_cleanup())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="OpenResearch", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# STORAGE (in-memory task store with auto-cleanup)
# ============================================================

research_tasks: Dict[str, Dict[str, Any]] = {}
_tasks_lock = threading.Lock()
TASK_TTL = 3600  # 1 hour


def _store_task(rid: str, task: dict):
    with _tasks_lock:
        research_tasks[rid] = task


def _get_task(rid: str) -> Optional[dict]:
    with _tasks_lock:
        return research_tasks.get(rid)


def _delete_task(rid: str):
    with _tasks_lock:
        research_tasks.pop(rid, None)


async def _periodic_cleanup():
    """Background task to clean up expired research tasks every 5 minutes."""
    while True:
        await asyncio.sleep(300)
        now = time.time()
        expired = []
        with _tasks_lock:
            for rid, task in research_tasks.items():
                if task.get("status") in ("complete", "error", "cancelled"):
                    start = task.get("start_time", 0)
                    if now - start > TASK_TTL:
                        expired.append(rid)
            for rid in expired:
                del research_tasks[rid]
        if expired:
            logger.info("Cleaned up %d expired tasks", len(expired))

# ============================================================
# MODELS
# ============================================================

VALID_DEPTHS = {"quick", "standard", "deep", "deeper"}


class ResearchRequest(BaseModel):
    query: str
    depth: str = "standard"

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Query must be at least 3 characters")
        if len(v) > 2000:
            raise ValueError("Query must be under 2000 characters")
        return v

    @field_validator("depth")
    @classmethod
    def depth_valid(cls, v: str) -> str:
        if v not in VALID_DEPTHS:
            raise ValueError(f"Depth must be one of: {', '.join(sorted(VALID_DEPTHS))}")
        return v


# ============================================================
# STATIC FILES
# ============================================================

WEB_DIR = Path(__file__).parent.parent.parent / "web"

# ============================================================
# API ROUTES
# ============================================================


@app.get("/api/health")
async def health():
    active = 0
    with _tasks_lock:
        for t in research_tasks.values():
            if t.get("status") in ("started", "processing"):
                active += 1
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "OpenResearch",
        "uptime": time.time() - APP_START_TIME,
        "active_tasks": active,
        "total_tasks": len(research_tasks),
    }


@app.post("/api/research")
async def start_research(req: ResearchRequest):
    """Start a new research task with the given query and depth."""
    rid = str(uuid.uuid4())

    task = {
        "status": "started",
        "query": req.query,
        "depth": req.depth,
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
    _store_task(rid, task)
    event_bus.create_queue(rid)

    async def _run() -> None:
        try:
            from src.agent.core.graph import run_deep_research, set_progress_callback

            # Set progress callback to forward events to SSE stream
            async def _progress(step: str, data: dict):
                await event_bus.publish(rid, step, data)

            set_progress_callback(_progress)

            # Publish initial event
            await event_bus.publish(rid, "status", {
                "status": "started",
                "current_step": "initializing",
                "progress": 0,
                "message": "Initializing research pipeline...",
            })

            # Run research with depth parameter
            result = await run_deep_research(req.query, req.depth)

            # Update task store
            with _tasks_lock:
                t = research_tasks.get(rid)
                if t is None:
                    return
                t["status"] = "complete"
                t["current_step"] = "final_answer"
                t["progress"] = 100
                t["final_answer"] = result.get("final_answer", "")
                t["sources"] = result.get("sources", [])
                t["confidence_score"] = result.get("confidence_score", 0.0)
                t["timestamps"] = result.get("timestamps", {})
                t["search_results"] = result.get("search_results", [])[:100]

            # Publish completion event
            await event_bus.publish(rid, "complete", {
                "status": "complete",
                "progress": 100,
                "message": "Research complete!",
            })

            # Clear the global callback
            set_progress_callback(None)

        except Exception as e:
            logger.exception("Research failed for %s", rid)
            from src.agent.core.graph import set_progress_callback
            set_progress_callback(None)
            with _tasks_lock:
                t = research_tasks.get(rid)
                if t:
                    t["status"] = "error"
                    t["error"] = str(e)
            await event_bus.publish(rid, "error", {
                "status": "error",
                "error": str(e),
            })
            event_bus.remove_queue(rid)

    asyncio.create_task(_run())
    logger.info("Started research %s [depth=%s]: %s", rid, req.depth, req.query[:80])
    return {"research_id": rid, "status": "started", "depth": req.depth, "message": "Research started"}


@app.post("/api/research/{rid}/cancel")
async def cancel_research(rid: str):
    """Cancel a running research task."""
    task = _get_task(rid)
    if not task:
        raise HTTPException(404, "Research task not found")
    if task["status"] not in ("started", "processing"):
        raise HTTPException(400, f"Cannot cancel task with status: {task['status']}")

    task["status"] = "cancelled"
    task["error"] = "Cancelled by user"
    await event_bus.publish(rid, "cancelled", {"status": "cancelled", "message": "Research cancelled by user"})
    event_bus.remove_queue(rid)
    return {"status": "cancelled", "message": "Research cancelled"}


@app.get("/api/research/{rid}/stream")
async def stream_research(rid: str):
    """SSE stream for real-time research progress updates."""
    task = _get_task(rid)
    if not task:
        raise HTTPException(404, "Research task not found")

    queue = event_bus.get_queue(rid)
    if queue is None:
        raise HTTPException(400, "No event stream available for this task")

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # Send initial state
            yield {
                "event": "status",
                "data": json.dumps({
                    "status": task["status"],
                    "current_step": task.get("current_step", "initializing"),
                    "progress": task.get("progress", 0),
                }),
            }

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=2.0)
                    event_type = event["type"]
                    event_data = event["data"]
                    yield {
                        "event": event_type,
                        "data": json.dumps(event_data),
                    }

                    # If terminal event, remove queue and stop
                    if event_type in ("complete", "error", "cancelled"):
                        event_bus.remove_queue(rid)
                        return

                except asyncio.TimeoutError:
                    # Check if task is done but no event was published
                    current = _get_task(rid)
                    if current and current.get("status") in ("complete", "error", "cancelled"):
                        if current["status"] == "complete":
                            yield {
                                "event": "complete",
                                "data": json.dumps({
                                    "status": "complete",
                                    "progress": 100,
                                }),
                            }
                        return
                    # Send heartbeat to keep connection alive
                    yield {"event": "heartbeat", "data": ""}

        except asyncio.CancelledError:
            event_bus.remove_queue(rid)
            raise

    return EventSourceResponse(event_generator())


@app.get("/api/research/{rid}/status")
async def get_status(rid: str):
    """Get current research progress/status."""
    task = _get_task(rid)
    if not task:
        raise HTTPException(404, "Research task not found")
    return {
        "status": task["status"],
        "depth": task.get("depth", "standard"),
        "progress": task["progress"],
        "current_step": task["current_step"],
        "final_answer": task["final_answer"],
        "sources": task["sources"],
        "confidence_score": task["confidence_score"],
        "timestamps": task["timestamps"],
        "search_results": task["search_results"],
        "error": task["error"],
    }


@app.get("/api/research/{rid}")
async def get_result(rid: str):
    """Get completed research result."""
    task = _get_task(rid)
    if not task:
        raise HTTPException(404, "Research task not found")
    if task["status"] != "complete":
        raise HTTPException(400, f"Not complete: {task['status']}")
    return {
        "research_id": rid,
        "query": task["query"],
        "depth": task.get("depth", "standard"),
        "final_answer": task["final_answer"],
        "sources": task["sources"],
        "confidence_score": task["confidence_score"],
        "timestamps": task["timestamps"],
        "total_time": time.time() - task["start_time"],
    }


@app.get("/api/research/{rid}/export/markdown")
async def export_markdown(rid: str):
    """Export research result as Markdown."""
    task = _get_task(rid)
    if not task:
        raise HTTPException(404, "Research task not found")
    if task["status"] != "complete":
        raise HTTPException(400, f"Not complete: {task['status']}")

    answer = task.get("final_answer", "")
    sources = task.get("sources", [])
    confidence = task.get("confidence_score", 0)

    md = f"# Research: {task['query']}\n\n"
    md += f"**Depth**: {task.get('depth', 'standard')}  \n"
    md += f"**Confidence**: {confidence:.1%}  \n\n"
    md += "---\n\n"
    md += answer
    md += "\n\n---\n\n"
    md += f"## Sources ({len(sources)})\n\n"
    for i, src in enumerate(sources, 1):
        md += f"{i}. **{src.get('title', 'Untitled')}**  \n"
        md += f"   {src.get('url', '#')}  \n"

    return Response(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="research-{rid[:8]}.md"',
        },
    )


@app.get("/api/research/{rid}/export/pdf")
async def export_pdf(rid: str):
    """Export research result as PDF."""
    task = _get_task(rid)
    if not task:
        raise HTTPException(404, "Research task not found")
    if task["status"] != "complete":
        raise HTTPException(400, f"Not complete: {task['status']}")

    answer = task.get("final_answer", "")
    sources = task.get("sources", [])

    try:
        from weasyprint import HTML
    except ImportError:
        raise HTTPException(500, "PDF export is not available (weasyprint not installed)")

    # Create HTML with embedded styles
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Inter', -apple-system, sans-serif; font-size: 12pt; line-height: 1.6; color: #1a1a1a; max-width: 800px; margin: 0 auto; padding: 2em; }}
  h1 {{ font-size: 1.6em; margin-bottom: 0.3em; }}
  h2 {{ font-size: 1.3em; margin-top: 1.5em; }}
  h3 {{ font-size: 1.1em; margin-top: 1.2em; }}
  p {{ margin-bottom: 0.8em; }}
  .meta {{ color: #666; font-size: 0.9em; margin-bottom: 2em; }}
  hr {{ border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }}
  .source {{ margin-bottom: 0.5em; }}
  .source a {{ color: #0066cc; }}
  @media print {{ body {{ padding: 0; }} }}
</style>
</head>
<body>
<h1>Research: {html_escape(task['query'])}</h1>
<div class="meta">
  Depth: {task.get('depth', 'standard')} | Confidence: {task.get('confidence_score', 0):.1%}
</div>
<hr>
<div class="content">
{md_to_html(answer)}
</div>
<hr>
<h2>Sources ({len(sources)})</h2>
{''.join(f'<div class="source">{i+1}. <strong>{html_escape(src.get("title", "Untitled"))}</strong><br><a href="{html_escape(src.get("url", "#"))}">{html_escape(src.get("url", "#"))}</a></div>' for i, src in enumerate(sources))}
</body>
</html>"""

    pdf_bytes = HTML(string=html).write_pdf()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="research-{rid[:8]}.pdf"',
        },
    )


# ============================================================
# RATE LIMITING (simple in-memory)
# ============================================================

_rate_limit_store: Dict[str, list] = {}
_rate_limit_lock = threading.Lock()
RATE_LIMIT = 20  # requests per window
RATE_WINDOW = 60  # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        with _rate_limit_lock:
            timestamps = _rate_limit_store.get(client_ip, [])
            timestamps = [t for t in timestamps if now - t < RATE_WINDOW]
            if len(timestamps) >= RATE_LIMIT:
                return Response(
                    content=json.dumps({"error": "Rate limit exceeded. Try again later."}),
                    status_code=429,
                    media_type="application/json",
                )
            timestamps.append(now)
            _rate_limit_store[client_ip] = timestamps

    return await call_next(request)


# ============================================================
# STATIC ROUTES (after API routes)
# ============================================================

if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="static")


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def html_escape(text: str) -> str:
    """Escape HTML entities."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def md_to_html(md: str) -> str:
    """Simple Markdown to HTML conversion for PDF export."""
    html = html_escape(md)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html)
    html = re.sub(r'\n\n', r'</p><p>', html)
    html = '<p>' + html + '</p>'
    html = html.replace('<p></p>', '')
    return html


# ============================================================
# RUN
# ============================================================


def main():
    print("\n" + "=" * 60)
    print("  OPENRESEARCH v2.0")
    print("  http://localhost:8000")
    print("=" * 60 + "\n")
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
