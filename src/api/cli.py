"""
CLI entry point for OpenResearch.
Run research directly in the terminal without the web UI.

Usage:
    uv run python cli.py
    uv run python cli.py "Your research query here"
"""

import sys
import asyncio
import json
from src.agent.core.graph import run_deep_research


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print("\n" + "=" * 60)
        print("  🧠  OpenResearch — CLI Mode")
        print("=" * 60)
        query = input("\nEnter your research query: ").strip()

    if not query:
        print("No query provided. Exiting.")
        sys.exit(1)

    print(f"\nQuery: {query}\n")
    print("Starting research pipeline...")

    try:
        result = asyncio.run(run_deep_research(query))

        # Print final answer
        print("\n\n" + "=" * 60)
        print("  FINAL ANSWER")
        print("=" * 60 + "\n")
        print(result.get("final_answer", "No answer generated."))

        # Print sources
        sources = result.get("sources", [])
        if sources:
            print(f"\n\n{'=' * 60}")
            print(f"  SOURCES ({len(sources)})")
            print("=" * 60 + "\n")
            for i, src in enumerate(sources, 1):
                print(f"{i}. {src.get('title', 'Untitled')}")
                print(f"   {src.get('url', 'No URL')}")
                print()

        # Print stats
        print(f"{'=' * 60}")
        print("  STATS")
        print("=" * 60)
        print(f"  Confidence:  {result.get('confidence_score', 0):.1%}")
        print(f"  Sources:     {len(sources)}")
        ts = result.get("timestamps", {})
        total = sum(ts.values())
        print(f"  Total time:  {total:.1f}s")
        for phase, dur in ts.items():
            print(f"    {phase}: {dur:.1f}s")
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
