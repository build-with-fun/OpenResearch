"""
System verification script for OpenResearch.
Tests all components without running full research.
"""

import sys
import os

def test_imports():
    """Test all module imports."""
    print("\n" + "="*80)
    print("Search TESTING IMPORTS")
    print("="*80)

    try:
        from src.agent.core.graph import build_research_graph
        from src.agent.core.state import ResearchState
        print("PASS Agent core modules imported")

        from src.agent.tools.scraper import AdvancedWebScraper
        print("PASS Web scraper imported")

        from src.database.embeddings import get_embedding_model
        print("PASS Embeddings module imported")

        from src.database.vector_db import get_vector_db
        print("PASS Vector DB module imported")

        from src.api.server import app
        print("PASS Server app imported")

        return True
    except Exception as e:
        print(f"\nFAIL Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_environment():
    """Test environment variables."""
    print("\n" + "="*80)
    print("Key TESTING ENVIRONMENT")
    print("="*80)

    from dotenv import load_dotenv
    load_dotenv()

    gemini_keys = sum(1 for k, v in os.environ.items() if k.startswith('GEMINI_API_KEY') and v)
    tavily_key = os.getenv('TAVILY_API_KEY')

    print(f"\nGemini API Keys: {gemini_keys} configured")
    print(f"Tavily API Key: {'PASS' if tavily_key else 'FAIL'}")

    if gemini_keys == 0:
        print("\nWarning  Warning: No Gemini API keys found in .env")
    if not tavily_key:
        print("\nWarning  Warning: No Tavily API key found in .env")

    return gemini_keys > 0 and bool(tavily_key)

def test_graph_construction():
    """Test LangGraph graph construction."""
    print("\n" + "="*80)
    print("Link TESTING GRAPH CONSTRUCTION")
    print("="*80)

    try:
        from src.agent.core.graph import build_research_graph
        graph = build_research_graph()
        print("PASS LangGraph graph constructed successfully")
        print(f"  Nodes: {len(graph.get_graph().nodes)}")
        return True
    except Exception as e:
        print(f"\nFAIL Graph construction failed: {e}")
        return False

def test_scraper():
    """Test web scraper initialization."""
    print("\n" + "="*80)
    print("Web TESTING WEB SCRAPER")
    print("="*80)

    try:
        from src.agent.tools.scraper import AdvancedWebScraper
        scraper = AdvancedWebScraper()
        print("PASS Web scraper initialized")
        print(f"  Tavily client: {'PASS' if scraper.tavily_client else 'FAIL'}")
        return True
    except Exception as e:
        print(f"\nFAIL Scraper initialization failed: {e}")
        return False

def test_vector_db():
    """Test vector database initialization."""
    print("\n" + "="*80)
    print("Brain TESTING VECTOR DATABASE")
    print("="*80)

    try:
        from src.database.vector_db import get_vector_db
        db = get_vector_db()
        print("PASS Vector database initialized")
        print(f"  Client: {'PASS' if db.client else 'FAIL'}")
        return True
    except Exception as e:
        print(f"\nFAIL Vector DB initialization failed: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("Brain DEEP RESEARCH AI - SYSTEM VERIFICATION")
    print("="*80)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_environment()))
    results.append(("Graph", test_graph_construction()))
    results.append(("Scraper", test_scraper()))
    results.append(("Vector DB", test_vector_db()))

    # Summary
    print("\n" + "="*80)
    print("Stats VERIFICATION SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASS PASS" if result else "FAIL FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\nSucceed All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Pull embedding model: ollama pull qwen3-embeddings:8b")
        print("3. Start server: uv run python src/api/server.py")
        print("4. Open browser: http://localhost:8000")
    else:
        print("\nWarning  Some tests failed. Please check the errors above.")
        print("Common fixes:")
        print("- Install dependencies: uv sync")
        print("- Check .env file for API keys")
        print("- Install Ollama: https://ollama.ai")

    print("\n" + "="*80)

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
