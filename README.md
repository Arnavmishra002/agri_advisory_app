# KrishiMitra — Agricultural Advisory App

Monorepo with a **Django + DRF API** (`backend/`) and a **standalone Vite frontend** (`frontend/`).

## Project layout

```
agri_advisory_app/
├── backend/              # Django API (manage.py, advisory/, core/)
├── frontend/             # Vite static UI (VITE_API_BASE_URL → API)
├── scripts/              # Ops: deploy, quick_services_check, production verify
├── docs/                 # Architecture & service audit
├── manage.py             # Wrapper — runs backend/manage.py from repo root
├── Dockerfile            # Multi-stage: API + optional nginx UI
└── docker-compose.yml
```

**Tests:** The pytest suite under `tests/` was removed. Use `python scripts/quick_services_check.py` or `python scripts/production_service_verification.py` for smoke checks.

## Quick start (backend)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # SECRET_KEY, DATA_GOV_IN_API_KEY, GOOGLE_AI_API_KEY
python manage.py migrate    # from repo root
python manage.py runserver
```

- API root: http://127.0.0.1:8000/
- Health: http://127.0.0.1:8000/api/health/
- Swagger: http://127.0.0.1:8000/api/schema/swagger-ui/

Equivalent from `backend/`: `cd backend && python manage.py runserver`

## Quick start (frontend)

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173 — set `VITE_API_BASE_URL=http://localhost:8000` in `frontend/.env`.

## Run both (local dev)

1. Terminal A: `python manage.py runserver` (port 8000)
2. Terminal B: `cd frontend && npm run dev` (port 5173)

CORS allows `localhost:5173` when `DEBUG=True`.

## Optional: serve built UI from Django

```bash
cd frontend && npm run build
export SERVE_FRONTEND=true
python manage.py runserver
```

Built files: `frontend/dist/`.

## Docker

```bash
# API only (host port 8001)
docker compose up web --build

# API + nginx static UI (host port 8080)
docker compose --profile full up --build
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Django secret |
| `DEBUG` | `true` for local dev |
| `DATABASE_URL` | Postgres/SQLite URL |
| `DATA_GOV_IN_API_KEY` | Live mandi prices ([data.gov.in](https://data.gov.in/user/register)) |
| `GOOGLE_AI_API_KEY` | Gemini chatbot |
| `CORS_ALLOWED_ORIGINS` | Production frontend origin(s) |
| `SERVE_FRONTEND` | Serve `frontend/dist` from Django |
| `VITE_API_BASE_URL` | Frontend → API (in `frontend/.env`) |

## Verification (no pytest)

```bash
python manage.py check
python scripts/quick_services_check.py
python scripts/production_service_verification.py
```

Pre-push: `python scripts/check_before_push.py`

## Deployment

- **API only:** Gunicorn from `backend/` (`Procfile`, Render `rootDir: backend`) — host frontend on CDN.
- **Combined:** Build frontend, set `SERVE_FRONTEND=true`, or use `docker compose --profile full`.

See `Dockerfile`, `render.yaml`, `scripts/deploy.sh`.
