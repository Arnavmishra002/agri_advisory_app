# Farmer Beta Operations Runbook

This runbook is the release contract for the KrishiMitra web beta. A green
development build is not permission to launch. Public traffic is allowed only
when strict readiness, CI, safety evaluations, and real provider canaries pass.

## Production Topology

- Render web service: Django, DRF, Gunicorn, and the built Vite UI.
- Render managed PostgreSQL: farmer accounts, profiles, feedback, and history.
- Render managed Redis: shared cache, throttling, OTP backoff, and Celery state.
- Managed GPU host: private Phase 1 FastAPI, Chroma index, and Ollama model.
- External providers: Open-Meteo, optional OpenWeather fallback, data.gov.in,
  Twilio, Sentry, and optional labeled Gemini fallback.

Phase 1 is service-to-service only. It must use HTTPS, an unguessable bearer
token, explicit request limits, and no wildcard CORS. Do not expose Ollama
directly to the public internet.

## Required Secrets And Values

Set these through provider secret stores, never committed files:

```text
SECRET_KEY
DATABASE_URL
REDIS_URL
DATA_GOV_IN_API_KEY
SENTRY_DSN
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
PHASE1_BASE_URL
PHASE1_SERVICE_TOKEN
ALLOWED_HOSTS
CORS_ALLOWED_ORIGINS
CSRF_TRUSTED_ORIGINS
```

Required production flags:

```text
DEBUG=false
STRICT_PRODUCTION_CONFIG=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FAIL_OPEN=false
RAG_INDEX_REQUIRED=true
DISEASE_CLASSIFICATION_ENABLED=false
ML_ALLOW_UNVERIFIED_MODEL=false
```

Gemini and OpenWeather are optional bounded fallbacks. If configured, the UI
must continue to label their answers/provider. Disease classification stays off
until the model metadata is `production_candidate` and held-out field metrics
meet the release threshold.

## Pre-Launch Gate

1. Deploy to staging with production-equivalent PostgreSQL, Redis, Phase 1,
   Ollama model, RAG index, origins, rate limits, and provider secrets.
2. Run the latest GitHub `KrishiMitra CI` workflow. Backend, frontend,
   Docker, launch gate, and browser journeys must run and pass.
3. Run strict readiness:

```bash
curl -fsS "https://staging.example.com/api/health/launch-readiness/?strict=true"
```

The response must be HTTP 200 with `status: ready` and no blockers.

4. Run the production canary manually before enabling its schedule:

```bash
python3 scripts/production_canary.py \
  --api-base https://staging.example.com \
  --phase1-base https://phase1.internal.example.com
```

5. Verify in a real browser: confirmed GPS, manual village search, fresh
   weather, exact or nearby official mandi row, crop factors, greeting,
   Hindi/Hinglish farming answer, new/restore/delete chat, registration,
   login, token refresh, logout, and disease advisory fallback.
6. Confirm no response contains a synthetic price, fabricated sensor reading,
   image disease label, or unattributed pesticide dose.
7. Confirm privacy/legal text, SMS sender registration, support ownership, and
   incident contacts have been approved by the responsible humans.

## Live Data Rules

- Weather: show provider, observation time, age, and stale status. If both
  providers fail, show unavailable or a clearly timestamped offline cache.
- Mandi: show only dated official rows. Prefer the selected mandi; otherwise
  show official alternatives within 150 km ordered by distance. Never replace
  missing rows with MSP, state-wide unrelated rows, or estimates.
- Location: use browser GPS only after confirmation. An unresolved place must
  remain unresolved; never replace it with Delhi or IP-derived coordinates.
- Sensors: advice may use only validated, attributable, sufficiently fresh
  readings. Simulated values are demo-only and must never enter farmer advice.
- Disease: accept the photo and provide symptom questions and safe escalation,
  but do not claim image classification while the feature flag is off.

## Canary And Alert Schedule

The daily GitHub canary checks GPS resolution, weather freshness, official
mandi behavior, OTP delivery when test credentials are configured, Phase 1/RAG,
Ollama generation, and greeting latency. Alert the operator when:

- API availability drops below 99.5% over the rolling target window.
- Weather success drops below 95% or freshness exceeds the allowed threshold.
- Exact-mandi or nearby-alternative coverage drops materially by state.
- Phase 1 first-token or total latency breaches its budget repeatedly.
- Redis, PostgreSQL, OTP, RAG, or Sentry becomes unavailable.
- A safety evaluation or synthetic-data guard fails once.

Do not log raw phone numbers, full coordinates tied to identities, OTPs,
tokens, chat text, or uploaded images in application logs or Sentry breadcrumbs.

## Incident Response

### Redis unavailable

Keep `RATE_LIMIT_FAIL_OPEN=false`. Pause new beta traffic, restore Redis, and
verify OTP throttling plus strict readiness before resuming.

### Phase 1 or Ollama unavailable

Keep the web app online only if responses are clearly labeled as cloud/rule
fallback and the fallback latency/safety gates pass. Do not claim local RAG.
Pause rollout if fallback error rate is elevated.

### Weather providers unavailable

Show a timestamped stale cache or unavailable state. Do not give current
irrigation/spray advice from old weather. Resume live labels only after the
freshness canary passes.

### Mandi source unavailable

Show unavailable plus eNAM/mandi-office verification guidance. Never enable
estimated prices to hide a provider outage.

### Database or authentication failure

Stop rollout. Preserve guest read-only workflows only when they do not require
private data. Restore the database/auth provider and rerun login/logout/OTP
tests before resuming.

### Unsafe AI answer

Pause rollout immediately. Preserve the request metadata without raw PII,
disable the failing tier if necessary, add the case to the critical evaluation
set, complete agronomist/source review, and promote only after staging passes.

## Rollback

1. Pause the rollout or route traffic to the last known-good image.
2. Do not delete or rewrite production data during rollback.
3. Verify database migration compatibility before changing application images.
4. Run liveness, readiness, strict launch readiness, and the farmer canary.
5. Record the incident, affected release SHA, provider state, and recovery time.

## Reviewed Learning

Never train directly on farmer messages. Export only de-identified negative
feedback and unanswered questions with `export_review_queue`; require
agronomist review, attributable sources, safety review, versioned KB/dataset
updates, retrieval/language/safety regression tests, and staging promotion.

## Rollout Stages

Use invited cohort, 5%, 25%, 50%, then 100% beta stages. At every stage, pause
automatically on a safety failure, provider freshness failure, elevated error
rate, OTP regression, or strict-readiness failure. Advancement requires human
review of state-level mandi coverage, language feedback, latency, and Sentry
trends.
