# KrishiMitra — application audit

**Date:** 14 September 2026 · **Revision:** `8d113d0` · **Branch:** `codex/farmer-readiness-repairs`
**Roles applied:** full-stack engineer, QA automation, security reviewer, accessibility auditor

---

## Overall assessment: **Not ready**

Not because the code is poor — much of it is careful, and several defences held up
under direct attack. It is not ready because of three things that are true right now:

1. **Nothing you have built in the last two weeks is reachable by a farmer.** Thirteen
   consecutive deploys have failed; the live site serves a build from before the current
   run of fixes.
2. **A farmer cannot log in.** OTP delivery is unconfigured, and the UI does not say so —
   it shows a code-entry screen for a code that was never sent.
3. **The advice engine invents a farmer's growing conditions when it does not know them**,
   and presents the invention as fact. For an app whose stated discipline is never to
   invent a price, this is the same sin one layer down.

Everything else in this report is secondary to those three.

Counts are at the end. The evidence for every claim is in `TEST_RESULTS.md`.

---

## What is genuinely working

These are not "it rendered" observations. Each was asserted against resulting state.

**Authentication and access control held under direct probing.**
The full OTP journey — request, verify, JWT issued, `User` row actually created — works.
A consumed OTP is rejected on reuse. Six wrong codes produce a `429` lockout. A fourth
OTP request inside the window is refused. Anonymous callers are rejected from
`/api/users/me/`, `/api/farmer-profile/me/` and `/api/farmer-profile/context/`. Two
separate authenticated users could not see each other's profile — no IDOR found in the
endpoints probed. An anonymous `POST /api/rate-limits/reset/` is refused, which matters
because that route is registered `AllowAny` and a working reset would have made every
limit above decorative.

**Input handling is strict.** A 5,000-character query, empty and whitespace-only
queries, an unsupported language code, and an unexpected `is_admin` field are all
rejected with `400`. The serializer is strict by default rather than permissive.

**Output escaping is correct where it matters.** `renderChatText` escapes first and
applies its markdown pass second, so a `<script>` in model output cannot be reconstructed
into a tag. Of 60 `innerHTML` assignments in `app.js`, a scan found 3 that interpolate,
and all 3 resolve to escaped or literal content.

**Configuration fails fast.** Booting with `STRICT_PRODUCTION_CONFIG=true` and no Redis
raises `ImproperlyConfigured` instead of starting in a silently degraded state. Under
`DEBUG=False`, `/api/monitoring/metrics/` correctly returns `403`.

**Market honesty holds under total upstream failure.** With every provider returning
proxy 403, the app returned no invented prices — it said so instead.

**Responsive layout is clean.** Zero horizontal overflow at 320, 360, 768 and 1440 px.
Zero tap targets under 24×24 px. This is better than most apps of this size.

**Right-to-left works.** Urdu, Sindhi and Kashmiri all set `dir="rtl"` correctly, and
the `lang` attribute tracks the language switcher across all 22 options.

**The project's own e2e suite is healthy** — 22/22 pass once pointed at an available
browser binary.

---

## Issues

### ISSUE-01 · Deploys have been failing for thirteen commits; the live site is stale
**Severity: Critical** · **Confirmed runtime failure** · Affects: every user · Role: all

**Evidence.** GitHub's Deployments page for `main - agri-advisory-web` shows 13
consecutive `Failed to deploy`, from *"Fix silent-failure bugs blocking farmer launch"*
through *"Wire the district-scoped price lookup that never ran"*. The last successful
deploy is *"Fix Devanagari word boundaries in intent routing"*.

Verified against the running service rather than inferred. `https://agri-advisory-web.onrender.com/api/health/`
returns OK, and its live `/js/i18n.js` serves:
```javascript
window.t = function (key, lang) {
    const l = lang || _currentLang;
    const entry = T[key];
    if (!entry) return key;
    return entry[l] || entry['hi'] || entry['en'] || key;
};
```
That is the pre-fix function — no `_DEVANAGARI_LANGS`. The script-aware fallback, the
irrigation scoring fix, the seed-price removal and the CSP work are all absent from
what farmers actually reach.

**Expected vs actual.** A green pipeline should mean the commit is live. It is not.

**Likely cause (high confidence).** `agri-advisory-db` is suspended, so the build dies
resolving the database host. `scripts/render_preflight.py` is why recent failures take
21 seconds instead of three minutes; it does not make them succeed.

**Smallest fix.** Restore the database — add a card and upgrade, or free the single
free-tier slot. This is an account decision, not a code change.

**Verification.** After the next push, the Deployments row for that commit reads
`Deployed`, and live `/js/i18n.js` contains `_DEVANAGARI_LANGS`.

---

### ISSUE-02 · The OTP screen asks for a code that was never sent
**Severity: Critical** · **Confirmed code defect** · Affects: login · Role: unauthenticated farmer

**Location.** `backend/advisory/api/viewsets/auth_viewset.py:108-113`, `:237-245` ·
`frontend/public/js/auth.js:130-152`

**Preconditions.** Twilio not configured (`otp_provider: false` — confirmed live at
`/api/health/launch-readiness/`).

**Steps.** Open the app → Login → enter a mobile number → tap Send OTP.

**Expected.** The farmer is told SMS login is unavailable.
**Actual.** The backend truthfully returns `{"success": true, "sms_sent": false}`. The
frontend branches on `data.success` alone:
```javascript
.then(function (data) {
  if (data.success) {
    if (step2) step2.style.display = '';   // advance to 6-digit entry
    self._startResendCountdown();
```
The farmer sees a code-entry screen and a resend countdown, waits for an SMS that was
never sent, guesses, is locked out after 3 attempts (`429`), and has also spent their
3-requests-per-hour budget. No message explains any of it.

**Impact.** Login is impossible, and the failure is silent. This is the single worst
first-run experience in the app.

**Smallest fix.** In `auth.js`, branch on `data.sms_sent`. When false, show a clear
message in the farmer's language and do not advance to step 2 or start the countdown.

**Regression test.** Extend `frontend/tests/e2e/auth.spec.js`: mock
`/api/users/otp/request/` returning `{success:true, sms_sent:false}` and assert
`#otpStep2` stays hidden and an error is shown.

---

### ISSUE-03 · Crop advice invents the farmer's soil and irrigation for uncovered districts
**Severity: High** · **Confirmed runtime failure** · Affects: crop recommendation · Role: all

**Location.** `backend/advisory/services/crop_recommendation_engine.py:565-600`,
`backend/advisory/services/district_data.py`

**Evidence.** `DISTRICT_PROFILES` holds **126 districts**; India has roughly 780. When a
district is absent the engine falls through to a *state_first_district* branch and serves
the first listed district's profile as if it were the farmer's own:

```
East Godavari  →  _source=state_first_district  soil=Alluvial  irr=High  rain=Medium
Kakinada       →  _source=state_first_district  soil=Alluvial  irr=High  rain=Medium
Rajahmundry    →  _source=state_first_district  soil=Alluvial  irr=High  rain=Medium
```
For Andhra Pradesh the stand-in is **Vijayawada**. For Assam it is **Guwahati**
(`irrigation=Low, rainfall=Very High`); for Kerala, Thiruvananthapuram.

The farmer is told, with no hedging:
```
1. 🟡 Rice (धान) — 75% suitability
   कारण: Perfect season match (kharif) | Ideal soil (Alluvial)
         | Water needs met (High, from irrigation)
```

**Expected vs actual.** Either ask the farmer, or label the profile as borrowed. Instead
a guess is stated as fact.

**Impact.** A rain-fed farmer in East Godavari is told rice is a 75% match because the
engine assumed Vijayawada's irrigation. Rice on a rain-fed field is a season's income.
This is precisely the harm the app's own market-honesty discipline exists to prevent,
one layer down and without the same discipline applied.

**Smallest fix.** Two steps, in order. (a) When `_source` is not `district_exact`, say so
in the answer — "Vijayawada ke aankdon par aadharit". (b) When the district is not in the
table, ask for irrigation before scoring rather than defaulting.

**Regression test.** Assert `_resolve_location_profile("East Godavari", "Andhra Pradesh")`
returns a profile whose provenance is visible to the renderer, and that the rendered
answer contains the stand-in district's name.

---

### ISSUE-04 · A test expires by wall-clock date and has now turned the suite red
**Severity: High** · **Confirmed runtime failure** · Affects: CI · Role: developer

**Location.** `backend/advisory/tests/test_market_district_scoping.py:232-245`

**Evidence.** Baseline run: `Ran 357 tests … FAILED (failures=1)`, `AssertionError: 0 != 2`.

The test pins `reported_date="06-09-2026"` and never passes `now`, while
`build_dated_official_reference` accepts a `now` parameter for exactly this reason. The
function keeps rows older than 24 h but younger than 7 days, so the fixture is only valid
inside a six-day window. Bisected by injecting `now`:

```
now=2026-09-07 → rows=2      now=2026-09-12 → rows=2
now=2026-09-13 → rows=0      now=2026-09-14 → rows=0   ← today
```

**Production code is correct.** The test is the defect, and it will now fail forever.

**Impact.** The suite is red, so it no longer distinguishes "someone broke something"
from "the calendar moved". Every future regression hides behind this failure.

**Smallest fix.** Pass an explicit `now` into `build_dated_official_reference`, or derive
the fixture date relative to `now`.

**Note.** This test was written in this project's own recent work. Flagging it as mine
rather than leaving it as an anonymous red mark.

---

### ISSUE-05 · Eight of twenty-two offered languages have no translations
**Severity: High** · **Confirmed runtime failure** · Affects: i18n · Role: all

**Evidence.** Each option in `#languageSwitcher` was selected in a real browser and the
rendered navigation captured:

| Code | Label shown to the farmer | What they actually get |
|---|---|---|
| `mai` | मैथिली (Maithili) | Hindi (Devanagari) |
| `kok` | कोंकणी (Konkani) | Hindi (Devanagari) |
| `doi` | डोगरी (Dogri) | Hindi (Devanagari) |
| `bo` | बड़ो (Bodo) | Hindi (Devanagari) |
| `sat` | ᱥᱟᱱᱛᱟᱲᱤ (Santali) | Hindi (Devanagari) |
| `mni` | মৈতৈলোন্ (Manipuri) | **English** |
| `sd` | سنڌي (Sindhi) | **English** |
| `ks` | کشمیری (Kashmiri) | **English** |

Nine are fully translated (hi, bn, te, mr, ta, gu, kn, ml, pa) and render in the correct
script — 31/34 to 40/43 of non-Latin characters fall inside the expected Unicode block.
Four more are partial (below). The dropdown promises 22.

**Impact.** A Kashmiri or Sindhi speaker selects their own language, in their own script,
and the interface answers in English. Offering a language you cannot serve is worse than
not listing it — it spends the user's trust before the app has said anything.

**Smallest fix.** Show only languages with translation coverage above a threshold, or
label the rest "coming soon" in the dropdown itself.

**Sub-issue ISSUE-05a — `bo` is the wrong ISO code.** The label says Bodo; `bo` is
ISO 639-1 for **Tibetan**. Bodo is `brx`. The page therefore emits `<html lang="bo">`,
telling screen readers and search engines that Devanagari Bodo text is Tibetan.
*Severity: Medium · confirmed code defect.*

**Sub-issue ISSUE-05b — Santali's dropdown label is Ol Chiki, its fallback is Devanagari.**
The option renders `ᱥᱟᱱᱛᱟᱲᱤ`, then the UI falls back to Hindi in Devanagari. Santali is
written in both scripts, so this is not absurd — but promising one script in the picker
and delivering another is still a broken promise. *Severity: Low-Medium.*

---

### ISSUE-06 · Four languages are translated only partway
**Severity: Medium** · **Confirmed runtime failure** · Affects: i18n · Role: all

Odia, Assamese, Urdu and Nepali translate "My Profile" but leave "Logout" in English:

```
or   KrishiMitra | ମୋର ପ୍ରୋଫାଇଲ | Logout
as   KrishiMitra | মোৰ প্ৰফাইল  | Logout
ur   KrishiMitra | میری پروفائل  | Logout
ne   KrishiMitra | मेरो प्रोफाइल | Logout
```
**Impact.** Mixed-language chrome is exactly the confusion a multilingual app exists to
remove, and "Logout" is a control a first-time user most needs to recognise.
**Smallest fix.** Fill the missing keys in `i18n.js`; add a CI check that every listed
language covers the navigation key set.

---

### ISSUE-07 · No `main` landmark
**Severity: Medium** · **Confirmed runtime failure** · WCAG 1.3.1 / 2.4.1 · Role: screen-reader user

Runtime landmark count: `{main: 0, nav: 2, header: 0}`. A screen-reader user has no way
to jump past two navigation regions to the content.
**Smallest fix.** Wrap the content region in `<main>`; add a skip link.

---

### ISSUE-08 · Two controls have no accessible name
**Severity: Medium** · **Confirmed runtime failure** · WCAG 3.3.2 / 4.1.2 · Role: screen-reader user

`#languageSwitcher` (select) and `#locationSearchInput` (text) have no `<label>`,
`aria-label` or `aria-labelledby`. The language switcher being unlabelled is the sharper
of the two: it is the first control a non-Hindi speaker needs, and it announces as
"combo box" with no purpose.
**Smallest fix.** Add `aria-label` to both, wired through `i18n.js` so the name is
translated.

---

### ISSUE-09 · Focus is invisible on three controls
**Severity: Medium** · **Confirmed runtime failure** · WCAG 2.4.7 · Role: keyboard user

Tabbing 18 stops from page load, three had neither outline nor box-shadow:
`#themeToggle`, `#locationSearchInput`, and the location Search button. A keyboard user
tabs into them and cannot see where they are.
**Smallest fix.** A global `:focus-visible` rule; remove any `outline: none` that is not
paired with a replacement indicator.

---

### ISSUE-10 · CD reports "Render: success" for a deploy that never ran
**Severity: Medium** · **Confirmed runtime failure** · Affects: pipeline · Role: developer

`KrishiMitra CD` #93 and #94 both finished green. Their deploy job logged:
```
RENDER_DEPLOY_HOOK_URL is not set; skipping Render deploy.
Render deploy was skipped; skipping post-deploy health check.
```
and the summary job printed `Docker: success` / `Render: success`. The Docker job had
logged `Docker Hub credentials missing; image will be build-tested only`. Two of the
three lines in that summary read identically whether the step happened or not.

**A fix for this is already written and sitting uncommitted in the working tree**
(`.github/workflows/deploy.yml` plus `test_deploy_pipeline_honesty.py`, 8 of whose 9
tests fail against the previous workflow). It was left uncommitted deliberately: its
warning text still says "Set RENDER_DEPLOY_HOOK_URL to make CD deploy", which is
misleading now that ISSUE-01 has established Render auto-deploys through its own GitHub
App. **Reword before committing.**

---

### ISSUE-11 · `/api/health/launch-readiness/` publishes the security posture to anonymous callers
**Severity: Medium** · **Confirmed runtime failure** · Affects: monitoring · Role: anonymous

Under production-shaped settings (`DEBUG=False`, `RATE_LIMIT_ENABLED=true`) the endpoint
returns `200` with:
```json
{"checks": {"rate_limiting": true, "redis": false, "strict_production_config": false,
            "phase1_service_auth": false, "otp_provider": false, "sentry": false, ...},
 "blockers": [{"code": "...", "action": "Set ..."}]}
```
Its siblings in the same file are gated — `MonitoringViewSet.metrics` and `system_health`
return `403` via `_staff_or_debug`. `launch_readiness_check` is a plain function view with
no gate, so the inconsistency looks accidental rather than intended.

**Impact.** An attacker learns which defences are off before probing anything. No secret
values are exposed — verified: zero matches for connection strings or 32+ character tokens.
**Smallest fix.** Apply the same `_staff_or_debug` gate, or return a bare status
unauthenticated and details only to staff.

---

### ISSUE-12 · Chat echoes raw input back in the response body
**Severity: Low** · **Suspected risk (hardening)** · Affects: chat API

`POST /api/chatbot/query/` with `<script>alert(1)</script>` returns it verbatim in
`"query"`. **This is not currently exploitable** — `Content-Type: application/json`,
`X-Content-Type-Options: nosniff`, and no client renders `data.query` as HTML. It is
recorded only because the safety depends on three conditions holding elsewhere. A test
pinning the content type and nosniff header is in `test_audit_journeys.py`.

---

### ISSUE-13 · Leftover Google Fonts `@import` that production CSP blocks
**Severity: Low** · **Confirmed runtime failure** · Affects: every page load

`frontend/css/styles.css:7`:
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:...&display=swap');
```
while `frontend/public/vendor/fonts/fonts.css:2` says fonts were deliberately
self-hosted: *"Previously loaded from fonts.googleapis.com; served locally so the UI
keeps…"*. Production CSP is `style-src 'self' 'unsafe-inline'` and `font-src 'self' data:`,
so the request is blocked. The browser audit recorded one failed request and one console
error at **every** viewport tested.

**Impact.** Cosmetically none — the fonts are self-hosted. But it is a blocked request and
a CSP violation on every page load, and it means the de-CDN work was completed in one file
and missed in the other.
**Smallest fix.** Delete line 7 of `styles.css`.

---

## Coverage gaps

**GAP-01 — the login journey had no success-path test at all.** *Critical.*
Before this audit, no test in the suite asserted a `200` from `/api/users/otp/verify/`.
`test_auth_otp_security.py` covers rate limits and log suppression only. And the journey
could not be tested through the public API: the code is obtainable only via `dev_otp`,
which is gated on `settings.DEBUG`, which Django's test runner forces to `False`. The new
`test_audit_journeys.py` drives it by reading the cache directly. **This gap is why
ISSUE-02 survived** — nobody had ever walked the whole path in a test.

**GAP-02 — the e2e suite never touches the backend.** Every spec mocks `**/api/**`. The
suite ran fully green with no backend process running. It verifies frontend logic against
*assumed* contracts, so a backend contract change cannot fail it.

**GAP-03 — no test covers the district stand-in.** ISSUE-03 has no guard; the
`state_first_district` fallback can change silently.

**GAP-04 — no accessibility tests.** All nine a11y findings came from this audit's
one-off scripts. Nothing in CI would catch a regression.

**GAP-05 — no test asserts translation completeness.** ISSUE-05 and ISSUE-06 are
invisible to CI; a language can be added to the dropdown with zero keys.

---

## Priorities

**Fix first — a farmer cannot use the app until these are done**
1. **ISSUE-01** — restore the database so deploys land. Nothing else you fix reaches anyone until this is true. *(Yours: card, or free the free-tier slot.)*
2. **ISSUE-02** — make the OTP screen tell the truth when `sms_sent` is false. One branch in `auth.js`.
3. **ISSUE-03** — stop presenting a borrowed district profile as the farmer's own.

**Fix next — correctness and trust**
4. **ISSUE-04** — un-expire the time-bomb test so CI means something again.
5. **ISSUE-05 / 05a / 05b / 06** — stop offering languages you do not serve; fix `bo` → `brx`.
6. **ISSUE-11** — gate `launch-readiness` like its siblings.
7. **ISSUE-10** — reword and commit the CD honesty fix already in the tree.

**Then — accessibility and hygiene**
8. **ISSUE-07, 08, 09** — `<main>`, two labels, one `:focus-visible` rule. Perhaps an hour for all three.
9. **ISSUE-13** — delete one line of CSS.
10. **GAP-02 … GAP-05** — add the guards, so the next audit starts from a better baseline.

**Do not spend time on** dependency pins or the `pip check` noise — that was this
container, not your repo.

---

## Counts

| | |
|---|---|
| **Features and scenarios inventoried** | **83** rows in `FEATURE_TEST_MATRIX.csv`, drawn from 81 API endpoints (non-format-suffix) across 20 viewsets, 5 frontend service screens, 22 language options, the admin surface, the pipeline, and 6 external integrations |
| **Test scenarios executed by this audit** | **38** — 16 new backend audit tests + 22 project e2e specs |
| Pre-existing backend tests also run | **357** (1 failing, pre-existing) |
| Browser scenarios executed | 4 viewports × layout + a11y, 22 language switches, 4 RTL checks, 1 performance profile |
| | |
| **PASS** | **42** |
| **FAIL** | **15** (mapping to 13 issues; ISSUE-03 and ISSUE-05 each span several rows) |
| **BLOCKED** | **7** |
| **NOT RUN** | **18** |
| **NOT APPLICABLE** | **1** (e2e project scoping, explained in `TEST_RESULTS.md`) |
| | |
| Confirmed issues | **13** — 2 Critical, 2 High + 2 High sub-issues, 6 Medium, 2 Low |
| Findings retracted after investigation | **6** |

Inventoried ≠ executed. Of 83 inventoried rows, **57 were exercised** (42 PASS + 15 FAIL);
**26 were not** (18 NOT RUN, 7 BLOCKED, 1 NOT APPLICABLE). Roughly a third of the surface
therefore carries no evidence either way from this audit.

**Unverified and worth saying plainly:** every upstream integration — Agmarknet,
Open-Meteo, MET Norway, Twilio, Gemini/Ollama — was exercised only in its failure path,
because both audit environments are network-restricted. The app behaves honestly when
they are all down. Whether it behaves correctly when they are *up* is not established by
this audit. Neither is any behaviour under PostgreSQL, Redis, concurrency, or a browser
other than Chromium.

This report does not establish that the application is secure, correct, or production-ready.
It establishes what was tested, what those tests showed, and what remains unknown.
