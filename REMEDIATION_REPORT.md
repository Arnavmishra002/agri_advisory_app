# KrishiMitra Remediation Report

Date: 2026-09-14. Scope: current web application and backend, not Flutter.
Baseline branch: `codex/farmer-readiness-repairs`; local base revision `8d113d0`.
This is a LOCAL remediation, not a production release. No push, merge, deployment,
billing change, real SMS or real farmer-data deletion was performed.

## Release assessment

Automatic collection follow-up: crop advisory requests now send the signed-in
account's authorization and reuse its explicitly account-bound saved soil/pH and
irrigation at matching stored coordinates. Explicit query inputs take precedence;
`field_input_sources` identifies saved versus request inputs. Missing coordinates
and legacy profiles without explicit account binding do not trigger reuse.
Responses are private/no-store and saved-profile results are excluded from shared
offline storage. Browsing another location no longer silently relocates the saved
farm. Weather, season and official market fetching remain automatic; field
measurements are not invented. Multi-field management and legacy profile migration
remain separate work. This follow-up changes crop personalization, not deployment.

**Not approved for farmer launch.** Major audited code defects have been repaired
and regression-tested, but this report does not claim that the entire implementation
brief is complete. Full translation of legacy service output, all-provider journeys,
distributed infrastructure, model serving and representative farmer validation remain.

| Dimension | Assessment |
|---|---|
| Code | Locally tested repairs; remaining gaps below |
| Integration | Real Django browser journey with isolated SMS; Open-Meteo reached live; Agmarknet returned dated references |
| Deployment | Older Render revision is healthy; this working tree is not deployed |
| Farmer usability | Engineering inspection only; no representative farmer study |

## Evidence integrity

Original attachments are preserved without editing in `audit/historical/2026-09-14/`.
Their CSV has **83 rows: 42 PASS, 15 FAIL, 18 NOT RUN, 7 BLOCKED, 1 NOT APPLICABLE**.
The last category represented missing real-backend coverage (GAP-02), not an exempt feature.
Historical TEST_RESULTS issue references differ from AUDIT_REPORT: the expired fixture
is ISSUE-04 (not ISSUE-01); the external font is ISSUE-13 (not ISSUE-02).
The historical CSV also names eligibility as GET; the implementation supports POST.
Language `/detect/` maps a state to a language; it is not free-text NLP detection.

Existing uncommitted deployment changes, PyYAML requirement, audit tests and
`backend/_to_delete/` were retained. No unrelated cleanup or history rewriting occurred.
The first local backend run already included new regression tests and therefore is
not a pristine reproduction of the historical 357-test baseline.

## Issue tracker

Paths below are relative to the repository. Verification logs are in `audit/remediation/`.

| ID | Reproduced finding / root cause | Fix and changed files | Verification | Current status |
|---|---|---|---|---|
| ISSUE-01 | Historical failed deployments cannot establish current database state | Read-only GitHub deployment/status and public health recheck; no account edits | Deployment 6369231333 succeeded Sept 10 for cbd5f875; public health 200 Sept 14 | SUPERSEDED OR NOT A DEFECT for historical outage; new release still BLOCKED |
| ISSUE-02 | Frontend advanced on success even when SMS was not sent | `frontend/public/js/auth.js`; `backend/advisory/api/viewsets/auth_viewset.py`: require sms_sent=true, acceptance vs delivery metadata, 15s request deadline, duplicate-submit guards, no development OTP shown | auth.spec.js including unsent/expired/timeout; real Django OTP journey | FIXED AND VERIFIED locally; real delivery BLOCKED |
| ISSUE-03 | State-first district lookup invented soil/irrigation; points looked probabilistic | crop_recommendation_engine.py removes borrowed profiles, scores unknowns as unknown, exposes reference district and clarification; app.js renders provenance; chat_intelligence_service.py asks for essential inputs and removes fixed Rabi fallback | test_remediation_contracts, personalization/realtime tests, crop-quality.spec.js | FIXED AND VERIFIED for borrowed facts; conversational ambiguous-place resolution remains OPEN |
| ISSUE-04 | Dated fixture expired against wall clock | test_market_district_scoping.py injects now; test_remediation_contracts covers 24h/7d/future and IST date-only boundaries | Full backend tests | FIXED AND VERIFIED |
| ISSUE-05 | Advertised language support exceeds actual translated content | i18n.js adds coverage export, explicit beta notice, translated service actions/calendar; check-translations.mjs in CI | Translation key check; English/Urdu layout tests | OPEN: legacy dynamic text and fluent review incomplete |
| ISSUE-05a | Bodo used Tibetan code bo | i18n.js, language_service.py, serializers.py and chat greeting use brx; accept stored/request bo as compatibility alias | language compatibility and API normalization tests | FIXED AND VERIFIED |
| ISSUE-05b | Santali silently used Devanagari fallback | i18n.js removes Santali from Devanagari fallback set; English fallback and visible beta label | Translation checker | FIXED AND VERIFIED for fallback policy, not complete Santali translation |
| ISSUE-06 | Missing logout labels in or/as/ur/ne | i18n.js fills keys | Coverage check; fluent review not claimed | IMPLEMENTED, NOT VERIFIED linguistically |
| ISSUE-07 | No main / skip link | index.html semantic main and skip link | accessibility.spec.js | FIXED AND VERIFIED |
| ISSUE-08 | Unnamed location/language controls | index.html and i18n.js localized accessible labels; service titles referenced by aria-labelledby | Browser assertions | FIXED AND VERIFIED for reported controls, not all screen-reader workflows |
| ISSUE-09 | Focus styling overwritten | styles.css focus rule; auth.js explicit focus-return target after Escape | Chromium/Firefox/WebKit keyboard tests | FIXED AND VERIFIED |
| ISSUE-10 | Hook-job success conflated with release success | Existing deploy.yml honesty work preserved; skip describes hook only, acknowledges platform auto-deploy; health explicitly does NOT verify revision | test_deploy_pipeline_honesty | FIXED AND VERIFIED as workflow contract; no workflow dispatched |
| ISSUE-11 | Anonymous production launch-readiness exposed controls | monitoring_views.py staff session/JWT gate before probes; public readiness only availability; CI launch probe requires token | public/nonstaff denial and staff readiness tests | FIXED AND VERIFIED locally |
| ISSUE-12 | Raw query echo alleged unsafe | Existing JSON/nosniff contract preserved; strengthened test must reach HTTP200 rather than return early | test_audit_journeys.ChatInputHandlingTests | SUPERSEDED OR NOT A DEFECT: no confirmed exploitable XSS; regression protected |
| ISSUE-13 | Redundant Google Fonts import blocked by CSP | styles.css import removed; self-hosted fonts retained; CSP not weakened | Build/static inspection and local browser request checks | FIXED AND VERIFIED locally |
| GAP-01 | No connected OTP success path | browser_journeys.py + real-backend-journey.mjs | Browser -> Django -> isolated SQLite; test-only SMS capture | FIXED AND VERIFIED at sandbox-provider boundary |
| GAP-02 | Every old browser spec intercepted APIs | Separate LiveServerTestCase gate and CI step; no API interception in that suite | User/owned profile asserted in DB; unavailable backend fails ECONNREFUSED | FIXED AND VERIFIED for one core journey, not all journeys |
| GAP-03 | No borrowed-profile regression | test_remediation_contracts.py tests exact/uncovered/conflicting/missing inputs | Full backend tests | FIXED AND VERIFIED |
| GAP-04 | No automated accessibility tests | accessibility.spec.js covers landmarks, labels, skip, Escape/focus, 4 widths, RTL | Three browser engines | FIXED AND VERIFIED for specified checks; no WCAG certification |
| GAP-05 | No translation coverage gate | check-translations.mjs + CI | Required hi/en keys, Bodo alias and Santali fallback asserted | FIXED AND VERIFIED structurally; linguistic quality external |
| NEW-01 | Profile POST errors displayed Saved; unsupported user_id sent | app.js checks HTTP/result, preserves failed entries, owned-profile reload, clears on logout, ignores late old-owner UI updates | Real browser saves wheat, reloads form, logs out | FIXED AND VERIFIED |
| NEW-02 | Mobile crop buttons and chat header overflowed | styles.css removes negative header margin, scopes icon-only sizing, gives crop input wrapping space | 32 view screenshots and browser width assertions | FIXED AND VERIFIED |
| NEW-03 | RTL mobile navbar inherited desktop row direction | styles.css confines row-reverse to desktop | Firefox/WebKit regression originally failed, now passes | FIXED AND VERIFIED |
| NEW-04 | Three ChromaDB advisories remain in installed environment | No unverified dependency replacement or new ignore added | pip-audit JSON; existing CI exceptions retained | BLOCKED pending security assessment / patched version or isolation decision |

## Connected journeys

- Actual Django: synthetic OTP request -> captured SMS-boundary acceptance -> code -> JWT ->
  owned profile saved -> token refresh -> page reload restores crop -> logout clears fields/tokens ->
  OTP reuse rejected -> anonymous private profile rejected. No SMS sent.
- Mocked-provider browsers: classic registration/guest migration/logout, password/email auth,
  timeout/expiry, two-turn chat payload, crop provenance, diagnostic advisory/feedback ownership,
  selected-mandi absence and large registry search. These are NOT live-provider success claims.
- Manual local UI: explicit Lucknow search selected the district; weather and other service
  views inspected. Public Open-Meteo request returned real weather in 3.21s; mandi request in
  3.79s returned no current exact quote and dated Sept 12 state references. No substitute prices created.
- Actual API/database: newly added language mapping, Bodo alias/catalog, logout acknowledgment,
  admin staff gate and missing-mandi validation. Admin test uses ordinary static storage;
  it does not establish production collectstatic/CDN health.

## Contract changes

1. Crop `soil_type` and `irrigation` may be null. `input_provenance` uses `unknown` or
   `farmer_supplied`; `reference_profile`/`reference_district`, `guidance_mode`,
   `clarification_required` and `score_interpretation` describe the remaining evidence.
   Clients must not convert null to an assumed irrigation/soil value. Older regional-assumption
   responses still receive an explicit warning in the web UI.
2. OTP response adds `delivery_status` and `delivery_confirmed=false`; sms_sent remains
   acceptance, never guaranteed delivery. The UI advances only on true acceptance.
3. Outside DEBUG, launch-readiness requires staff authentication and returns 403 otherwise.
   Anonymous readiness provides minimal availability. `LAUNCH_READINESS_TOKEN` in CI must
   be a valid staff JWT; an expired token must fail the check, not bypass authorization.
4. Canonical Bodo is brx. Legacy bo is normalized at API/frontend boundaries.

No schema migration was generated. Only a NEW disposable local SQLite database was migrated.

## Remaining work and blockers

| Item | Owner / exact next action | Verification |
|---|---|---|
| Complete language experience | Web engineer: replace remaining hardcoded service/error/footer copy with translation keys; fluent reviewers validate all offered languages | Full string inventory, native-speaker review and long-text journeys, not key counts alone |
| Location conversation | Engineer: add explicit candidate confirmation for ambiguous free-text places without overwriting confirmed GPS | Ambiguous/state-only/conflicting chat-location browser tests |
| Private profile autosave ordering | Engineer: serialize rapid overlapping saves and test delayed responses/refresh-token expiry | Race/failure browser tests; current tests cover ordinary saves only |
| Fresh selected-mandi coverage | Operator: provision legitimate DATA_GOV_IN_API_KEY and measure selected-mandi/nearby coverage; publisher must supply current rows | Date/source/unit/distance checks by district; dated state averages remain separate |
| SMS delivery | Account owner: authorize a sandbox/staging Twilio integration and registered sender configuration | Acceptance, rejection, timeout, delivery receipt, expiry and real device journeys |
| AI serving | Operator: start configured Phase1/Ollama and embedding/index dependencies in staging | Retrieval returns relevant documents; grounded JSON/SSE answers, latency/failure tests |
| Disease classification | ML owner: validate serving runtime, field holdout, negatives and metadata; keep advisory fallback meanwhile | Independent model-quality evidence and actual photo journey; metadata accuracy alone is insufficient |
| PostgreSQL/Redis/workers | Operator: provide disposable services (Docker daemon currently unavailable) | Migrations/constraints, multi-worker limiter, broker retry/dedupe tests |
| ChromaDB security | Security owner: evaluate deployment exposure for CVE-2026-45830/45831/45833; keep untrusted collection mutation unreachable | Document mitigation and rerun audit when a fixed release is available |
| Production release | Owner approval required before push/deploy; then verify exact approved revision in Render, protected readiness and workflows | Successful provider deploy ID + matching revision + critical live journeys |
| Usability/performance | Product/QA: observed representative farmer sessions and constrained-network device tests | Record completion, comprehension, errors and latency; local FCP is not production performance |

The feature matrix retains unrun cases rather than relabeling them not applicable.
See TEST_RESULTS.md for commands and RELEASE_CHECKLIST.md for release gates.
