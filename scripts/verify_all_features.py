#!/usr/bin/env python3
"""
Verify all farmer-facing features return proper data for multiple locations.

Usage:
    python3 scripts/verify_all_features.py
    python3 scripts/verify_all_features.py --json
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ.setdefault("SECRET_KEY", "verify-local")
os.environ.setdefault("DATABASE_URL", "sqlite:///verify_features.sqlite3")

import django

django.setup()

from rest_framework.test import APIClient  # noqa: E402

FEATURES = [
    ("🏛️ सरकारी योजनाएं", "GET", "/api/schemes/"),
    ("🌾 फसल सुझाव", "GET", "/api/advisories/"),
    ("🌤️ मौसम", "GET", "/api/weather/"),
    ("💰 बाजार कीमतें", "GET", "/api/market-prices/"),
    ("🐛 KrishiRaksha", "POST", "/api/diagnostics/detect/"),
    ("🤖 AI सहायक", "POST", "/api/chatbot/query/"),
]

LOCATIONS = ["Delhi", "Mumbai", "Bangalore"]


def classify_source(body: dict) -> str:
    if not isinstance(body, dict):
        return str(body)[:80]
    return (
        body.get("data_source")
        or body.get("source")
        or body.get("status")
        or "ok"
    )


def is_realtime_weather(source: str) -> bool:
    s = (source or "").lower()
    return "open-meteo" in s or "openweathermap" in s


def is_realtime_market(body: dict) -> bool:
    if body.get("status") == "fallback":
        return False
    source = (body.get("data_source") or "").lower()
    return "data.gov.in" in source or "agmarknet" in source or "enam" in source


def run(json_out: bool):
    client = APIClient()
    report = []

    for feature_name, method, path in FEATURES:
        row = {"feature": feature_name, "path": path, "locations": {}}
        for loc in LOCATIONS:
            if method == "GET":
                resp = client.get(path, {"location": loc})
            elif path.endswith("detect/"):
                resp = client.post(
                    path,
                    {"crop": "tomato", "location": loc, "images": {}, "session_id": f"v-{loc}"},
                    format="json",
                )
            else:
                resp = client.post(
                    path,
                    {"query": "गेहूँ MSP", "location": loc, "language": "hi"},
                    format="json",
                )
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.content.decode("utf-8", errors="replace")[:200]}
            source = classify_source(body)
            entry = {
                "http": resp.status_code,
                "source": source,
            }
            if "weather" in path:
                cur = (body.get("current") or body.get("current_weather") or {}) if isinstance(body, dict) else {}
                entry["temp_c"] = cur.get("temperature")
                entry["realtime"] = is_realtime_weather(str(source))
            if "market-prices" in path and isinstance(body, dict):
                entry["realtime"] = is_realtime_market(body)
                entry["status"] = body.get("status")
                top = (body.get("top_crops") or [])[:1]
                if top:
                    entry["sample"] = f"{top[0].get('crop_name')} ₹{top[0].get('modal_price')}/q"
            if "schemes" in path and isinstance(body, dict):
                entry["scheme_count"] = body.get("total")
            if "diagnostics" in path and isinstance(body, dict):
                entry["crop"] = body.get("crop_detected")
                entry["diagnosis_count"] = len(body.get("diagnosis") or [])
            if "chatbot" in path and isinstance(body, dict):
                entry["response_preview"] = (body.get("response") or "")[:60]
            row["locations"][loc] = entry
        report.append(row)

    if json_out:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    print("\n" + "=" * 72)
    print("  KrishiMitra — Feature verification (live API)")
    print("=" * 72)
    for row in report:
        print(f"\n{row['feature']}  {row['path']}")
        print("-" * 72)
        for loc, info in row["locations"].items():
            line = f"  {loc:12} HTTP {info['http']}  |  {info['source']}"
            if "temp_c" in info:
                rt = "✅ realtime" if info.get("realtime") else "⚠️ fallback"
                line += f"  |  {info['temp_c']}°C  {rt}"
            if "sample" in info:
                rt = "✅ live mandi" if info.get("realtime") else "⚠️ MSP estimate"
                line += f"  |  {info['sample']}  {rt}"
            if "scheme_count" in info:
                line += f"  |  {info['scheme_count']} schemes"
            if "crop" in info:
                line += f"  |  {info['crop']} ({info['diagnosis_count']} diagnoses)"
            if "response_preview" in info:
                line += f"\n               → {info['response_preview']}…"
            print(line)
    print("\n" + "=" * 72)
    print("  Notes:")
    print("  • Weather: Open-Meteo = real-time by GPS/city coordinates")
    print("  • Market: data.gov.in when reachable; else MSP seasonal estimate (labeled)")
    print("  • Schemes: official 2024-25 catalog (PM-Kisan, PMFBY, KCC, PM-KUSUM, …)")
    print("  • Re-run: python scripts/verify_all_features.py")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    run(args.json)
