"""
KrishiMitra Phase 1 — FastAPI Local AI Server
==============================================
Qwen 2.5 7B + ChromaDB RAG + Open-Meteo weather
Runs 100% locally. Zero cloud API cost.

Start:
    source ../phase1_env/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Endpoints:
    POST /chat          — main chat endpoint
    POST /chat/stream   — streaming chat (tokens arrive in real-time)
    GET  /health        — system health check
    GET  /rag/status    — knowledge base status
    GET  /rag/search    — test a RAG search query
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# ── Ensure phase1 modules are importable ─────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("krishimitra")

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
except ImportError:
    print("❌  FastAPI not installed. Run: pip install fastapi uvicorn")
    sys.exit(1)

from rag.retriever import retrieve, retrieve_with_sources, is_available
from services.ollama_service import (
    build_farming_prompt,
    chat,
    stream_chat,
    get_model_info,
    AGRI_SYSTEM_PROMPT,
)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="KrishiMitra Local AI",
    description="Agricultural AI powered by Qwen 2.5 7B + ICAR knowledge base",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    query:    str              = Field(..., min_length=1, max_length=2000)
    language: str              = Field("hi", description="hi|en|mr|ta|te|gu|pa|bn|auto")
    location: Optional[str]   = Field(None, description="City or district name")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    crop:     Optional[str]   = Field(None, description="Current crop being grown")
    season:   Optional[str]   = Field(None, description="Kharif / Rabi / Zaid")
    history:  Optional[List[dict]] = Field(default_factory=list,
                                           description="Previous [{role,content}] turns")
    sensor_context:  Optional[dict] = Field(None, description="IoT sensor readings if available")
    farmer_profile:  Optional[dict] = Field(None, description="Farmer profile context for personalisation")
    stream:   bool             = Field(False, description="Stream tokens in real-time")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "मेरे गेहूँ की पत्तियाँ पीली हो रही हैं — क्या करूँ?",
                "language": "hi",
                "location": "Lucknow",
                "crop": "wheat",
                "season": "Rabi",
            }
        }


class ChatResponse(BaseModel):
    response:    str
    rag_chunks:  int
    rag_sources: List[str]
    model:       str
    language:    str
    timestamp:   str
    query:       str


# ── Helper: build weather summary string ─────────────────────────────────────
# Bug 4 fix: sys.path was being mutated on every request.
# We set the Django backend path once at module load time.
_BACKEND_PATH = str(Path(__file__).parent.parent / "backend")
if _BACKEND_PATH not in sys.path:
    sys.path.insert(0, _BACKEND_PATH)

_weather_service = None

def _get_weather_service():
    """Lazy-load the Django weather service once."""
    global _weather_service
    if _weather_service is None:
        try:
            from advisory.services.unified_realtime_service import weather_service as _ws
            _weather_service = _ws
        except Exception:
            _weather_service = None
    return _weather_service


def _get_weather_summary(location: str, lat: float, lon: float, lang: str) -> str:
    """Fetch weather from the existing Django weather service (loaded once)."""
    try:
        ws = _get_weather_service()
        if ws is None:
            return ""
        w = ws.get_weather(location, lat, lon, lang=lang)
        cur     = w.get("current") or {}
        alerts  = w.get("farming_alerts") or []
        forecast = (w.get("forecast_7day") or [])[:3]
        lines = [
            f"Current: {cur.get('temperature')}°C, {cur.get('condition', '')}",
            f"Humidity: {cur.get('humidity')}%",
        ]
        if alerts:
            lines.append(f"ALERT: {' | '.join(str(a) for a in alerts[:2])}")
        if forecast:
            fc_text = "; ".join(
                f"{d.get('date')}: {d.get('max_temp')}°C rain {d.get('rainfall_mm', 0)}mm"
                for d in forecast
            )
            lines.append(f"3-day forecast: {fc_text}")
        return "\n".join(lines)
    except Exception:
        return ""


# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Main chat endpoint. Uses RAG + Qwen for every response.
    No cloud API calls.
    """
    if req.stream:
        raise HTTPException(400, "Use POST /chat/stream for streaming responses")

    # 1. RAG retrieval — k=8 for maximum coverage, prioritises exact numbers
    rag_results = retrieve_with_sources(req.query, k=8)
    rag_texts   = [r["text"]        for r in rag_results]
    rag_sources = list({r["source_file"] for r in rag_results})

    # 2. Optional weather (non-blocking)
    weather_summary = ""
    if req.latitude and req.longitude and req.location:
        weather_summary = _get_weather_summary(
            req.location, req.latitude, req.longitude, req.language
        )

    # 3. Build prompt
    farmer_profile = {
        "location": req.location,
        "crop":     req.crop,
        "season":   req.season,
        **(req.farmer_profile or {}),   # merge full profile if provided
    }
    prompt = build_farming_prompt(
        question=req.query,
        rag_chunks=rag_texts,
        weather_summary=weather_summary or None,
        sensor_data=req.sensor_context,
        farmer_profile=farmer_profile,
        conversation_history=req.history,
    )

    # 4. Generate response via Qwen
    # Bug 6 fix: if Qwen returns empty string (e.g. Ollama overloaded),
    # return a safe fallback message instead of letting Pydantic validation
    # reject the empty string and emit a 422 to the Django caller.
    _OFFLINE_MSG = (
        "माफ़ करें, AI सेवा अभी व्यस्त है। "
        "Kisan Helpline: 1800-180-1551 (Free, 24x7)\n\n"
        "Sorry, AI service is temporarily busy. "
        "Please call Kisan Helpline: 1800-180-1551 (Free, 24x7)"
    )
    response_text = chat(prompt) or _OFFLINE_MSG

    return ChatResponse(
        response=response_text,
        rag_chunks=len(rag_texts),
        rag_sources=rag_sources,
        model=get_model_info().get("model", "qwen2.5:7b"),
        language=req.language,
        timestamp=datetime.now().isoformat(),
        query=req.query,
    )


@app.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    """
    Streaming chat — tokens arrive in real-time.
    Response is newline-delimited JSON: {"token": "..."} or {"done": true}.
    """
    # 1. RAG — k=6 for broader coverage
    rag_texts = retrieve(req.query, k=6)

    # 2. Weather
    weather_summary = ""
    if req.latitude and req.longitude and req.location:
        weather_summary = _get_weather_summary(
            req.location, req.latitude, req.longitude, req.language
        )

    # 3. Build prompt
    prompt = build_farming_prompt(
        question=req.query,
        rag_chunks=rag_texts,
        weather_summary=weather_summary or None,
        sensor_data=req.sensor_context,
        farmer_profile={"location": req.location, "crop": req.crop},
        conversation_history=req.history,
    )

    def _token_generator():
        for token in stream_chat(prompt):
            yield json.dumps({"token": token}, ensure_ascii=False) + "\n"
        yield json.dumps({"done": True, "rag_chunks": len(rag_texts)}) + "\n"

    return StreamingResponse(
        _token_generator(),
        media_type="application/x-ndjson",
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    model_info = get_model_info()
    rag_ok     = is_available()
    status     = "healthy" if (model_info["available"] and rag_ok) else "degraded"
    return {
        "status":   status,
        "ollama":   model_info["available"],
        "model":    model_info.get("model"),
        "rag":      rag_ok,
        "timestamp": datetime.now().isoformat(),
        "notes": (
            []
            if status == "healthy"
            else [
                "Run: ollama serve" if not model_info["available"] else None,
                "Run: python3 rag/ingest.py" if not rag_ok else None,
            ]
        ),
    }


# ── RAG status + search ───────────────────────────────────────────────────────
@app.get("/rag/status")
def rag_status():
    rag_ok = is_available()
    kb_dir = Path(__file__).parent / "knowledge_base"
    files  = list(kb_dir.rglob("*.txt")) + list(kb_dir.rglob("*.pdf"))
    return {
        "vector_store_ready": rag_ok,
        "knowledge_files":    len(files),
        "categories": sorted({f.parent.name for f in files}),
        "chroma_dir": str(Path(__file__).parent / "chroma_db"),
        "ingest_command": "python3 rag/ingest.py",
    }


@app.get("/rag/search")
def rag_search(
    q: str = Query(..., description="Test search query"),
    k: int = Query(3, ge=1, le=10),
):
    """Manually test what the RAG retrieves for a given query."""
    results = retrieve_with_sources(q, k=k)
    return {
        "query":   q,
        "results": [
            {
                "source":    r["source_file"],
                "category":  r["category"],
                "score":     r["score"],
                "preview":   r["text"][:200],
            }
            for r in results
        ],
    }


# ── Startup info ──────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    model_info = get_model_info()
    rag_ok     = is_available()
    logger.info("═" * 50)
    logger.info("KrishiMitra Local AI — Phase 1")
    logger.info("Ollama: %s — model: %s", "✅" if model_info["available"] else "❌", model_info.get("model"))
    logger.info("RAG:    %s", "✅ vector store ready" if rag_ok else "⚠  run: python3 rag/ingest.py")
    logger.info("Docs:   http://localhost:8001/docs")
    logger.info("═" * 50)
