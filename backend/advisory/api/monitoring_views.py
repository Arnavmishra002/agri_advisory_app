"""
KrishiMitra — Monitoring & Health Check API Views
Self-contained: no dependency on the deleted advisory.monitoring package.
"""

import logging
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
        req = urllib.request.Request("http://127.0.0.1:8001/health")
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
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            import json
            models = [m["name"] for m in json.loads(resp.read()).get("models", [])]
            qwen_present = any("qwen2.5" in m for m in models)
            checks["ollama"] = f"ok (qwen={'present' if qwen_present else 'missing'})"
    except Exception:
        checks["ollama"] = "offline (local LLM unavailable)"

    status_code = 200 if overall_ok else 503
    return JsonResponse({
        "status":    "ready" if overall_ok else "not_ready",
        "checks":    checks,
        "timestamp": _now(),
    }, status=status_code)


@csrf_exempt
def liveness_check(request):
    """Liveness probe — returns alive if process is responding."""
    return JsonResponse({
        "status":    "alive",
        "uptime_s":  _uptime_seconds(),
        "timestamp": _now(),
    })
