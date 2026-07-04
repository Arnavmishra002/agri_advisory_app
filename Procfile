# KrishiMitra AI — Procfile
# Used by Render, Railway, Heroku, and other Procfile-based platforms.
#
# IMPORTANT: Render may override this with dashboard settings.
# If getting "No module named 'core'", set these in Render dashboard:
#   Start Command: cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 4 --worker-class gthread --timeout 120 core.wsgi:application
#   Build Command: pip install -r requirements-production.txt && cd backend && python manage.py collectstatic --noinput

# ── Release phase (runs once before each deploy) ─────────────────────────────
# Order matters:
#   1. migrate  — schema changes first (zero-downtime deploys)
#   2. seed_msp — idempotent MSP price seeding
#   3. warm_cache — pre-warms Agmarknet + weather caches so first user request
#                   is sub-100ms instead of waiting for cold API calls
release: cd backend && \
  python manage.py migrate --noinput && \
  python manage.py seed_msp 2>/dev/null || true && \
  python manage.py warm_cache

# ── Web process ──────────────────────────────────────────────────────────────
web: cd backend && gunicorn \
  --bind 0.0.0.0:$PORT \
  --workers ${WEB_CONCURRENCY:-4} \
  --threads 4 \
  --worker-class gthread \
  --timeout ${GUNICORN_TIMEOUT:-120} \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  core.wsgi:application

# ── Celery worker (optional — only needed when REDIS_URL is set) ─────────────
# Handles async post-response writes: FarmerInteractionLog, session memory.
# Without Redis, chatbot.py falls back to synchronous inline writes.
# Enable on Render: add a Background Worker with this command.
worker: cd backend && celery \
  --app core.celery \
  worker \
  --loglevel=info \
  --concurrency=2 \
  --max-tasks-per-child=1000 \
  --without-gossip \
  --without-mingle \
  --queues=celery

# ── Celery beat (optional — periodic task scheduler) ────────────────────────
# Runs scheduled tasks like cache refresh, MSP updates.
# Only start this if you also have a Celery worker running.
# beat: cd backend && celery --app core.celery beat --loglevel=info

# ── Phase 1 local LLM/RAG service (optional) ────────────────────────────────
# Requires Ollama plus the Phase 1 vector store/knowledge assets.
# If not started, /api/health/readiness/ reports phase1_ai=offline and chat
# falls back to direct Ollama/Gemini/rules with clear source labels.
phase1: cd phase1 && uvicorn main:app --host 0.0.0.0 --port ${PHASE1_PORT:-8001}
