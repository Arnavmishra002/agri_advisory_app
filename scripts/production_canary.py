#!/usr/bin/env python3
"""Daily production canary for farmer-critical KrishiMitra dependencies."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


class CanaryFailure(RuntimeError):
    pass


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    token: str = "",
    timeout: float = 15,
) -> tuple[int, Dict[str, Any], float]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    elapsed_ms = (time.monotonic() - started) * 1000
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise CanaryFailure(f"Non-JSON response from {url}: HTTP {status}") from exc
    return status, data, elapsed_ms


def run_canary(api_base: str, phase1_base: str = "", phase1_token: str = "") -> Dict[str, Any]:
    api = api_base.rstrip("/")
    report: Dict[str, Any] = {"status": "running", "checks": {}}

    def check(name: str, url: str, *, expected=(200,), **kwargs):
        status, data, elapsed = _request(url, **kwargs)
        report["checks"][name] = {
            "http_status": status,
            "latency_ms": round(elapsed),
            "status": data.get("status"),
        }
        if status not in expected:
            raise CanaryFailure(f"{name} returned HTTP {status}")
        return data, elapsed

    check("api_health", f"{api}/api/health/")
    readiness, _ = check("launch_readiness", f"{api}/api/health/launch-readiness/?strict=true")
    if readiness.get("status") != "ready":
        raise CanaryFailure(f"strict launch readiness is {readiness.get('status')}")

    latitude = os.getenv("CANARY_LATITUDE") or "26.8467"
    longitude = os.getenv("CANARY_LONGITUDE") or "80.9462"
    commodity = os.getenv("CANARY_COMMODITY") or "Wheat"
    location_query = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": "25",
    })
    location, _ = check("gps_resolution", f"{api}/api/locations/reverse/?{location_query}")
    resolved = location.get("location") or {}
    if not resolved.get("state") or resolved.get("source") in {"default_fallback", "ip_geolocation"}:
        raise CanaryFailure("GPS resolution returned an untrusted location source")

    service_query = urllib.parse.urlencode({
        "location": resolved.get("display_name") or "Lucknow",
        "state": resolved.get("state") or "Uttar Pradesh",
        "latitude": latitude,
        "longitude": longitude,
        "crop": commodity,
    })
    weather, _ = check("weather", f"{api}/api/weather/?{service_query}")
    if not weather.get("is_live") or weather.get("freshness") != "live":
        raise CanaryFailure("weather provider did not return fresh live observations")

    market, _ = check("official_mandi", f"{api}/api/market-prices/?{service_query}")
    market_rows = (market.get("top_crops") or []) + (market.get("prices") or [])
    has_synthetic_row = any(
        "estimate" in str(row.get("price_source") or row.get("source") or "").lower()
        or row.get("supplemented") is True
        for row in market_rows
        if isinstance(row, dict)
    )
    if has_synthetic_row or market.get("_auto_estimates"):
        raise CanaryFailure("mandi response contains prohibited estimated prices")
    report["checks"]["official_mandi"]["coverage"] = market.get("coverage_status") or market.get("status")
    report["checks"]["official_mandi"]["is_live"] = bool(market.get("is_live"))

    greeting, elapsed = check(
        "chatbot_greeting",
        f"{api}/api/chatbot/query/",
        method="POST",
        payload={
            "query": "नमस्ते",
            "language": "hi",
            "location": resolved.get("display_name") or "Lucknow",
            "latitude": float(latitude),
            "longitude": float(longitude),
            "location_confirmed": True,
            "fast_mode": True,
        },
    )
    app_latency = greeting.get("response_time_ms", elapsed)
    if app_latency >= 500:
        raise CanaryFailure(f"greeting latency {app_latency}ms exceeds 500ms")

    if phase1_base:
        phase1 = phase1_base.rstrip("/")
        health, _ = check("phase1_health", f"{phase1}/health")
        if health.get("status") not in {"healthy", "running"}:
            raise CanaryFailure("Phase 1 health is degraded")
        rag, _ = check("phase1_rag", f"{phase1}/rag/status", token=phase1_token)
        if not (rag.get("ready") or rag.get("status") in {"ready", "healthy"}):
            raise CanaryFailure("Phase 1 RAG index is not ready")

    canary_phone = os.getenv("CANARY_OTP_PHONE", "").strip()
    if canary_phone:
        otp, _ = check(
            "otp_delivery",
            f"{api}/api/users/otp/request/",
            method="POST",
            payload={"phone_number": canary_phone},
        )
        if otp.get("status") not in {"sent", "success"}:
            raise CanaryFailure("OTP provider did not accept the canary delivery")
    else:
        report["checks"]["otp_delivery"] = {"status": "not_configured", "required_for_launch": True}

    report["status"] = "passed"
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default=os.getenv("CANARY_API_BASE_URL", ""))
    parser.add_argument("--phase1-base", default=os.getenv("CANARY_PHASE1_BASE_URL", ""))
    parser.add_argument("--phase1-token", default=os.getenv("PHASE1_SERVICE_TOKEN", ""))
    parser.add_argument("--json", dest="json_path")
    args = parser.parse_args()
    if not args.api_base:
        parser.error("--api-base or CANARY_API_BASE_URL is required")
    try:
        report = run_canary(args.api_base, args.phase1_base, args.phase1_token)
        exit_code = 0
    except Exception as exc:
        report = {"status": "failed", "error": str(exc)}
        exit_code = 1
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.json_path:
        Path(args.json_path).write_text(output + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
