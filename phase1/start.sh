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

# Prefer the model that currently passes the grounded-answer eval. The custom
# checkpoint remains opt-in through OLLAMA_MODEL after it passes the same gate.
REQUESTED_MODEL=${OLLAMA_MODEL:-qwen2.5:7b}
MODEL_CHECK=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; requested=sys.argv[1]; d=json.load(sys.stdin); names=[m['name'] for m in d.get('models',[])]; print('ready' if any(n == requested or n.split(':')[0] == requested.split(':')[0] for n in names) else 'missing')" "$REQUESTED_MODEL" 2>/dev/null)
if [ "$MODEL_CHECK" = "missing" ]; then
  echo "⚠  No model found."
  echo "   Run: ollama pull $REQUESTED_MODEL"
  exit 1
else
  echo "✅  $REQUESTED_MODEL ready"
  export OLLAMA_MODEL="$REQUESTED_MODEL"
fi

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

# Build or refresh the vector store when knowledge source files change.
python3 rag/ensure_index.py
echo "✅  Vector store ready"

# Start FastAPI server
echo ""
echo "🚀  Starting KrishiMitra Phase 1 server on port 8001..."
echo "   API docs:  http://localhost:8001/docs"
echo "   Health:    http://localhost:8001/health"
echo "   Chat test: http://localhost:8001/rag/search?q=wheat+irrigation"
echo ""
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
