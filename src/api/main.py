"""
OpenResearch - Main Entry Point
Run with: uv run python main.py
"""

import sys
import os

def main():
    print("\n" + "="*80)
    print("🧠 OpenResearch")
    print("="*80)
    print("\nAvailable commands:")
    print("\n1. Start Web Server (Recommended)")
    print("   Command: uv run python src/api/server.py")
    print("   URL: http://localhost:8000")
    print("\n2. Run Research (CLI Mode)")
    print("   Command: uv run python -m src.agent.core.graph")
    print("\n3. View API Documentation")
    print("   URL: http://localhost:8000/docs (after starting server)")
    print("\n" + "="*80)
    
    # Auto-start server if desired
    choice = input("\nStart web server? (y/n): ").strip().lower()
    
    if choice == 'y':
        import subprocess
        subprocess.run([sys.executable, "server.py"])
    else:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
