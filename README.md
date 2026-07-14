# KrishiMitra - Agricultural Advisory App

KrishiMitra is a farmer advisory platform for Indian agriculture. The repository
is a monorepo containing a Django REST API, a Vite web UI, a Flutter mobile app,
a local Phase 1 AI/RAG service, crop disease ML tooling, and deployment scripts.

The production goal is farmer-safe behavior: live weather and mandi data when
available, location-aware crop recommendations, honest disease diagnostics, and
chatbot answers grounded in the local knowledge base before optional cloud AI.

## What Runs Where

| Surface | Local dev | Docker compose | Purpose |
| --- | --- | --- | --- |
| Django API and optional built UI | `http://127.0.0.1:8000` | `http://localhost:8001` | Main app, API, admin, health checks |
| Vite frontend | `http://localhost:5173` | Built into Django/nginx image | Web UI during frontend development |
| Phase 1 AI/RAG | `http://localhost:8001` from `phase1/` | `http://localhost:8002` | FastAPI bridge for local RAG/Ollama |
| Nginx full profile | - | `http://localhost:8080` | Static UI plus reverse proxy |

Important: `localhost:8002` is the Phase 1 AI/RAG service, not the main web UI.
Use `localhost:8001` for the Docker app or `127.0.0.1:8000` for local
`runserver`.

## Repository Layout

```text
agri_advisory_app/
├── backend/                  # Django + DRF API, services, admin, ML inference
├── frontend/                 # Standalone Vite UI
├── mobile/                   # Flutter mobile app source
├── phase1/                   # FastAPI local AI/RAG service for Ollama + Chroma
├── custom_llm_trainer/       # Local KrishiMitra Ollama model assets
├── scripts/                  # Smoke checks, deploy helpers, training helpers
├── docs/                     # Architecture, audits, operational notes
├── models/                   # Local/mounted ML artifacts, ignored by git
├── data/                     # Local datasets/runtime data, ignored by git
├── manage.py                 # Root wrapper for backend/manage.py
├── Dockerfile                # Multi-stage API and nginx image
├── docker-compose.yml        # Web, Phase 1, Postgres, Redis, nginx, MQTT
└── render.yaml               # Render deployment blueprint
```

## Current Production Notes

- Chatbot priority is local knowledge base plus Phase 1 RAG/Ollama first, direct
  Ollama next, Gemini only when `GOOGLE_AI_API_KEY` is configured, then a
  rule-based farmer-safe fallback.
- Weather uses Open-Meteo without an API key. `OPENWEATHER_API_KEY` is optional.
- Mandi prices use only fresh, dated official Agmarknet/data.gov.in rows.
  Agmarknet 2.0 provides current state-level rows without a key. A valid
  `DATA_GOV_IN_API_KEY` adds fuller commodity and exact-mandi coverage. The app
  never substitutes synthetic or MSP-estimate prices when an official row is
  absent.
- Crop recommendations use 200+ canonical Indian crop profiles and combine
  location, season, weather, soil, irrigation, optional soil-test readings,
  farmer budget, crop rotation, and verified market signals. Static cost and
  profit figures are explicitly labeled as indicative planning estimates.
- Disease diagnostics do not fake image classification. If the trained model is
  missing or low quality, the API returns an advisory fallback instead of a false
  disease label.
- Production should use Redis via `REDIS_URL` for shared cache, rate limiting,
  Celery, and consistent behavior across workers.

## Quick Start - Backend

Use Python 3.11, matching Docker and GitHub Actions. Django 5.2 requires Python
3.10 or newer; the macOS system Python 3.9 is not supported by this project.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Useful backend URLs:

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/` | API/root app |
| `http://127.0.0.1:8000/api/health/` | Basic health |
| `http://127.0.0.1:8000/api/health/readiness/` | Database, cache, AI, model readiness |
| `http://127.0.0.1:8000/api/health/launch-readiness/` | Explicit production launch blockers |
| `http://127.0.0.1:8000/api/schema/swagger-ui/` | Swagger UI |
| `http://127.0.0.1:8000/admin/` | Django admin |

Equivalent backend-only command:

```bash
cd backend
python manage.py runserver
```

## Quick Start - Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Set `frontend/.env` for local API calls:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

Use `http://localhost:8001` instead when the API is running through Docker.

## Run Backend And Frontend Together

```bash
# Terminal A
python manage.py runserver

# Terminal B
cd frontend
npm run dev
```

When `DEBUG=True`, CORS allows the Vite dev server on `localhost:5173`.

## Phase 1 Local AI/RAG

Phase 1 is a FastAPI service that connects the Django chatbot to local RAG and
Ollama. It is optional, but recommended when using KrishiMitra's own local LLM.

Prerequisites:

```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

Create the custom local model if needed:

```bash
cd custom_llm_trainer
ollama pull qwen2.5:7b
```

Start Phase 1 locally:

```bash
cd phase1
bash start.sh
# or:
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

`phase1/start.sh` fingerprints every `.txt` and `.pdf` knowledge source and
rebuilds Chroma only when the content changes. Docker performs the same check
and stores the generated index in the `krishimitra_rag_data` volume. Set
`RAG_INDEX_REQUIRED=true` in production to stop startup when fresh knowledge
cannot be indexed; the default local setting starts in a clearly degraded mode.

Check it:

```bash
curl http://localhost:8001/health
curl "http://localhost:8001/rag/search?q=wheat"
```

When using Docker, Phase 1 is exposed on host port `8002`:

```bash
docker compose --profile ai up --build web phase1
curl http://localhost:8002/health
```

## Docker

Create `.env` first and set at least `SECRET_KEY`.

```bash
cp .env.example .env
```

Common commands:

```bash
# API plus built frontend served by Django, host port 8001
docker compose up --build web

# API plus Phase 1 AI/RAG, host ports 8001 and 8002
docker compose --profile ai up --build web phase1

# API plus nginx static UI, host ports 8001 and 8080
docker compose --profile full up --build

# Full stack: Django, nginx, PostgreSQL, Redis, Phase 1, MQTT
docker compose --profile all up --build
```

The compose file stores runtime state in named volumes for the database,
uploads, static files, Redis, MQTT, and mounted ML models.

## Crop Disease Model

Real image classification requires a trained Keras model at:

```text
models/crop_disease/efficientnetb3_crop_disease.keras
```

Large datasets and trained model artifacts are intentionally not committed.
Install or mount the model in production, or train one from local datasets.

Install ML dependencies:

```bash
pip install -r backend/requirements-ml.txt
```

Prepare datasets under `data/datasets/` and inspect them:

```bash
python scripts/setup_training_data.py --analyze-only
```

Train EfficientNet-B3:

```bash
PYTHONPATH=backend python -m advisory.ml.train \
  --data-dir data/datasets \
  --output-dir models/crop_disease \
  --architecture efficientnetb3
```

Evaluate before production:

```bash
PYTHONPATH=backend python -m advisory.ml.evaluate \
  --model-dir models/crop_disease \
  --data-dir data/datasets
```

For quick local/CI smoke checks on constrained hardware:

```bash
PYTHONPATH=backend python -m advisory.ml.evaluate \
  --model-dir models/crop_disease \
  --data-dir data/datasets \
  --max-test-samples 390
```

`/api/health/readiness/` reports whether the model is missing, needs retraining,
or is a production candidate. Models marked `needs_retraining` or `unknown` are
blocked from farmer-facing predictions by default; use
`ML_ALLOW_UNVERIFIED_MODEL=true` only for offline evaluation, never for a farmer
production deployment.

## Flutter Mobile

The mobile app lives in `mobile/`. For release builds, pass the backend URL with
`--dart-define` instead of hard-coding it:

```bash
cd mobile/krishimitra
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
flutter build apk --release --dart-define=API_BASE_URL=https://your-api.example.com
flutter build appbundle --release --dart-define=API_BASE_URL=https://your-api.example.com
```

Local shell environments may not have Flutter installed. GitHub Actions runs
`flutter analyze` for mobile regressions.

## Environment Variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Production | Django secret key |
| `DEBUG` | No | Local debug mode |
| `DATABASE_URL` | Production | PostgreSQL or SQLite URL |
| `ALLOWED_HOSTS` | Production | Django host allow-list |
| `CORS_ALLOWED_ORIGINS` | Production | Frontend origins allowed to call API |
| `CSRF_TRUSTED_ORIGINS` | Production | Trusted origins for state-changing requests |
| `DATA_GOV_IN_API_KEY` | Recommended | Fuller commodity and exact-mandi coverage beyond the no-key Agmarknet state feed |
| `MANDI_MAX_DATA_AGE_HOURS` | Optional | Maximum accepted age for an official daily mandi row; default `72` |
| `GOOGLE_AI_API_KEY` | Optional | Gemini fallback for chatbot |
| `OPENWEATHER_API_KEY` | Optional | OpenWeather fallback; Open-Meteo works without a key |
| `REDIS_URL` | Production | Shared cache, rate limits, Celery broker |
| `RATE_LIMIT_ENABLED` | Production | Enables API and chatbot-stream throttling |
| `RATE_LIMIT_FAIL_OPEN` | Development only | Allow traffic when the rate-limit cache is unavailable; keep `false` in production |
| `RATE_LIMIT_PUBLIC_RPM/RPH/RPD` | Optional | Public per-IP minute/hour/day limits |
| `RATE_LIMIT_AUTHENTICATED_RPM/RPH/RPD` | Optional | Authenticated per-IP and per-account limits |
| `RATE_LIMIT_AUTH_RPM/RPH/RPD` | Optional | Login, OTP, and registration limits |
| `RATE_LIMIT_HEAVY_RPM/RPH/RPD` | Optional | Diagnostics, pest, and TTS limits |
| `RATE_LIMIT_CHAT_*`, `RATE_LIMIT_DATA_*`, `RATE_LIMIT_DIAG_*`, `RATE_LIMIT_DEFAULT_*`, `RATE_LIMIT_NOMINATIM_*` | Optional | Token-bucket capacity and refill settings for non-HTTP integrations |
| `AUTH_BACKOFF_THRESHOLD` | Optional | Failed OTP attempts before progressive delay |
| `AUTH_BACKOFF_BASE_SECONDS` | Optional | Initial OTP backoff delay |
| `AUTH_BACKOFF_MAX_SECONDS` | Optional | Maximum OTP backoff delay |
| `AUTH_BACKOFF_WINDOW_SECONDS` | Optional | Failed-attempt counter lifetime |
| `KRISHI_RAKSHA_MAX_UPLOAD_MB` | Optional | Maximum decoded diagnostic image size; default `5` |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | Optional | Django request parser limit in bytes; default `8388608` |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | Optional | Django in-memory file limit in bytes; default `8388608` |
| `PRIVATE_UPLOAD_ROOT` | Optional | Private future-upload directory; never expose it as static/media content |
| `SENTRY_DSN` | Production | Error tracing without exposing farmer PII |
| `LAUNCH_CHECK` | CI/deploy | Return HTTP 503 from strict launch checks when blockers remain |
| `SERVE_FRONTEND` | Optional | Serve `frontend/dist/` from Django |
| `VITE_API_BASE_URL` | Frontend | Browser API base URL |
| `PHASE1_BASE_URL` | Optional | Django -> Phase 1 service URL |
| `PHASE1_CORS_ALLOWED_ORIGINS` | Optional | Explicit browser origins allowed to call Phase 1; empty means no cross-origin access |
| `PHASE1_ALLOW_ALL_CORS` | Development only | Allows wildcard Phase 1 CORS only when `DEBUG=true`; keep `false` in production |
| `OLLAMA_MODEL` | Optional | Local composition model; `qwen2.5:7b` is the current quality-tested default |
| `PHASE1_TIMEOUT_S` | Optional | Phase 1 request timeout |
| `PHASE1_STREAM_FIRST_TOKEN_TIMEOUT_S` | Optional | Max wait for first streamed local-AI token |
| `PHASE1_STREAM_IDLE_TIMEOUT_S` | Optional | Max idle gap between streamed local-AI tokens |
| `PHASE1_STREAM_TOTAL_TIMEOUT_S` | Optional | Total Phase 1 stream budget |
| `CHAT_LOCAL_AI_MAX_CONCURRENCY` | Optional | Max concurrent local Phase 1/Ollama chatbot calls; use `1` on small CPU-only hosts |
| `OLLAMA_BASE_URL` | Optional | Local Ollama URL |
| `OLLAMA_MODEL` | Optional | Local LLM model name |
| `OLLAMA_DIRECT_TIMEOUT_S` | Optional | Direct Ollama fallback read timeout |
| `CROP_DISEASE_MODEL_DIR` | Optional | Directory containing disease model artifacts |
| `ML_CONFIDENCE_THRESHOLD` | Optional | Minimum confidence for image classification |
| `ML_ALLOW_UNVERIFIED_MODEL` | Development only | Allows low-quality/unverified disease model predictions for offline testing |
| `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | Optional | WhatsApp integration |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Optional | SMS/IVR integration |
| `GROQ_API_KEY` | Optional | Voice transcription for WhatsApp audio |
| `MQTT_BROKER_HOST` | Optional | ESP32/IoT telemetry ingestion |

## Security And API Contracts

- Farmer profile reads and writes require JWT authentication and are always
  resolved from the authenticated farmer. Legacy `phone`/`session_id` fields
  may be accepted for compatibility but are ignored for ownership.
- Saving IoT sensor readings requires JWT authentication. Public field
  recommendations remain read-only and may use anonymous GPS data.
- OTP request/verification and password registration use strict schemas,
  per-IP/per-account limits, and progressive backoff after repeated failures.
- Chatbot JSON and SSE requests share one strict schema. Unknown fields,
  malformed coordinates, oversized history, and invalid language values are
  rejected with a safe 400 response.
- The Phase 1 FastAPI service rejects unknown body fields, bounds nested farmer,
  history, and sensor payloads, and has no wildcard CORS by default.
- Diagnostic and pest image uploads are decoded before inference. Only JPEG,
  PNG, and WebP images within the configured size/pixel limits are accepted;
  uploads are processed in memory and are not persisted by these endpoints.
- Nginx denies public `/media/` access. Any future persisted upload must use
  `PRIVATE_UPLOAD_ROOT` with restrictive permissions and an authenticated download
  endpoint rather than static file serving.
- Production errors return stable farmer-safe messages and error codes. Full
  exception details remain in server logs/Sentry only.
- The DRF rate limiter uses atomic shared-cache counters. Set `REDIS_URL` in
  production so limits and OTP backoff are consistent across workers.

## Verification

This repo currently uses smoke checks and CI contract tests rather than a pytest
suite.

Backend:

```bash
python3 -m compileall -q backend phase1 scripts custom_llm_trainer
python manage.py check
python manage.py makemigrations --check --dry-run
python scripts/check_before_push.py
```

Frontend:

```bash
cd frontend
node --check public/js/app.js
npm audit --audit-level=high
npm run build
```

Mobile:

```bash
cd mobile/krishimitra
flutter analyze
```

Manual farmer-critical API probes:

```bash
curl http://127.0.0.1:8000/api/health/readiness/
curl "http://127.0.0.1:8000/api/health/launch-readiness/?strict=true"
curl "http://127.0.0.1:8000/api/locations/search/?q=lucknow&limit=2"
curl "http://127.0.0.1:8000/api/crops/search/?q=makhana"
```

## GitHub Actions

The CI workflow validates backend routes and farmer-critical API behavior,
frontend build health, mobile analysis, code quality rules, and Docker build
contracts. It starts the API and Phase 1 containers, checks both health routes,
and verifies an instant chatbot greeting. Quick-service and production reports
are uploaded as Actions artifacts for 14 days even though generated `docs/`
reports are ignored locally. Pull requests should be green before merging.

For a deployed pre-launch gate, set repository variable `LAUNCH_CHECK=true` and
`LAUNCH_READINESS_URL=https://your-api.example.com`. The optional Actions job
then calls the strict endpoint and fails while any production blocker remains.

## Deployment

Recommended production setup:

1. PostgreSQL database with `DATABASE_URL`.
2. Redis with `REDIS_URL`.
3. Django API served by Gunicorn from `backend/`.
4. Frontend hosted by CDN/static hosting, nginx, or Django with
   `SERVE_FRONTEND=true`.
5. Optional Phase 1 service plus Ollama for local RAG/LLM.
6. Trained crop disease model mounted at `models/crop_disease/`.
7. `DATA_GOV_IN_API_KEY` set for stronger mandi coverage.
8. `SENTRY_DSN`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and
   `CSRF_TRUSTED_ORIGINS` set to production values.
9. `PHASE1_BASE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and
   `CHAT_LOCAL_AI_MAX_CONCURRENCY` matched to the deployed CPU/RAM capacity.
10. `RAG_INDEX_REQUIRED=true` so stale or missing local knowledge blocks the
    production Phase 1 service instead of silently weakening answers.

Before launch, the strict readiness endpoint must return `ready`. Missing Redis,
mandi key, Phase 1/RAG, configured Ollama model, production-candidate disease
model, or Sentry are reported as explicit blockers. Development remains usable
with honest fallback labels when `LAUNCH_CHECK=false`.

Disease model training must use a licensed dataset manifest in the format at
`backend/advisory/ml/dataset_manifest.schema.json`:

```bash
python -m advisory.ml.dataset_manifest data/datasets/dataset_manifest.json
python -m advisory.ml.train --data-dir data/datasets \
  --output-dir models/crop_disease --require-manifest
python -m advisory.ml.evaluate --model-dir models/crop_disease \
  --data-dir data/datasets
```

Evaluation writes per-class precision, recall, F1, support, and false-negative
rates. Farmer image classification remains disabled unless metadata quality is
`production_candidate`; otherwise diagnostics return `advisory_fallback`.

Render/Railway style API-only deployments can use `Procfile`, `render.yaml`,
or `scripts/deploy.sh`. Combined single-container deployments should build the
frontend first and set `SERVE_FRONTEND=true`.

## Troubleshooting

`http://localhost:8002` returns JSON or API responses:

- This is expected. Port `8002` is Phase 1 AI/RAG in Docker.
- Open `http://localhost:8001` for the main Docker app.

Docker Desktop reports no space left on device:

```bash
docker system df
docker builder prune
docker system prune -a --volumes
```

The last command removes unused images, containers, build cache, and volumes.
Back up any local database/uploads before pruning volumes.

Chatbot is slow or times out:

- Start Phase 1 and Ollama if using local AI.
- Lower `PHASE1_TIMEOUT_S`, `OLLAMA_READ_TIMEOUT_S`, and
  `CHAT_REALTIME_TIMEOUT_S` for development.
- Confirm `/api/health/readiness/` reports `phase1_ai` and `ollama` separately.

Disease diagnosis returns `advisory_fallback`:

- The image was accepted, but no production-ready trained classifier was loaded.
- Train or mount `models/crop_disease/efficientnetb3_crop_disease.keras`.
- Re-check `/api/health/readiness/` before exposing image classification to
  farmers.
