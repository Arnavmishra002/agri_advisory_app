#!/bin/bash
# KrishiMitra Phase 1 — Quick Start Script
# Usage: bash start.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/../phase1_env"

echo ""
echo "═══════════════════════════════════════════════"
echo "  KrishiMitra Phase 1 — Local AI Server"
echo "═══════════════════════════════════════════════"

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "❌  Ollama is not running."
  echo "   Open a new terminal and run: ollama serve"
  exit 1
fi
echo "✅  Ollama running"

# Check model
MODEL_CHECK=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); models=[m['name'] for m in d.get('models',[])]; print('ok' if any('qwen2.5' in m or 'krishimitra' in m for m in models) else 'missing')" 2>/dev/null)
if [ "$MODEL_CHECK" != "ok" ]; then
  echo "⚠  Model not found. Pulling qwen2.5:7b..."
  ollama pull qwen2.5:7b
fi
echo "✅  Ollama model ready"

# Activate venv
source "$VENV/bin/activate"
echo "✅  Virtual environment activated"

cd "$SCRIPT_DIR"

# Build knowledge base if not done
KB_COUNT=$(find knowledge_base -name "*.txt" 2>/dev/null | wc -l | tr -d ' ')
if [ "$KB_COUNT" -lt "5" ]; then
  echo ""
  echo "📚  Knowledge base not found. Generating with Qwen (~15 min)..."
  python3 generate_knowledge_base.py
fi
echo "✅  Knowledge base: $KB_COUNT files"

# Build vector store if not done
CHROMA_EXISTS=$([ -d "chroma_db" ] && echo "yes" || echo "no")
if [ "$CHROMA_EXISTS" = "no" ]; then
  echo ""
  echo "🔢  Building vector store (2-5 min)..."
  python3 rag/ingest.py
fi
echo "✅  Vector store ready"

# Start FastAPI server
echo ""
echo "🚀  Starting KrishiMitra Phase 1 server on port 8001..."
echo "   API docs:  http://localhost:8001/docs"
echo "   Health:    http://localhost:8001/health"
echo "   Chat test: http://localhost:8001/rag/search?q=wheat+irrigation"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
