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
MODEL_CHECK=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); models=[m['name'] for m in d.get('models',[])]; print('krishimitra' if any('krishimitra' in m for m in models) else 'qwen' if any('qwen2.5' in m for m in models) else 'missing')" 2>/dev/null)
if [ "$MODEL_CHECK" = "missing" ]; then
  echo "⚠  No model found."
  echo "   Preferred: cd custom_llm_trainer && ollama create krishimitra-llm -f Modelfile"
  echo "   Fallback:  ollama pull qwen2.5:7b"
  exit 1
elif [ "$MODEL_CHECK" = "qwen" ]; then
  echo "⚠  krishimitra-llm not found — using qwen2.5:7b fallback"
  echo "   To load your fine-tuned model: cd custom_llm_trainer && ollama create krishimitra-llm -f Modelfile"
  # Update DEFAULT_MODEL env override so Phase1 uses qwen2.5:7b
  export OLLAMA_MODEL=qwen2.5:7b
else
  echo "✅  krishimitra-llm (your custom model) ready"
  export OLLAMA_MODEL=krishimitra-llm
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
