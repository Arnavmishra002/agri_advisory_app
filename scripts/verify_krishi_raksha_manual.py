#!/usr/bin/env python3
"""Manual KrishiRaksha verification (laptop vs leaf) against running API."""

from __future__ import annotations

import base64
import io
import json
import sys

import requests
from PIL import Image

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def _jpeg_b64(color_or_factory, size=(320, 240)) -> str:
    if callable(color_or_factory):
        img = color_or_factory(size)
    else:
        img = Image.new("RGB", size, color=color_or_factory)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _green_leaf(size):
    img = Image.new("RGB", size, color=(40, 120, 50))
    w, h = size
    for x in range(0, w, 16):
        for y in range(0, h, 16):
            for dx in range(8):
                for dy in range(8):
                    if x + dx < w and y + dy < h:
                        img.putpixel((x + dx, y + dy), (55, 150, 60))
    return img


def detect(crop: str, image_data_url: str | None) -> dict:
    payload = {
        "crop": crop,
        "location": "Delhi",
        "latitude": 28.6139,
        "longitude": 77.209,
        "session_id": "verify_manual",
        "images": {},
    }
    if image_data_url:
        payload["images"] = {"close_up": image_data_url}
    r = requests.post(f"{BASE}/api/diagnostics/detect/", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def main() -> int:
    print(f"API base: {BASE}\n")

    # Health
    try:
        h = requests.get(f"{BASE}/api/health/", timeout=5)
        print(f"Health: {h.status_code} {h.text.strip()}")
    except requests.RequestException as exc:
        print(f"ERROR: Server not reachable at {BASE} — start with: python manage.py runserver")
        print(exc)
        return 1

    print("\n--- 1) Rice + NO image (expect photo_required, no Rice Blast) ---")
    r1 = detect("rice", None)
    print(f"status: {r1.get('status')}")
    print(f"message: {r1.get('message', '')}")
    names = [d.get("name", "") for d in r1.get("diagnosis", [])]
    print(f"diagnosis names: {names}")
    ok1 = r1.get("status") == "photo_required" and not any("Rice Blast" in n for n in names)
    print("PASS" if ok1 else "FAIL")

    print("\n--- 2) Rice + laptop-like gray image (expect not_plant) ---")
    laptop = _jpeg_b64((130, 132, 138))
    r2 = detect("rice", laptop)
    print(f"status: {r2.get('status')}")
    print(f"message: {r2.get('message', r2.get('ml_prediction', {}).get('message', ''))}")
    names2 = [d.get("name", "") for d in r2.get("diagnosis", [])]
    print(f"diagnosis names: {names2[:2]}")
    ok2 = r2.get("status") == "not_plant" and not any("Rice Blast" in n for n in names2)
    print("PASS" if ok2 else "FAIL")

    print("\n--- 3) Rice + synthetic green leaf (expect model_unavailable OR success if trained) ---")
    leaf = _jpeg_b64(_green_leaf)
    r3 = detect("rice", leaf)
    print(f"status: {r3.get('status')}")
    mp = r3.get("ml_prediction") or {}
    print(f"ml_prediction.status: {mp.get('status')}")
    print(f"message: {r3.get('message', mp.get('message', ''))}")
    names3 = [d.get("name", "") for d in r3.get("diagnosis", [])]
    print(f"diagnosis names: {names3[:2]}")
    ok3 = r3.get("status") in (
        "model_unavailable",
        "tensorflow_missing",
        "success",
        "low_confidence",
    ) and not any("Rice Blast" in n and r3.get("status") == "success" for n in names3)
    # Without trained model we expect model_unavailable/tensorflow_missing, never fake Rice Blast
    if r3.get("status") in ("model_unavailable", "tensorflow_missing"):
        ok3 = ok3 and not any("Rice Blast" in n for n in names3)
    print("PASS" if ok3 else "FAIL")

    all_ok = ok1 and ok2 and ok3
    print("\n" + ("All checks PASSED" if all_ok else "Some checks FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
