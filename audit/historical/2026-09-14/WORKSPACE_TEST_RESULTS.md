# TEST_RESULTS.md — KrishiMitra audit execution log

**Audit date:** 14 September 2026
**Repository:** `Arnavmishra002/agri_advisory_app`
**Revision under test:** `8d113d05edf14bc17b6dc33e2038b1c80ef2686d`
**Branch:** `codex/farmer-readiness-repairs`
**Working tree at start:** dirty — `.github/workflows/deploy.yml` and `backend/requirements.txt`
modified, `backend/advisory/tests/test_deploy_pipeline_honesty.py` untracked (all from a
prior session, preserved unchanged).

## Environments

Two environments were used. Every result below states which one produced it,
because several apparent failures were environment artifacts and are retracted.

| | ENV-A — user's machine (device bridge) | ENV-B — cloud container (fresh clone) |
|---|---|---|
| Python | 3.10.12 | 3.11.15 |
| Django | 5.2.17 | 5.2.17 |
| Node | 22.23.2 | 22.22.2 |
| Outbound network | none (proxy 403 to all upstreams) | allow-listed only |
| Browser | none reachable from the shell | Chromium build 1194 + Playwright |
| DB | SQLite test DB (in-memory) | SQLite at `/tmp/audit.sqlite3` |

ENV-B was created with `git clone --depth 1 --branch codex/farmer-readiness-repairs`
at the same revision. No production system was contacted, no data was deleted, no
message or SMS was sent, no paid service was called.

## Commands executed

### ENV-A — backend suite (baseline)

```
cd backend && DEBUG=True python manage.py test advisory.tests --verbosity 1
```
```
Ran 357 tests in 34.339s
FAILED (failures=1, skipped=1)
FAIL: test_a_dated_official_reference_is_built_from_them
      (advisory.tests.test_market_district_scoping.DatedOfficialReferenceSurvivesLiveFilterTests)
AssertionError: 0 != 2
```
Exit code 1. **Pre-existing failure — present before any audit change.** Root cause
established below (ISSUE-01).

### ENV-A — audit probes added by this audit

```
cd backend && DEBUG=True python manage.py test advisory.tests.test_audit_authz_probe
Ran 5 tests in 0.621s — OK

cd backend && DEBUG=True python manage.py test advisory.tests.test_audit_journeys
Ran 11 tests in 6.213s — OK
```

Both suites were first run in a deliberately stricter form; four assertions failed,
each was investigated, and **all four were retracted as bad assertions rather than
reported as defects**. See "Retracted findings".

### ENV-A — frontend

```
cd frontend && npm run test:ui    → exit 0
   UI contract passed: 169 unique IDs, 7 services, 22 handlers.

cd frontend && npm run build      → exit 1  (BLOCKED, environment)
   Error: Cannot find module @rollup/rollup-linux-arm64-gnu
```
The installed `node_modules` was built for a different architecture than the Linux VM
the bridge shell runs in. Not an application defect — the same build succeeds in ENV-B
(below) and on CI. Recorded BLOCKED, not FAIL. No attempt was made to delete or
reinstall the user's `node_modules`.

### ENV-B — dependency install

```
pip install -r backend/requirements.txt
   ERROR: Failed building wheel for paho-mqtt   (paho-mqtt==1.6.1)
   ERROR: Could not find a version that satisfies the requirement paho-mqtt==1.6.1
          (from versions: 2.0.0rc2, 2.0.0, 2.1.0)
```
Retracted as environment-specific: this container reaches a filtered package index.
CI (`KrishiMitra CI` run #140, Python 3.11) installs the same file successfully.
All other packages installed; `paho-mqtt` was excluded to proceed. The MQTT worker is
already commented out in `render.yaml`, so nothing under test depends on it.

### ENV-B — application under test

```
python manage.py migrate --noinput                      → OK
python manage.py runserver 127.0.0.1:8199 --noreload     → serving
python3 /tmp/serve_audit.py                              → static + /api proxy on :8200
curl /  /js/app.js  /css/styles.css  /api/health/        → 200 200 200 200
```
A purpose-written static server + `/api` reverse proxy was used because the frontend
calls the API same-origin. It is an audit fixture only and was never committed.

### ENV-B — frontend build and contract

```
cd frontend && npm install --no-audit --no-fund   → added 17 packages
cd frontend && npm run test:ui                    → exit 0, 169 IDs
cd frontend && npm run build                      → exit 0, built in 219ms
   dist/index.html                 93.24 kB │ gzip: 20.16 kB
   dist/assets/index-C2QL5mj8.css  59.81 kB │ gzip: 12.08 kB
```
The build that is BLOCKED in ENV-A **passes in a clean clone**. This confirms the
ENV-A failure is local `node_modules` state, not the repository.

### ENV-B — project's own end-to-end suite

First run, unmodified config:
```
npx playwright test --reporter=line
   24 failed
   Error: browserType.launch: Executable doesn't exist at
   /opt/pw-browsers/chromium_headless_shell-1228/chrome-headless-shell-linux64/...
```
All 24 failures were one cause: the project pins a Playwright version expecting browser
build **1228**; this container has **1194**, and downloading browsers is disallowed here.
Re-run with an audit-only config that points the same tests at the available binary:
```
npx playwright test -c playwright.audit.config.mjs --reporter=line
   2 skipped
   22 passed (49.2s)
```
**The project's e2e suite is healthy.** The 2 skips are `test.skip(...)` project scoping —
the desktop navigation test skips on the mobile project and vice versa, so each runs
exactly once. Recorded NOT APPLICABLE, not hidden coverage.

One characteristic worth recording: every spec calls `page.route('**/api/**', ...)` and
fulfils it locally. The suite ran to green with **no backend running at all** (the vite
proxy logged `ECONNREFUSED 127.0.0.1:8000` throughout). The e2e tests therefore verify
frontend logic against mocked contracts, never the real API.

### ENV-B — browser audit (written for this audit)

```
node audit/browser_audit.mjs     → audit/browser_audit.json + 5 screenshots
node audit/lang_audit.mjs        → audit/lang_audit.json
node audit/rtl.mjs
node audit/perf.mjs
```
Browser: Chromium 1194, headed-equivalent headless. Viewports actually tested:
**320×568, 360×640, 768×1024, 1440×900.** Only Chromium was tested — no Firefox or
WebKit binary is available here, so cross-browser behaviour is **NOT RUN**.

Results:

| Check | Result |
|---|---|
| Horizontal overflow | **0 px at all four viewports** (scrollWidth == clientWidth) |
| Elements overflowing viewport | **0** |
| Tap targets under 24×24 px | **0** |
| Console errors | 1 per viewport — the Google Fonts request (ISSUE-02) |
| Failed network requests | 1 per viewport — same |
| `<h1>` count / heading skips | 1 / none |
| Images without `alt` | 0 |
| Controls with no accessible name | 0 |
| `<main>` landmark | **0** — ISSUE-07 |
| Inputs with no label or aria-label | **2** — ISSUE-08 |
| Tab stops with no visible focus | **3 of 18** — ISSUE-09 |
| `dir="rtl"` for ur / sd / ks | correct |
| `lang` attribute tracks the switcher | correct for all 22 options |

### ENV-B — performance (method stated, not extrapolated)

Measured on localhost against the **uncompressed** audit static server, cold cache,
1440×900, Chromium 1194:

```
goto → load (wall):      538 ms
domContentLoaded:        445 ms
first-contentful-paint:  500 ms
requests:                17
total transfer:          1,070 KB (uncompressed)

largest assets: bootstrap.min.css 228 KB · app.js 189 KB · fa-solid-900.woff2 147 KB
                styles.css 101 KB · all.min.css 100 KB · i18n.js 87 KB
                bootstrap.bundle.min.js 79 KB
```

**These are not production transfer sizes.** Production uses
`whitenoise.storage.CompressedManifestStaticFilesStorage` and `nginx.conf` enables gzip,
so text assets compress roughly 3–4× on the wire. The woff2 font is already compressed
and does not shrink further. Nothing here should be read as a production scalability
measurement — it is a single local cold load on one machine.

## Blockers and limitations

| Area | Status | Why |
|---|---|---|
| Live upstream integrations (Agmarknet, Open-Meteo, MET Norway, Twilio, Gemini/Ollama) | **BLOCKED** | Both environments are network-restricted; every upstream returned proxy 403. Behaviour was verified only in the *total-failure* path. Success paths are unverified. |
| Cross-browser (Firefox, WebKit, Safari, real mobile) | **NOT RUN** | No engine other than Chromium available; no device lab. |
| Production database behaviour (PostgreSQL) | **NOT RUN** | Both environments used SQLite. Constraints, index behaviour and migration timing under PostgreSQL are unverified. |
| Redis-backed rate limiting and cache | **NOT RUN** | No Redis. Limiters were exercised against the locmem fallback only; cross-worker behaviour is untested. |
| Background jobs / Celery / MQTT worker | **NOT RUN** | No broker; the MQTT worker is commented out in `render.yaml`. |
| Disease model inference (TFLite) | **NOT RUN** | Model serving path not exercised; `disease_mode` reported `advisory_fallback` throughout. |
| Load / concurrency / soak | **NOT RUN** | Out of scope for a single-machine audit; no representative workload available. |
| `frontend` build in ENV-A | **BLOCKED** | Architecture-mismatched `node_modules`; passes clean in ENV-B. |

## Retracted findings

Each of these looked like a defect and was disproved before reporting.

1. **"launch-readiness leaks DATABASE_URL."** The response contains the *variable name*
   inside remediation advice — `"action": "Set DATABASE_URL to the managed PostgreSQL
   connection string."` A regex for `postgres://` and for any 32+ character token found
   **0 matches**. A name in advice is not a leak. Probe corrected.
2. **"requirements.txt has a numpy/opencv conflict."** `pip check` flagged three
   `opencv-*` packages needing `numpy>=2`. `opencv` is not in `requirements.txt` and
   `pip show` reports `Required-by:` nothing — it is pre-installed in the container image.
3. **"paho-mqtt 1.6.1 is uninstallable."** Index-specific to this container; CI installs it.
4. **"`/api/market-prices/mandi-prices/` returns 400."** That is the documented contract —
   `mandi` is required — and `frontend/public/js/app.js:1621` only calls it inside
   `if (currentMandi && currentMandi.trim())`. The audit test called it wrong.
5. **"Reflected XSS in the chat endpoint."** `<script>alert(1)</script>` is echoed verbatim
   in `"query"`, but the response is `Content-Type: application/json` with
   `X-Content-Type-Options: nosniff`, and no frontend code renders `data.query` as HTML.
   `renderChatText` (`app.js:285`) escapes *before* applying its markdown pass, so the
   pass cannot reconstruct a tag. Downgraded to a hardening note (ISSUE-12), not a
   confirmed vulnerability.
6. **"24 e2e failures."** Browser build mismatch; 22/22 pass on the available binary.

## Files created or modified by this audit

On the user's machine (`~/ai/agri_advisory_app`):

| File | Action | Note |
|---|---|---|
| `backend/advisory/tests/test_audit_authz_probe.py` | **created** | 5 tests, all passing |
| `backend/advisory/tests/test_audit_journeys.py` | **created** | 11 tests, all passing |
| `audit/baseline_backend_debugTrue.log` | created | raw suite output |
| `audit/baseline_ui_contract.log` | created | raw output |
| `audit/baseline_build.log` | created | raw output |
| `backend/_to_delete/` | created | 12 throwaway probe scripts moved here; the bridge cannot delete files, so they are parked for you to remove |
| `AUDIT_REPORT.md`, `FEATURE_TEST_MATRIX.csv`, `TEST_RESULTS.md` | created | these deliverables |

**No application code, configuration, schema, dependency pin or test outside the two new
`test_audit_*` files was changed.** The three files already modified when the audit began
were left exactly as they were.

In the cloud container only (never committed): `/home/claude/km` clone,
`audit/browser_audit.mjs`, `audit/lang_audit.mjs`, `audit/rtl.mjs`, `audit/perf.mjs`,
`frontend/playwright.audit.config.mjs`, `/tmp/serve_audit.py`.
