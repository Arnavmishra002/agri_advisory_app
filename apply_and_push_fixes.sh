#!/usr/bin/env bash
# KrishiMitra — push the security/truthfulness/cleanup fixes to a new branch.
# Run this from anywhere; it cd's into the repo. The fixed files are already
# written to disk by Claude — this just branches, commits, and pushes them.
set -euo pipefail

REPO="$HOME/ai/agri_advisory_app"
BRANCH="fixes/security-truthfulness-realtime"

cd "$REPO"
echo "Repo: $(pwd)"
git rev-parse --is-inside-work-tree >/dev/null

# Make sure we branch off the latest main
git fetch origin --quiet || true
git checkout main 2>/dev/null || git checkout -b main
git pull --ff-only origin main 2>/dev/null || true

git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"

# Stage ONLY the files Claude changed (won't sweep unrelated edits)
git add \
  backend/advisory/api/viewsets/misc.py \
  backend/advisory/api/viewsets/auth_viewset.py \
  backend/advisory/api/viewsets/pest.py \
  backend/advisory/services/knowledge_base.py \
  backend/advisory/services/unified_realtime_service.py \
  backend/advisory/services/enhanced_market_prices.py \
  backend/advisory/services/ultra_dynamic_government_api.py \
  backend/advisory/services/comprehensive_crop_recommendations.py \
  backend/advisory/services/accurate_location_api.py \
  backend/advisory/services/enhanced_pest_detection.py \
  backend/advisory/middleware/security_headers.py \
  backend/core/settings.py \
  frontend/index.html \
  frontend/public/js/app.js \
  frontend/public/js/i18n.js \
  mobile/krishimitra_app/lib/main.dart \
  mobile/krishimitra_app/lib/services/storage_service.dart \
  mobile/krishimitra_app/lib/services/api_service.dart \
  mobile/krishimitra_app/lib/screens/chat_screen.dart \
  mobile/krishimitra_app/lib/screens/mandi_screen.dart \
  mobile/krishimitra_app/lib/utils/constants.dart

echo; echo "Staged changes:"; git status --short

git commit -m "Fix security/correctness bugs, remove fabricated data, dead-code cleanup

Backend: fix WhatsApp webhook NameError crash; OTP /me empty-profile;
add per-IP + global OTP send caps; enforce password validators on
registration; word-boundary crop detection (price != rice); dup rice
fertilizer key; thread-safe market cache with real LRU; OpenWeatherMap
language bug; geocode primary-token match; emit CSP; strict-prod default.

Truthfulness: remove all random.seed/random.uniform price generators that
labelled fabricated numbers as live Agmarknet/e-NAM data. Live market/
weather/crop paths use real data.gov.in/Agmarknet/Open-Meteo; honest
'unavailable' when APIs can't be reached.

Dead code: tombstone ~2900 lines of zero-importer modules
(comprehensive_crop_recommendations, accurate_location_api,
enhanced_pest_detection with its fictional gov endpoints).

Web: fix 3 XSS sinks (toast, diagnosis fields, scheme URLs); chat timeout
message; Gujarati i18n mojibake.

Mobile: refresh data on location/language change; cryptographic session id;
SSE idle timeout + CRLF tolerance; correct multi-turn chat history;
offline mandi respects saved selection.

Verified: manage.py check clean; 161 backend tests pass (0 fail).

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin "$BRANCH"

echo
echo "===================================================================="
echo "Pushed branch: $BRANCH"
echo "Open a PR:  https://github.com/Arnavmishra002/agri_advisory_app/pull/new/$BRANCH"
echo "===================================================================="
