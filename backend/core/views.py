from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


def api_root(request):
    """Root handler — serves frontend SPA or JSON API info."""
    # If SERVE_FRONTEND + FRONTEND_AT_ROOT, serve_frontend_index handles this.
    # This fallback handles any HEAD/GET that reaches here.
    if request.method == "HEAD":
        from django.http import HttpResponse
        return HttpResponse(status=200)

    payload = {
        "service": "KrishiMitra AI",
        "version": "2.1",
        "status": "running",
        "docs": "/api/schema/swagger-ui/",
        "health": "/api/health/",
    }
    if getattr(settings, "SERVE_FRONTEND", False):
        payload["ui"] = "/"
    return JsonResponse(payload)


def serve_frontend_index(request):
    """Serve built SPA from frontend/dist when SERVE_FRONTEND is enabled."""
    index_path = Path(settings.FRONTEND_DIST) / "index.html"
    if not index_path.is_file():
        raise Http404("Frontend not built. Run: cd frontend && npm run build")
    return FileResponse(index_path.open("rb"), content_type="text/html; charset=utf-8")


@csrf_exempt
@require_http_methods(["POST"])
def api_test(request):
    """Simple API test endpoint."""
    try:
        data = json.loads(request.body)
        return JsonResponse({
            "status": "success",
            "message": "API is working!",
            "received_data": data,
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
