# Remediation Test Results

2026-09-14, macOS ARM64. Current worktree; no production deployment.
Earlier evidence: `audit/historical/2026-09-14/` (including the previous workspace report).

## Results

Automatic-input follow-up: backend suite rerun with 392 tests, one existing skip
(14.19s). Four new regression tests cover owned, matching-location profile reuse,
explicit overrides, account isolation and missing coordinates. Frontend build and
static UI contract passed again. Chromium desktop/mobile rerun: 36 passed, two
existing device-scope skips (11.7s). The earlier saved logs below precede this follow-up.

| Check | Result | Evidence / limitation |
|---|---|---|
| Python compileall backend/phase1/scripts/trainer | PASS | Python 3.12 isolated environment |
| Django system check | PASS | No issues |
| Migration drift | PASS | No changes detected; no new migrations |
| Full backend suite | PASS: 388 tests, 1 existing skip, 24.33s | `audit/remediation/backend-final.log`; SQLite, not PostgreSQL |
| Separate actual-backend browser journey | PASS: 1 journey | `real-backend-final.log`; actual Django/DB, only SMS boundary substituted |
| Backend-unavailable negative control | Expected failure, exit 1 | `backend-unavailable-negative.log`, ECONNREFUSED on unused port 4199 |
| Chromium desktop/mobile contracts | PASS: 36, 2 existing device-scope skips | `browser-final.log`; APIs mocked in this suite |
| Firefox/WebKit contracts | PASS: 36, 2 existing device-scope skips | `cross-browser-final.log`; APIs mocked |
| UI static contract | PASS | 168 static IDs, 7 services, 22 handlers; removed decorative counter, not a service |
| Required translations | PASS structurally | 118 required HTML keys; 155/155 dictionary entries for hi/en. Does NOT count hardcoded legacy strings or establish linguistic quality |
| Frontend build | PASS | Vite 6.4.3; macOS dependencies work, historical architecture error not reproduced |
| npm audit | PASS | 0 reported vulnerabilities |
| pip check | PASS | Installed dependency consistency only |
| pip-audit installed environment | FAIL: 3 ChromaDB advisories | `python-dependency-audit-final.json`; no listed fixed version. No new suppressions added |
| Pre-push checker | PASS: 25/25 | `prepush.log`; no push performed |
| Whitespace/diff check | PASS | `git diff --check` |
| Open-Meteo live via local API | PASS sampled request | HTTP200, 3.21s, Lucknow coordinates; observation timestamp present |
| Agmarknet live request | PARTIAL | HTTP200, 3.79s; no fresh exact-mandi row; Sept12 official state reference rows labelled dated, not live |
| Public Render health | PASS liveness only | `https://agri-advisory-web.onrender.com/api/health/` returned HTTP200 / OK |
| Intended production revision | NOT VERIFIED | Current changes have not been pushed or deployed |
| Docker / PostgreSQL / Redis / workers | BLOCKED | Docker socket absent; no shared-service verification |

The earlier local baseline had 380 tests with 11 failures, 1 error and 1 skip. It
included newly added regression tests and was not a pristine historical baseline.
`backend-baseline.log` is preserved. Red OTP and red profile/chat logs preserve
the reproduced failures before repairs. Browser failures were inspected: source
compatibility, focus restoration, RTL navbar overflow and an isolated test-server
collision were corrected. Assertions were not mass-deleted or skipped.

## Reproduce safely

Use a new virtual environment, never the system Python 3.9 environment:

```sh
python3.12 -m venv /tmp/krishimitra-remediation-venv
/tmp/krishimitra-remediation-venv/bin/pip install -r backend/requirements.txt
cd frontend
npm ci
npx playwright install chromium firefox webkit
npm run test:ui
npm run test:i18n
npm run build
npm audit --audit-level=high
npm run test:e2e
CROSS_BROWSER=1 PLAYWRIGHT_PORT=4183 npx playwright test --project=firefox --project=webkit
cd ../backend
export PYTHON_DOTENV_DISABLED=1 DEBUG=True
export DATABASE_URL=sqlite:////tmp/km-remediation-unit.sqlite3
export REDIS_URL= SENTRY_DSN= RATE_LIMIT_ENABLED=false
/tmp/krishimitra-remediation-venv/bin/python manage.py check
/tmp/krishimitra-remediation-venv/bin/python manage.py makemigrations --check --dry-run
/tmp/krishimitra-remediation-venv/bin/python manage.py test advisory.tests --noinput
/tmp/krishimitra-remediation-venv/bin/python manage.py test advisory.tests.browser_journeys --noinput
cd ..
/tmp/krishimitra-remediation-venv/bin/python -m compileall -q backend phase1 scripts custom_llm_trainer
/tmp/krishimitra-remediation-venv/bin/python scripts/check_before_push.py
```

Run the two Playwright commands sequentially, or use separate ports; do not share
a Vite process owned by another runner. The actual-backend journey owns port4197
and a dynamic Django test port. It creates a test DB and a temporary OTP capture
file inside the test process only. No deployable OTP-capture endpoint or runtime
production switch was introduced.

For the local preview, use the isolated environment above with a **new** disposable
database path `/tmp/km-remediation-web.sqlite3`, run migrations on that database
only, start Django on8000, and Vite on4193. No service credentials are loaded while
`PYTHON_DOTENV_DISABLED=1`; missing providers must remain unavailable/fallback.

## Browser inspection and performance

`audit/remediation/baseline/` and `after/` contain 8 views at widths320/360/768/1440,
height900. The after set has zero measured horizontal overflow. Baseline captures
included an in-progress fade animation and were made before the isolated API was
started, so they are not a controlled visual-diff benchmark. Final screenshots
disable animation. Native Urdu layout was also exercised in automated tests.

Screens inspected directly include the 320px crop form, desktop home, sign-in
dialog, and Firefox/WebKit failure screenshots before the RTL repair. The manual
local search selected Lucknow without personal GPS; live weather/mandi requests
used public district coordinates. All seven service panels were captured; that
is not evidence that every provider-dependent button completed successfully.

Local unthrottled Chromium/Vite measurements (`local-performance.jsonl`): cold
FCP100ms, 17 resources, 1,282,437 transferred bytes; repeat FCP40ms, 5,102 bytes.
CPU/network throttling was not applied. These figures do not predict Render cold
starts, slow rural networks or actual device performance.

## Coverage counts and remaining gaps

The revised 83-row matrix has **49 PASS, 10 PARTIAL, 6 BLOCKED, 18 NOT RUN**.
Historical status remains a separate column. No missing required coverage is
called NOT APPLICABLE. Some PASS entries cover a named boundary only, not an entire
service; read the verification column.

Still unverified: full production revision/readiness, real SMS delivery, live
RAG/model output, production classifier execution, all hardware/worker actions,
all six field actions as connected browser journeys, actual audio playback,
trending routes, comprehensive enlarged-text/screen-reader checks, representative
load/soak, complete translations and farmer usability sessions.
