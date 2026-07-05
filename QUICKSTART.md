# 🚀 Quick Start Guide - OpenResearch

## ✅ Prerequisites Checklist

Before starting, make sure you have:

- [x] Python 3.13+ (installed via uv)
- [x] Dependencies installed (`uv sync`)
- [ ] Ollama installed and running
- [ ] Qwen3 embeddings model downloaded
- [ ] API keys configured in `.env`

## 📋 Step-by-Step Setup

### Step 1: Install Ollama

1. Download from: https://ollama.ai
2. Install and run Ollama
3. Verify it's running (should be on http://localhost:11434)

### Step 2: Download Embedding Model

Open a new terminal and run:
```bash
ollama pull qwen3-embeddings:8b
```

This will download the ~8B parameter embedding model (may take a few minutes).

### Step 3: Verify API Keys

Your `.env` file should have:
- ✅ `GEMINI_API_KEY` (already configured - 8 keys)
- ✅ `TAVILY_API_KEY` (already configured)

### Step 4: Run System Check

```bash
uv run python test_system.py
```

You should see: `🎉 All tests passed! System is ready.`

### Step 5: Start the Server

```bash
uv run python server.py
```

The server will start at: http://localhost:8000

### Step 6: Open the Web UI

Navigate to: http://localhost:8000

You'll see the OpenResearch interface with:
- Beautiful gradient dark theme
- Query input box
- "Start Deep Research" button
- Progress tracking
- Results display

## 🎯 Using the System

### Example Queries

Try these research queries:
1. "What are the latest advances in artificial intelligence and their impact on society?"
2. "How does quantum computing work and what are its applications?"
3. "What is blockchain technology and how is it being used in finance?"
4. "What are the best practices for cybersecurity in 2026?"
5. "How does machine learning work in autonomous vehicles?"

### Research Process

When you submit a query, you'll see 8 phases:

1. **📋 Planning** (5-10s)
   - Breaks your query into 35 sub-questions
   - Example: "What is AI?", "How does AI work?", "What are AI benefits?"

2. **🔍 Query Generation** (5-10s)
   - Creates 120+ optimized search queries
   - Variations with different keywords and formats

3. **🌐 Web Search** (60-180s)
   - Searches Tavily API with each query
   - Collects 35 results per query
   - Total: ~4,200+ websites

4. **✂️ Chunking** (2-5s)
   - Splits all content into 1000-char chunks
   - Adds metadata and hashes

5. **📊 Ranking** (5-15s)
   - Scores each chunk by relevance
   - Keeps top 500 most relevant chunks

6. **🧠 Vector DB** (30-60s)
   - Creates embeddings with Ollama qwen3:8b
   - Stores in ChromaDB for semantic search

7. **🔄 Reasoning Loop** (30-60s)
   - Generates 120 analytical questions
   - Queries vector DB for each question
   - Collects 1,200+ insights

8. **📝 Final Answer** (10-20s)
   - Synthesizes comprehensive response
   - Includes citations and sources

**Total time**: ~3-6 minutes per query

## 📊 Expected Performance

### Resources Used
- **API Calls**: ~130 Gemini calls + 120 Tavily searches
- **Websites**: 4,200+ (120 queries × 35 results)
- **Embeddings**: 500+ vectors (8B parameter model)
- **Vector DB**: ~500 documents stored
- **Memory**: 2-4 GB RAM during research

### Output Quality
- **Confidence Score**: 70-95%
- **Sources Cited**: 30-50 unique sources
- **Answer Length**: 2,000-5,000 words
- **Sections**: 7+ comprehensive sections

## 🔧 Troubleshooting

### "Ollama connection failed"
```bash
# Start Ollama
ollama serve

# Or check if running
curl http://localhost:11434
```

### "Model not found"
```bash
ollama pull qwen3-embeddings:8b
ollama list  # Verify it's there
```

### "API rate limit exceeded"
- The system has 8 Gemini API keys for rotation
- Tavily has usage limits - check your plan
- Wait a few minutes and retry

### "Port 8000 already in use"
Edit `server.py` line with `port=8000` to different port:
```python
port=8001  # Use 8001 instead
```

### "Module import error"
```bash
uv sync
# Or reinstall
uv pip install -e .
```

## 💡 Pro Tips

1. **Be Specific**: More specific queries get better results
   - ✅ "What are the security risks of AI in healthcare 2026?"
   - ❌ "Tell me about AI"

2. **Use the API**: For programmatic access
   ```bash
   curl -X POST http://localhost:8000/api/research \
     -H "Content-Type: application/json" \
     -d '{"query": "Your question"}'
   ```

3. **Monitor Progress**: Watch the web UI for real-time updates
   - Each phase shows completion status
   - Progress bar updates automatically

4. **Save Results**: Copy the final answer or export sources
   - Click "📋 Copy" button in UI
   - Sources list has direct links

5. **Run Overnight**: Full research can take 3-6 minutes
   - Perfect for running in background
   - Results are saved when complete

## 📝 CLI Mode (Alternative)

If you prefer command line:

```bash
uv run python -m Agent.agent
```

This runs a test research with a sample query.

## 🎨 Customization

### Change LLM Model
Edit `Agent/agent.py` → `get_llm()`:
```python
model = "gemini-2.5-pro"  # Instead of flash
```

### Adjust Research Depth
Edit `Agent/agent.py`:
```python
max_queries = 60   # Fewer queries (faster)
max_results = 20   # Less results per query
max_chunks = 200   # Keep fewer chunks
```

### Different Embedding Model
Edit `Agent/embeddings.py`:
```python
model = "nomic-embed-text"  # Alternative Ollama model
```

## 📚 Next Steps

- Read full documentation: `README.md`
- Explore API docs: http://localhost:8000/docs
- Check project structure in repository
- Modify and customize for your needs

## 🆘 Need Help?

1. Run verification: `uv run python test_system.py`
2. Check logs in terminal where server is running
3. Review error messages carefully
4. Check API keys in `.env` are valid
5. Ensure Ollama is running and model is downloaded

---

**Happy Researching! 🧠✨**
