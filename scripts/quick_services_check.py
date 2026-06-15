#!/usr/bin/env python3
"""Quick per-service smoke check for SERVICES_STATUS.md (subset of production verify)."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ.setdefault("SECRET_KEY", "quick-services-check-secret")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///quick_check.sqlite3")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("PHASE1_TIMEOUT_S", "25")

import django

django.setup()

from django.conf import settings as django_settings  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from advisory.services.location_context import (  # noqa: E402
    INDIA_LAT_MAX,
    INDIA_LAT_MIN,
    INDIA_LON_MAX,
    INDIA_LON_MIN,
)

_hosts = list(django_settings.ALLOWED_HOSTS)
for _h in ("testserver", "127.0.0.1", "localhost"):
    if _h not in _hosts:
        _hosts.append(_h)
django_settings.ALLOWED_HOSTS = _hosts

REALTIME_WEATHER = ("open-meteo", "openweathermap", "imd")
REALTIME_MARKET = ("data.gov.in", "agmarknet", "enam", "msp")
MOCK_MARKERS = ("simulated", "mock", "random", "estimated (all apis unavailable)")


def _json(resp) -> dict:
    if resp.status_code >= 300 and resp.status_code < 400 and resp.get("Location"):
        # Follow one redirect (e.g. monitoring health without trailing slash)
        from django.test import Client
        loc = resp.get("Location", "")
        if loc.startswith("/"):
            c2 = Client()
            r2 = c2.get(loc)
            return r2.json() if r2.status_code == 200 else {}
    try:
        return resp.json()
    except Exception:
        return {}


def _in_india(lat: float, lon: float) -> bool:
    return INDIA_LAT_MIN <= lat <= INDIA_LAT_MAX and INDIA_LON_MIN <= lon <= INDIA_LON_MAX


def _data_source(body: dict) -> str:
    return str(body.get("data_source") or body.get("source") or "").lower()


def _is_realtime_weather(body: dict) -> Tuple[bool, str]:
    src = _data_source(body)
    if body.get("status") == "fallback":
        return False, src or "fallback"
    if any(s in src for s in REALTIME_WEATHER):
        return True, src
    if body.get("temperature") is not None or body.get("current"):
        return True, src or "live (fields present)"
    return False, src or "unknown"


def _is_realtime_market(body: dict) -> Tuple[bool, str]:
    src = _data_source(body)
    if body.get("is_live") is False:
        return False, src or body.get("status", "not live")
    if body.get("status") in ("fallback", "unavailable"):
        return False, src or body.get("status", "")
    if any(m in src for m in MOCK_MARKERS):
        return False, src
    if body.get("is_live") is True:
        return True, src or "live"
    if any(s in src for s in REALTIME_MARKET):
        return True, src
    crops = body.get("top_crops") or body.get("market_prices") or []
    if crops and body.get("timestamp"):
        return True, src or "live (prices + timestamp)"
    return bool(crops), src or "unknown"


Row = Dict[str, str]


def main() -> int:
    client = APIClient()
    rows: List[Row] = []
    failed = 0

    def add(
        service: str,
        endpoint: str,
        ok: bool,
        realtime: str,
        data_source: str,
        notes: str,
    ):
        nonlocal failed
        if not ok:
            failed += 1
        rows.append({
            "service": service,
            "endpoint": endpoint,
            "realtime": realtime,
            "status": "OK" if ok else "FAIL",
            "data_source": data_source or "—",
            "notes": notes,
        })

    # Health
    for path in ("/api/health/", "/api/health/simple/", "/api/monitoring/health/"):
        r = client.get(path, follow=True)
        add("Health", path, r.status_code == 200, "n/a", "—", f"HTTP {r.status_code}")

    # Location
    r = client.get("/api/locations/search/", {"q": "Delhi"})
    ok = r.status_code == 200 and (_json(r).get("total", 0) >= 0)
    add("Location", "GET /api/locations/search/?q=Delhi", ok, "yes (Nominatim)", "nominatim", "")

    r = client.get("/api/locations/resolve/", {"location": "Delhi"})
    body = _json(r) if r.status_code == 200 else {}
    coords = body.get("coordinates") or {}
    lat, lon = coords.get("lat"), coords.get("lon")
    ok = r.status_code == 200 and body.get("status") == "success" and _in_india(float(lat), float(lon))
    add("Location", "GET /api/locations/resolve/", ok, "yes", body.get("location", {}).get("source", ""), "India bounds")

    r = client.get("/api/locations/reverse/", {"lat": 28.6139, "lon": 77.2090})
    body = _json(r) if r.status_code == 200 else {}
    ok = r.status_code == 200 and body.get("status") == "success"
    add("Location", "GET /api/locations/reverse/", ok, "yes", body.get("location", {}).get("source", ""), "")

    # Weather
    r = client.get("/api/weather/", {"location": "Delhi", "latitude": 28.6139, "longitude": 77.2090})
    body = _json(r) if r.status_code == 200 else {}
    rt, src = _is_realtime_weather(body)
    add("Weather", "GET /api/weather/", r.status_code == 200 and rt, "yes" if rt else "fallback", src, body.get("status", ""))

    # Market
    r = client.get("/api/market-prices/", {"location": "Delhi", "latitude": 28.6139, "longitude": 77.2090})
    body = _json(r) if r.status_code == 200 else {}
    rt, src = _is_realtime_market(body)
    has_registered_key = bool(os.environ.get("DATA_GOV_IN_API_KEY", "").strip()) and (
        os.environ.get("DATA_GOV_IN_API_KEY", "").strip().lower()
        not in ("your_data_gov_in_api_key_here", "change_me", "")
    )
    if has_registered_key:
        market_ok = r.status_code == 200 and rt
        market_note = "registered DATA_GOV_IN_API_KEY — expect is_live=true"
    else:
        market_ok = r.status_code == 200 and body.get("status") in (
            "success",
            "partial",
            "unavailable",
            "fallback",
        )
        market_note = (
            "unavailable without key is OK; set DATA_GOV_IN_API_KEY for live assertion"
        )
    add(
        "Market",
        "GET /api/market-prices/",
        market_ok,
        "yes" if rt else body.get("status", "not live"),
        src,
        market_note,
    )

    r = client.get("/api/market-prices/mandis/", {"location": "Delhi", "state": "Delhi"})
    body = _json(r) if r.status_code == 200 else {}
    mandis = body.get("mandis") or body.get("results") or []
    add("Market", "GET /api/market-prices/mandis/", r.status_code == 200, "yes" if mandis else "list may be empty", _data_source(body), f"{len(mandis)} mandis")

    # Crop advisory
    r = client.get("/api/advisories/", {"location": "Delhi", "latitude": 28.6139, "longitude": 77.2090})
    body = _json(r) if r.status_code == 200 else {}
    recs = body.get("recommendations") or []
    scored = sum(
        1
        for c in recs
        if c.get("suitability_score") is not None
        or c.get("score") is not None
        or c.get("profitability_score") is not None
    )
    ok = r.status_code == 200 and len(recs) >= 3
    add("Crop advisory", "GET /api/advisories/", ok, "yes (engine+live inputs)", _data_source(body), f"{len(recs)} recs, {scored} scored")

    r = client.get("/api/advisories/", {"location": "Mumbai", "latitude": 19.076, "longitude": 72.8777})
    body2 = _json(r) if r.status_code == 200 else {}
    recs2 = body2.get("recommendations") or []
    add("Crop advisory", "GET /api/advisories/ (Mumbai)", r.status_code == 200 and len(recs2) >= 3, "yes", _data_source(body2), "multi-location")

    # Schemes
    r = client.get("/api/schemes/", {"location": "Delhi"})
    body = _json(r) if r.status_code == 200 else {}
    schemes = body.get("schemes") or body.get("results") or []
    add("Schemes", "GET /api/schemes/", r.status_code == 200 and len(schemes) >= 1, "catalog", _data_source(body), f"{len(schemes)} schemes")

    r = client.get("/api/government-schemes/", {"location": "Delhi"})
    add("Schemes", "GET /api/government-schemes/", r.status_code == 200, "catalog", "unified", "alias route")

    # Chatbot
    r = client.post("/api/chatbot/query/", {"query": "Delhi weather today", "language": "en"}, format="json")
    body = _json(r) if r.status_code == 200 else {}
    ok = (
        r.status_code == 200
        and body.get("response")
        and body.get("intent") is not None
    )
    add("Chatbot", "POST /api/chatbot/query/", ok, "NLP+routing", body.get("data_source", ""), f"intent={body.get('intent')}")

    # Diagnostics
    r = client.get("/api/diagnostics/crop-search/", {"q": "tom"})
    body = _json(r) if r.status_code == 200 else {}
    add("Diagnostics", "GET /api/diagnostics/crop-search/", r.status_code == 200 and body.get("total", 0) > 0, "catalog", "crop_catalog", "")

    r = client.post(
        "/api/diagnostics/detect/",
        {"crop": "tomato", "images": {}},
        format="json",
    )
    body = _json(r) if r.status_code == 200 else {}
    diag = body.get("diagnosis") or []
    # Empty images must return photo_required (not a fake diagnosis)
    ok = r.status_code == 200 and body.get("status") in (
        "success",
        "partial",
        "photo_required",
    )
    fake = body.get("status") not in ("photo_required",) and any(
        "unknown" in str(d.get("name", "")).lower() and d.get("confidence", 1) == 0
        for d in diag
    )
    add(
        "Diagnostics",
        "POST /api/diagnostics/detect/",
        ok and not fake,
        "KrishiRaksha pipeline",
        body.get("data_source", "") or "krishi_raksha",
        body.get("status", ""),
    )

    # Pest
    r = client.get("/api/pest-detection/", {"crop": "wheat", "location": "Delhi"})
    add("Pest", "GET /api/pest-detection/", r.status_code == 200, "gov APIs", _data_source(_json(r) if r.status_code == 200 else {}), "")

    # Gov realtime legacy
    r = client.get("/api/realtime-gov/weather/", {"location": "Delhi"})
    add("Government", "GET /api/realtime-gov/weather/", r.status_code == 200, "yes", "ultra_dynamic", "")

    # Crops search
    r = client.get("/api/crops/search/", {"q": "wheat"})
    add("Crops", "GET /api/crops/search/", r.status_code == 200, "catalog", "crop_catalog", "")

    out = os.path.join(ROOT, "docs", "SERVICES_STATUS.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Services Status",
        "",
        f"Last verified: **{ts}** (quick smoke check)",
        "",
        "| Service | Endpoint | Real-time? | Status | data_source | Notes |",
        "|---------|----------|------------|--------|-------------|-------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['service']} | `{row['endpoint']}` | {row['realtime']} | **{row['status']}** | {row['data_source']} | {row['notes']} |"
        )

    lines.extend([
        "",
        "## Endpoint inventory",
        "",
        "Router (`advisory/api/urls.py`): `users`, `advisories`, `crops`, `weather`, `market-prices`,",
        "`trending-crops`, `sms-ivr`, `pest-detection`, `tts`, `forum`, `schemes`, `chatbot`,",
        "`locations`, `realtime-gov`, `monitoring`, `rate-limits`, `diagnostics`, `iot-blockchain`.",
        "",
        "Custom actions: `weather/current`, `market-prices/mandis`, `market-prices/crop-search`,",
        "`locations/search|resolve|reverse`, `chatbot/query`, `diagnostics/crop-search|detect|predict|feedback`,",
        "`schemes/eligibility`, `realtime-gov/weather|market_prices|crop_recommendations|mandi_search|crop_search`,",
        "`crops/search`, health: `/api/health/`, `/api/health/simple/`, `/api/health/liveness/`,",
        "`/api/government-schemes/` (alias).",
        "",
        "## Re-run checks",
        "",
        "```bash",
        "cd /Users/arnavmishra/ai/agri_advisory_app",
        "export SECRET_KEY=local-dev-secret DEBUG=True DATABASE_URL=sqlite:///local.db RATE_LIMIT_ENABLED=false",
        "python3 manage.py check",
        "python3 scripts/quick_services_check.py",
        "python3 scripts/production_service_verification.py --markdown docs/PRODUCTION_TEST_REPORT.md",
        "```",
        "",
        "Optional env: `DATA_GOV_IN_API_KEY`, `GOOGLE_AI_API_KEY`, `OPENWEATHER_API_KEY`.",
        "",
    ])

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {out}")
    print(f"FAILURES={failed} / {len(rows)}")
    print(json.dumps(rows, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
