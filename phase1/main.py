"""
KrishiMitra Phase 1 — FastAPI Local AI Server
==============================================
Qwen 2.5 7B + ChromaDB RAG + Open-Meteo weather
Runs 100% locally. Zero cloud API cost.

Start:
    source ../phase1_env/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8001 --reload

Endpoints:
    GET  /              — service summary for browser checks
    POST /chat          — main chat endpoint
    POST /chat/stream   — streaming chat (tokens arrive in real-time)
    GET  /health        — system health check
    GET  /rag/status    — knowledge base status
    GET  /rag/search    — test a RAG search query
"""

import json
import asyncio
import hmac
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

# ── Ensure phase1 modules are importable ─────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("krishimitra")

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse, StreamingResponse
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


def _phase1_cors_origins() -> list[str]:
    raw = os.environ.get("PHASE1_CORS_ALLOWED_ORIGINS", "")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    allow_all = os.environ.get("PHASE1_ALLOW_ALL_CORS", "false").lower() in {"1", "true", "yes"}
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    if allow_all and debug:
        return ["*"]
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_phase1_cors_origins(),
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

_PROTECTED_PATH_PREFIXES = ("/chat", "/rag")
_REQUEST_SEMAPHORE = asyncio.Semaphore(
    max(1, int(os.environ.get("PHASE1_MAX_CONCURRENT_REQUESTS", "4")))
)


@app.middleware("http")
async def protect_ai_service(request: Request, call_next):
    """Fail closed for remote AI calls while keeping health probes public."""
    if not request.url.path.startswith(_PROTECTED_PATH_PREFIXES):
        return await call_next(request)

    configured_token = os.environ.get("PHASE1_SERVICE_TOKEN", "").strip()
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    require_token = (
        os.environ.get("PHASE1_REQUIRE_SERVICE_TOKEN", str(not debug)).lower()
        in {"1", "true", "yes"}
    )
    if require_token and not configured_token:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Phase 1 service authentication is not configured.",
                "error_code": "SERVICE_AUTH_NOT_CONFIGURED",
            },
        )
    if configured_token:
        supplied = request.headers.get("Authorization", "")
        expected = f"Bearer {configured_token}"
        if not hmac.compare_digest(supplied, expected):
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized", "error_code": "UNAUTHORIZED"},
                headers={"WWW-Authenticate": "Bearer"},
            )

    max_body_bytes = max(1024, int(os.environ.get("PHASE1_MAX_BODY_BYTES", "65536")))
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_body_bytes:
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body is too large.", "error_code": "PAYLOAD_TOO_LARGE"},
        )

    try:
        await asyncio.wait_for(_REQUEST_SEMAPHORE.acquire(), timeout=0.1)
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Local AI is busy.", "error_code": "CAPACITY_FULL"},
            headers={"Retry-After": "2"},
        )
    try:
        return await call_next(request)
    finally:
        _REQUEST_SEMAPHORE.release()


@app.get("/")
def root():
    """Friendly browser landing response for the Phase 1 service."""
    return {
        "service": "KrishiMitra Phase 1 Local AI/RAG",
        "status": "running",
        "message": "This is the AI/RAG service. Use the main web app on port 8001.",
        "main_app": "http://localhost:8001",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "chat": "POST /chat",
            "stream": "POST /chat/stream",
            "rag_status": "/rag/status",
            "rag_search": "/rag/search?q=wheat",
        },
        "timestamp": datetime.now().isoformat(),
    }


# ── Request / Response models ─────────────────────────────────────────────────
class _StrictModel(BaseModel):
    class Config:
        extra = "forbid"


class HistoryEntry(_StrictModel):
    role: Literal["user", "assistant"] = "user"
    content: str = Field(..., min_length=1, max_length=2000)


class SensorContextPayload(_StrictModel):
    moisture_pct: Optional[float] = Field(None, ge=0, le=100)
    moisture_status: Optional[str] = Field(None, max_length=40)
    soil_temp_c: Optional[float] = Field(None, ge=-20, le=80)
    ph: Optional[float] = Field(None, ge=0, le=14)
    nitrogen_kg_ha: Optional[float] = Field(None, ge=0, le=5000)
    phosphorus_kg_ha: Optional[float] = Field(None, ge=0, le=2000)
    potassium_kg_ha: Optional[float] = Field(None, ge=0, le=5000)
    temp_c: Optional[float] = Field(None, ge=-50, le=70)
    humidity_pct: Optional[float] = Field(None, ge=0, le=100)
    source: Optional[str] = Field(None, max_length=120)


class FarmerProfilePayload(_StrictModel):
    location: Optional[str] = Field(None, max_length=200)
    state: Optional[str] = Field(None, max_length=120)
    farm_size_bigha: Optional[float] = Field(None, ge=0, le=1_000_000)
    current_crop: Optional[str] = Field(None, max_length=120)
    current_season: Optional[str] = Field(None, max_length=40)
    soil_ph: Optional[float] = Field(None, ge=0, le=14)
    irrigation_type: Optional[str] = Field(None, max_length=40)
    crop_history: Optional[str] = Field(None, max_length=2000)
    has_pm_kisan: Optional[bool] = None
    has_kcc: Optional[bool] = None
    language: Optional[str] = Field(None, max_length=20)
    sensor_reading: Optional[SensorContextPayload] = None


class ChatRequest(_StrictModel):
    query: str = Field(..., min_length=1, max_length=2000)
    language: str = Field("hi", min_length=2, max_length=20, description="Language code")
    location: Optional[str] = Field(None, max_length=200)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    crop: Optional[str] = Field(None, max_length=120)
    season: Optional[str] = Field(None, max_length=40)
    history: List[HistoryEntry] = Field(default_factory=list, max_length=20)
    sensor_context: Optional[SensorContextPayload] = None
    farmer_profile: Optional[FarmerProfilePayload] = None
    verified_knowledge: Optional[str] = Field(None, max_length=3000)
    stream: bool = False

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


def _model_dict(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    return value.dict(exclude_none=True)

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
        alerts = [
            str(alert)
            for alert in (w.get("farming_alerts") or [])
            if "uv" not in str(alert).casefold()
        ]
        forecast = (w.get("forecast_7day") or [])[:3]
        lines = [
            f"Current: {cur.get('temperature')}°C, {cur.get('condition', '')}",
            f"Air humidity: {cur.get('humidity')}% (not soil moisture)",
        ]
        if alerts:
            lines.append(f"ALERT: {' | '.join(alerts[:2])}")
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

    # 1. RAG retrieval — fetch 20 candidates, reranker returns top 5
    #    (RAG-1: parallel vector+keyword; RAG-2: compressed context; RAG-3: cached)
    rag_results = retrieve_with_sources(req.query, k=5)
    rag_texts   = [r["text"]        for r in rag_results]
    rag_sources = list({r["source_file"] for r in rag_results})
    if not rag_texts and not (req.verified_knowledge or "").strip():
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "NO_GROUNDING",
                "message": "No verified knowledge matched this question.",
            },
        )

    # 2. Optional weather (non-blocking)
    weather_summary = ""
    if req.latitude and req.longitude and req.location:
        weather_summary = _get_weather_summary(
            req.location, req.latitude, req.longitude, req.language
        )

    # 3. Build prompt
    prompt = build_farming_prompt(
        question=req.query,
        rag_chunks=rag_texts,
        verified_knowledge=req.verified_knowledge,
        weather_summary=weather_summary or None,
        sensor_data=_model_dict(req.sensor_context),
        farmer_profile={
            "location": req.location,
            "crop": req.crop,
            "season": req.season,
            **(_model_dict(req.farmer_profile) or {}),
        },
        conversation_history=[_model_dict(item) for item in req.history],
    )

    # An empty model result is a service failure, not an answer. Returning 503
    # lets Django continue through direct Ollama and its grounded rule fallback.
    response_text = chat(prompt)
    if not response_text:
        raise HTTPException(status_code=503, detail="Local AI model unavailable")

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
    # 1. RAG — Top-20 → rerank → Top-5 (RAG-1/2/3 pipeline)
    rag_texts = retrieve(req.query, k=5)
    if not rag_texts and not (req.verified_knowledge or "").strip():
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "NO_GROUNDING",
                "message": "No verified knowledge matched this question.",
            },
        )

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
        verified_knowledge=req.verified_knowledge,
        weather_summary=weather_summary or None,
        sensor_data=_model_dict(req.sensor_context),
        farmer_profile={
            "location": req.location,
            "crop":     req.crop,
            "season":   req.season,
            **(_model_dict(req.farmer_profile) or {}),
        },
        conversation_history=[_model_dict(item) for item in req.history],
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
        "chroma_storage": "server_local",
        "ingest_command": "python3 rag/ingest.py",
    }


@app.get("/rag/search")
def rag_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=2000, description="Test search query"),
    k: int = Query(3, ge=1, le=10),
):
    """Manually test what the RAG retrieves for a given query."""
    unknown = set(request.query_params) - {"q", "k"}
    if unknown:
        raise HTTPException(status_code=400, detail="Unexpected query parameter")
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
