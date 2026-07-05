"""
Starter script for OpenResearch.
Launches the FastAPI server and opens the web UI in a browser.

Usage:
    uv run python starter.py
    uv run python starter.py --port 8001
    uv run python starter.py --no-browser
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Start OpenResearch server and open the web UI.")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open the browser automatically")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"], help="Uvicorn log level")
    args = parser.parse_args()

    url = f"http://localhost:{args.port}"

    # Banner
    print("\n" + "=" * 60)
    print("  🧠  OpenResearch")
    print(f"  Server → {url}")
    print(f"  API docs → {url}/docs")
    print("=" * 60 + "\n")

    # Open browser in a short delay so the server has time to start
    if not args.no_browser:
        def _open_browser() -> None:
            time.sleep(1.5)
            webbrowser.open(url)

        import threading
        threading.Thread(target=_open_browser, daemon=True).start()

    # Start uvicorn server (blocks until stopped)
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api.server:app",
        "--host", args.host,
        "--port", str(args.port),
        "--log-level", args.log_level,
    ]

    print(f"Starting server: {' '.join(cmd)}\n")
    print("Press Ctrl+C to stop.\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server exited with error (code {e.returncode})")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
