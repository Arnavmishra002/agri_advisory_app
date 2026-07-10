"""
KrishiMitra — Monitoring & Health Check API Views
Self-contained: no dependency on the deleted advisory.monitoring package.
"""

from typing import Any, Dict
import logging
import os
import time
from datetime import datetime

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..middleware.rate_limiting import get_rate_limit_status, reset_rate_limits

logger = logging.getLogger(__name__)

# ── Service start time (for uptime reporting) ─────────────────
_SERVICE_START = time.time()


def _now() -> str:
    return datetime.now().isoformat()


def _uptime_seconds() -> float:
    return round(time.time() - _SERVICE_START, 1)


def _staff_or_debug(request) -> bool:
    if settings.DEBUG:
        return True
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


def _system_metrics() -> dict:
    """Collect lightweight system metrics without psutil dependency."""
    import os, sys
    metrics = {
        "timestamp":       _now(),
        "uptime_seconds":  _uptime_seconds(),
        "python_version":  sys.version.split()[0],
        "debug":           settings.DEBUG,
    }
    try:
        import psutil
        metrics["cpu_percent"]    = psutil.cpu_percent(interval=0.1)
        metrics["memory_percent"] = psutil.virtual_memory().percent
        metrics["disk_percent"]   = psutil.disk_usage("/").percent
    except ImportError:
        pass
    return metrics


# ══════════════════════════════════════════════════════════════
# MonitoringViewSet
# ══════════════════════════════════════════════════════════════
class MonitoringViewSet(viewsets.ViewSet):
    """System health and performance monitoring endpoints."""

    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def health(self, request):
        """Basic health check — used by Docker HEALTHCHECK, Render, load balancers."""
        return Response({
            "status":    "healthy",
            "service":   "KrishiMitra AI",
            "timestamp": _now(),
            "uptime_s":  _uptime_seconds(),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def system_health(self, request):
        """Detailed system metrics (staff/DEBUG only)."""
        if not _staff_or_debug(request):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            return Response({
                "status":  "healthy",
                "metrics": _system_metrics(),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("system_health error: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def performance_summary(self, request):
        """Lightweight performance summary (no in-memory tracking needed)."""
        if not _staff_or_debug(request):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            "status":    "ok",
            "timestamp": _now(),
            "uptime_s":  _uptime_seconds(),
            "note":      "Detailed APM available via Sentry (SENTRY_DSN env var)",
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def metrics(self, request):
        """System metrics endpoint."""
        if not _staff_or_debug(request):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response(_system_metrics(), status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def record_activity(self, request):
        """No-op stub — activity tracking via Sentry/Gemini usage analytics."""
        if not _staff_or_debug(request):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        return Response({"status": "success", "message": "Activity noted"})


# ══════════════════════════════════════════════════════════════
# RateLimitViewSet
# ══════════════════════════════════════════════════════════════
class RateLimitViewSet(viewsets.ViewSet):
    """Rate limit management endpoints."""

    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def status(self, request):
        if not _staff_or_debug(request):
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        try:
            client_ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
            user_id   = request.user.id if request.user.is_authenticated else None
            client_id = f"user_{user_id}" if user_id else f"ip_{client_ip}"
            return Response({
                "client_id":   client_id,
                "rate_limits": get_rate_limit_status(client_id),
                "timestamp":   _now(),
            })
        except Exception as e:
            logger.exception("rate limit status error: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"])
    def reset(self, request):
        try:
            if not (request.user.is_staff or request.user.is_superuser):
                return Response({"error": "Insufficient permissions"}, status=status.HTTP_403_FORBIDDEN)
            client_id = request.data.get("client_id")
            if not client_id:
                return Response({"error": "client_id required"}, status=status.HTTP_400_BAD_REQUEST)
            reset_rate_limits(client_id)
            return Response({"status": "success", "message": f"Rate limits reset for {client_id}"})
        except Exception as e:
            logger.exception("rate limit reset error: %s", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ══════════════════════════════════════════════════════════════
# Function-based health views
# ══════════════════════════════════════════════════════════════
@csrf_exempt
def simple_health_check(request):
    """Simple health check for load balancers — no auth."""
    return JsonResponse({
        "status":    "healthy",
        "service":   "KrishiMitra AI",
        "timestamp": _now(),
    })


@csrf_exempt
def readiness_check(request):
    """Readiness probe — checks DB, cache, Phase 1 AI server, and Ollama."""
    checks: Dict[str, str] = {}
    overall_ok = True

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall_ok = False

    # ── Cache ─────────────────────────────────────────────────────────────────
    try:
        from django.core.cache import cache
        cache.set("readiness_probe", "ok", 10)
        checks["cache"] = "ok" if cache.get("readiness_probe") == "ok" else "miss"
    except Exception as e:
        checks["cache"] = f"error: {e}"

    # ── Phase 1 AI server (Qwen + RAG) ────────────────────────────────────────
    try:
        import urllib.request
        phase1_base = os.environ.get("PHASE1_BASE_URL") or os.environ.get("PHASE1_URL", "http://127.0.0.1:8001")
        if phase1_base.rstrip("/").endswith("/chat"):
            phase1_base = phase1_base.rstrip("/")[:-5]
        req = urllib.request.Request(phase1_base.rstrip("/") + "/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            import json
            h = json.loads(resp.read())
            if h.get("status") == "healthy":
                checks["phase1_ai"] = f"ok (rag={h.get('rag')}, ollama={h.get('ollama')})"
            else:
                checks["phase1_ai"] = f"degraded: {h.get('status')}"
    except Exception:
        checks["phase1_ai"] = "offline (Qwen+RAG unavailable — rule-based fallback active)"

    # ── Ollama ────────────────────────────────────────────────────────────────
    try:
        import urllib.request
        req = urllib.request.Request(os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434") + "/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            import json
            models = [m["name"] for m in json.loads(resp.read()).get("models", [])]
            desired_model = os.environ.get("OLLAMA_MODEL", "krishimitra-llm").strip()
            desired_base = desired_model.split(":", 1)[0]
            model_present = any(
                model == desired_model or model.split(":", 1)[0] == desired_base
                for model in models
            )
            checks["ollama"] = (
                f"ok (model={desired_model}, "
                f"present={'yes' if model_present else 'no'})"
            )
    except Exception:
        checks["ollama"] = "offline (local LLM unavailable)"

    # ── Chatbot runtime capacity ─────────────────────────────────────────────
    try:
        from advisory.services.chat_intelligence_service import chatbot_runtime_status
        chat_runtime = chatbot_runtime_status()
        local_ai = chat_runtime.get("local_ai", {})
        phase1 = chat_runtime.get("phase1", {})
        cb_label = "open" if phase1.get("circuit_breaker_open") else "closed"
        checks["chatbot_runtime"] = (
            f"ok (local_ai_active={local_ai.get('active')}/"
            f"{local_ai.get('max_concurrency')}, phase1_cb={cb_label})"
        )
    except Exception as exc:
        checks["chatbot_runtime"] = f"unknown: {exc}"

    # ── Crop disease ML model ────────────────────────────────────────────────
    try:
        from advisory.ml.config import DEFAULT_MODEL_DIR, MODEL_FILENAME, LABELS_FILENAME
        from advisory.ml.labels import load_labels
        from advisory.ml.model_metadata import load_model_metadata, readiness_summary
        model_path = DEFAULT_MODEL_DIR / MODEL_FILENAME
        labels_path = DEFAULT_MODEL_DIR / LABELS_FILENAME
        if model_path.exists() and labels_path.exists():
            labels = load_labels(labels_path)
            metadata = load_model_metadata(DEFAULT_MODEL_DIR, labels)
            checks["crop_disease_model"] = readiness_summary(metadata)
        else:
            checks["crop_disease_model"] = (
                f"missing ({model_path.name}); diagnostics use advisory_fallback"
            )
    except Exception as exc:
        checks["crop_disease_model"] = f"unknown: {exc}"

    status_code = 200 if overall_ok else 503
    return JsonResponse({
        "status":    "ready" if overall_ok else "not_ready",
        "checks":    checks,
        "timestamp": _now(),
    }, status=status_code)


def _configured_env(name: str) -> bool:
    value = os.environ.get(name, "").strip()
    return bool(value) and value.lower() not in {
        "change_me",
        "your_api_key_here",
        "your_data_gov_in_api_key_here",
    }


@csrf_exempt
def launch_readiness_check(request):
    """Production launch gate with explicit, non-secret remediation details."""
    import json

    readiness_response = readiness_check(request)
    try:
        runtime_checks = json.loads(readiness_response.content).get("checks", {})
    except Exception:
        runtime_checks = {}

    strict = (
        os.environ.get("LAUNCH_CHECK", "false").lower() in {"1", "true", "yes"}
        or request.GET.get("strict", "false").lower() in {"1", "true", "yes"}
    )
    blockers = []

    def block(code: str, service: str, message: str, action: str) -> None:
        blockers.append({
            "code": code,
            "service": service,
            "message": message,
            "action": action,
        })

    database_ok = str(runtime_checks.get("database", "")).startswith("ok")
    phase1_ok = str(runtime_checks.get("phase1_ai", "")).startswith("ok")
    ollama_status = str(runtime_checks.get("ollama", ""))
    ollama_ok = ollama_status.startswith("ok") and "present=yes" in ollama_status
    disease_ok = str(runtime_checks.get("crop_disease_model", "")).startswith("ok")
    redis_required = not settings.DEBUG and bool(settings.RATE_LIMIT_ENABLED)
    redis_ok = _configured_env("REDIS_URL")
    data_gov_ok = _configured_env("DATA_GOV_IN_API_KEY")
    sentry_ok = bool(getattr(settings, "SENTRY_DSN", None))

    if not database_ok:
        block(
            "database_unavailable",
            "database",
            "The farmer data service is not ready.",
            "Verify DATABASE_URL and database connectivity.",
        )
    if redis_required and not redis_ok:
        block(
            "redis_required",
            "redis",
            "Shared rate limiting and cache are not configured for production.",
            "Set REDIS_URL to a production Redis instance.",
        )
    if not data_gov_ok:
        block(
            "mandi_api_key_missing",
            "mandi",
            "Full live mandi coverage is not configured.",
            "Set DATA_GOV_IN_API_KEY from data.gov.in.",
        )
    if not phase1_ok:
        block(
            "phase1_offline",
            "local_ai",
            "The local knowledge and RAG service is unavailable.",
            "Start Phase 1 and verify PHASE1_BASE_URL/health.",
        )
    if not ollama_ok:
        block(
            "ollama_model_unavailable",
            "local_ai",
            "The configured local language model is not available.",
            "Install OLLAMA_MODEL and verify the Ollama tags endpoint.",
        )
    if not disease_ok:
        block(
            "disease_model_unverified",
            "diagnostics",
            "Image disease classification is not production-verified.",
            "Keep advisory fallback enabled until model quality is production_candidate.",
        )
    if not sentry_ok:
        block(
            "sentry_missing",
            "observability",
            "Production error monitoring is not configured.",
            "Set SENTRY_DSN before farmer launch.",
        )

    status_label = "blocked_for_launch" if blockers else "ready"
    http_status = 503 if strict and blockers else 200
    return JsonResponse({
        "status": status_label,
        "strict": strict,
        "message": (
            "Launch checks need attention. Development fallbacks remain available."
            if blockers
            else "All required farmer-launch checks passed."
        ),
        "checks": {
            "database": database_ok,
            "redis": redis_ok if redis_required else "not_required_in_debug",
            "data_gov_in_api_key": data_gov_ok,
            "phase1_rag": phase1_ok,
            "ollama_model": ollama_ok,
            "disease_model": disease_ok,
            "sentry": sentry_ok,
        },
        "blockers": blockers,
        "timestamp": _now(),
    }, status=http_status)


@csrf_exempt
def liveness_check(request):
    """Liveness probe — returns alive if process is responding."""
    return JsonResponse({
        "status":    "alive",
        "uptime_s":  _uptime_seconds(),
        "timestamp": _now(),
    })


# ── Data freshness endpoint (Fix 8) ──────────────────────────────────────────
@csrf_exempt
def data_freshness(request):
    """
    GET /api/health/data-freshness/

    Returns the current age of every cached real-time data source so the
    Flutter app and ops team can instantly see whether data is stale.

    Response shape:
    {
      "market": {"is_live": true, "reported_date": "12-06-2026", "cache_age_min": 14},
      "weather": {"is_live": true, "source": "Open-Meteo", "cache_age_min": 2},
      "timestamp": "2026-06-17T08:30:00Z"
    }
    """
    from datetime import datetime, timezone as _tz
    result = {"timestamp": datetime.now(tz=_tz.utc).isoformat()}

    # ── Market (Agmarknet Direct) ─────────────────────────────
    try:
        from advisory.services.agmarknet_direct_client import agmarknet_direct, CACHE_TTL_SECS
        import time as _time
        cache_key = "national"
        cached = agmarknet_direct._cache.get(cache_key)
        ts     = agmarknet_direct._cache_ts.get(cache_key, 0)
        age_s  = int(_time.time() - ts) if ts else None
        result["market"] = {
            "is_live":       cached.get("is_live", False) if cached else False,
            "reported_date": cached.get("reported_date", "") if cached else "",
            "total_records": cached.get("total_records", 0) if cached else 0,
            "data_source":   cached.get("data_source", "not loaded") if cached else "not loaded",
            "cache_age_min": round(age_s / 60, 1) if age_s is not None else None,
            "cache_ttl_min": round(CACHE_TTL_SECS / 60, 0),
            "next_refresh_min": (
                max(0, round((CACHE_TTL_SECS - age_s) / 60, 1))
                if age_s is not None else None
            ),
        }
    except Exception as exc:
        result["market"] = {"error": str(exc)}

    # ── Weather (Open-Meteo) ──────────────────────────────────
    try:
        from django.core.cache import caches
        _wcache = caches["weather_cache"]
        # Probe Delhi to check if weather cache is populated
        probe = _wcache.get("weather:delhi:hi")
        result["weather"] = {
            "cache_populated": probe is not None,
            "primary_source": "Open-Meteo (free, no key)",
            "fallback_source": "OpenWeatherMap (OPENWEATHER_API_KEY)",
            "note": "Weather cache is per-location; probe checks Delhi as sentinel.",
        }
    except Exception as exc:
        result["weather"] = {"error": str(exc)}

    # ── RAG / Phase1 ──────────────────────────────────────────
    try:
        from phase1.rag.retriever import _result_cache, _embed
        info = _embed.cache_info()
        result["rag"] = {
            "result_cache_entries": len(_result_cache),
            "embedding_lru_hits":   info.hits,
            "embedding_lru_misses": info.misses,
            "embedding_lru_size":   info.currsize,
        }
    except Exception:
        result["rag"] = {"note": "Phase1 RAG not loaded (offline mode)"}

    # ── Crop Recommendation Source Health ───────────────────────
    try:
        from django.core.cache import cache
        from advisory.services.crop_recommendation_engine import CROP_REC_HEALTH_CACHE_KEY

        latest = cache.get(CROP_REC_HEALTH_CACHE_KEY)
        result["crop_recommendation"] = latest or {
            "status": "not_loaded",
            "alerts": ["No crop recommendation request has recorded source health yet."],
            "sources": {},
        }
    except Exception as exc:
        result["crop_recommendation"] = {"error": str(exc)}

    return JsonResponse(result)


@csrf_exempt
def sentry_test(request):
    """
    GET /api/health/sentry-test/

    Sends a test event to Sentry to verify the DSN is correctly configured
    post-deploy.  Returns {"sentry": "event_sent"} when DSN is active,
    {"sentry": "not_configured"} when absent — never raises.
    """
    try:
        import sentry_sdk
        from django.conf import settings as _s
        if getattr(_s, "SENTRY_DSN", None):
            sentry_sdk.capture_message("KrishiMitra Sentry DSN test", level="info")
            return JsonResponse({"status": "ok", "sentry": "event_sent"})
        return JsonResponse({"status": "ok", "sentry": "not_configured"})
    except Exception as exc:
        return JsonResponse({"status": "ok", "sentry": f"error: {exc}"})
