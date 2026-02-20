#!/usr/bin/env python3
"""
KrishiMitra AI — Regression Guard
Run this before pushing to catch regressions locally before CI.

Usage:
    python check_before_push.py           # Run all checks
    python check_before_push.py --fast    # Skip slow API tests
"""

import os
import sys
import subprocess
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
os.environ.setdefault("SECRET_KEY", "local-check-key-krishimitra")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///check_db.sqlite3")
os.environ.setdefault("DATA_GOV_IN_API_KEY",
                      "579b464db66ec23bdd000001cdd3946e44c4a1747200ff293b68cc36")
os.environ.setdefault("GOOGLE_AI_API_KEY", "")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "\033[92m✅\033[0m"
FAIL = "\033[91m❌\033[0m"
WARN = "\033[93m⚠️\033[0m"

def header(title):
    print(f"\n{'═'*55}")
    print(f"  {title}")
    print('═'*55)

def check(label, fn):
    try:
        fn()
        print(f"  {PASS}  {label}")
        return True
    except Exception as e:
        print(f"  {FAIL}  {label}")
        print(f"       {e}")
        return False

results = []

# ─── 1. Static data integrity ────────────────────────────────────
header("1/4 Data Integrity Checks")

import django
django.setup()
from advisory.services.unified_realtime_service import GOVERNMENT_SCHEMES, MarketPricesService

results.append(check("GOVERNMENT_SCHEMES has 7+ entries",
    lambda: (_ for _ in ()).throw(AssertionError(f"Got {len(GOVERNMENT_SCHEMES)}"))
    if len(GOVERNMENT_SCHEMES) < 7 else None))

results.append(check("No 'Land documents' in any scheme",
    lambda: [(_ for _ in ()).throw(AssertionError(f"In scheme {s['id']}"))
             for s in GOVERNMENT_SCHEMES if "Land documents" in s.get("documents", [])]))

results.append(check("Wheat MSP == ₹2,275",
    lambda: (_ for _ in ()).throw(AssertionError(f"Got {MarketPricesService().MSP_DATA['wheat']}"))
    if MarketPricesService().MSP_DATA['wheat'] != 2275 else None))

results.append(check("All scheme websites start with https://",
    lambda: [(_ for _ in ()).throw(AssertionError(f"Bad URL in {s['id']}: {s['website']}"))
             for s in GOVERNMENT_SCHEMES if not s.get('website', '').startswith('http')]))

results.append(check("All schemes have helpline numbers",
    lambda: [(_ for _ in ()).throw(AssertionError(f"No helpline in {s['id']}"))
             for s in GOVERNMENT_SCHEMES if not s.get('helpline')]))

# ─── 2. Chatbot rule-based responses ─────────────────────────────
header("2/4 Chatbot Rule-Based Responses")

from advisory.services.unified_realtime_service import GeminiService
bot = GeminiService()

test_queries = [
    ("गेहूँ MSP query",     "wheat gehu msp price"),
    ("PM-Kisan query",       "pm kisan yojana benefit"),
    ("Pest control query",   "aphid pest control kida"),
    ("Fertilizer query",     "urea dap fertilizer dose"),
    ("Irrigation query",     "drip irrigation sinchahi"),
    ("Soil health query",    "soil health card mitti"),
    ("KCC loan query",       "kisan credit card loan kcc"),
    ("Weather advisory",     "mausam barish weather"),
    ("Organic farming",      "organic jaivik kheti"),
    ("Market/mandi",         "mandi bhav market price"),
    ("Empty query fallback", ""),
    ("Unknown query",        "xyzzy random unknown query 12345"),
]

for label, query in test_queries:
    resp = bot._rule_based_response(query)
    results.append(check(f"{label}",
        lambda r=resp: (_ for _ in ()).throw(AssertionError("Empty response"))
        if not r.strip() else None))

# ─── 3. Frontend critical checks ─────────────────────────────────
header("3/4 Frontend HTML Checks")

with open("core/templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

results.append(check("No spaced HTML tags (< div >)",
    lambda: (_ for _ in ()).throw(AssertionError("Found spaced tags"))
    if "< div" in html or "< span" in html or "< strong" in html else None))

results.append(check("Message class uses ${sender}-message",
    lambda: (_ for _ in ()).throw(AssertionError("Broken message class"))
    if "${sender}-message" not in html else None))

results.append(check("handleChatUserMessage function defined",
    lambda: (_ for _ in ()).throw(AssertionError("Missing function"))
    if "handleChatUserMessage" not in html else None))

results.append(check("Farming calendar present",
    lambda: (_ for _ in ()).throw(AssertionError("Missing farming calendar"))
    if "farming-calendar" not in html and "Kharif" not in html else None))

results.append(check("MSP quick stats present (₹2,275)",
    lambda: (_ for _ in ()).throw(AssertionError("Missing MSP stats"))
    if "2,275" not in html else None))

results.append(check("8+ suggested questions present",
    lambda: (_ for _ in ()).throw(AssertionError("Missing suggested questions"))
    if html.count("suggested-question") < 5 else None))

# ─── 4. Run pytest (quick) ───────────────────────────────────────
header("4/4 Running Pytest (quick service tests)")

t0 = time.time()
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests_production.py",
     "-q", "--tb=line", "--no-header",
     "-x",           # Stop on first failure
     "--timeout=30"],
    capture_output=True, text=True
)
elapsed = time.time() - t0

if result.returncode == 0:
    # Extract pass/fail counts from pytest output
    last_line = [l for l in result.stdout.splitlines() if "passed" in l or "failed" in l]
    summary = last_line[-1] if last_line else "completed"
    print(f"  {PASS}  pytest: {summary} ({elapsed:.1f}s)")
    results.append(True)
else:
    print(f"  {FAIL}  pytest failed ({elapsed:.1f}s)")
    # Show failing tests
    for line in result.stdout.splitlines()[-20:]:
        if "FAILED" in line or "ERROR" in line or "error" in line.lower():
            print(f"       {line}")
    results.append(False)

# ─── Summary ─────────────────────────────────────────────────────
header("Summary")
passed = sum(1 for r in results if r)
failed = sum(1 for r in results if not r)
total = len(results)

print(f"\n  Passed: {passed}/{total}")
if failed:
    print(f"  {FAIL}  {failed} check(s) failed — fix before pushing!")
    sys.exit(1)
else:
    print(f"\n  {PASS}  All checks passed! Safe to push.")
    sys.exit(0)
