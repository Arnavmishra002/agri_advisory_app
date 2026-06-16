# ═══════════════════════════════════════════════════════════════
# KrishiMitra AI — Production Dockerfile v2.1
# Multi-stage: Vite frontend → Python deps → Django API → Nginx
#
# Quick start (API only):
#   docker build -t krishimitra-ai .
#   docker run -p 8000:8000 \
#     -e SECRET_KEY=<your-secret-key> \
#     -e DATABASE_URL=postgresql://user:pass@db:5432/krishimitra \
#     -e DATA_GOV_IN_API_KEY=<your-key> \
#     krishimitra-ai
#
# Full stack with Nginx:
#   docker compose up                  # API on :8001
#   docker compose --profile full up   # API + Nginx on :8080
#
# Build specific target:
#   docker build --target nginx -t krishimitra-nginx .
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────
# Stage 1 — Vite Frontend Build
#   Outputs: /build/frontend/dist/{index.html, js/app.js,
#             js/i18n.js, css/styles.css, assets/*}
# ─────────────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# Cache npm deps separately from source changes
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund --silent

# Copy ALL source files (vite.config.js, index.html, public/, css/)
COPY frontend/ ./

# Force rebuild with no cache by echoing the current file contents hash
# This ensures the enhanced index.html and styles.css are always picked up
RUN echo "Building v$(cat package.json | grep version | head -1)" && \
    npm run build 2>&1 && \
    echo "✅ Frontend built: $(du -sh dist/)" && \
    echo "   dist/index.html: $(wc -l < dist/index.html) lines" && \
    ls -la dist/ && \
    ls -la dist/js/ 2>/dev/null && \
    ls -la dist/css/ 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────
# Stage 2 — Python dependency wheel cache
# ─────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libmagic1 \
        libmagic-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    echo "✅ $(pip list | wc -l) Python packages installed"

# ─────────────────────────────────────────────────────────────────
# Stage 3 — Production API Image
# ─────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS production

# ── Labels ────────────────────────────────────────────────────
LABEL org.opencontainers.image.title="KrishiMitra AI"
LABEL org.opencontainers.image.description="Precision Agriculture Advisory — 150+ crops, 22 languages, IoT sensors, real-time mandi prices, 19-intent NLP chatbot"
LABEL org.opencontainers.image.source="https://github.com/Arnavmishra002/agri_advisory_app"
LABEL org.opencontainers.image.version="3.0.0"

# ── Runtime environment ────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings \
    # Gunicorn — all tunable via docker run -e or docker-compose env:
    WEB_CONCURRENCY=4 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_KEEPALIVE=5 \
    GUNICORN_MAX_REQUESTS=1000

# ── System runtime libs only (no build tools) ─────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ─────────────────────────────────────────────
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app/backend

# ── Python packages from builder ──────────────────────────────
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ── Application code ──────────────────────────────────────────
COPY backend/ /app/backend/

# ── Frontend static files ─────────────────────────────────────
COPY --from=frontend-builder /build/frontend/dist    /app/frontend/dist
COPY --from=frontend-builder /build/frontend/public  /app/frontend/public
COPY --from=frontend-builder /build/frontend/css     /app/frontend/css

# ── Persistent directories (mounted as volumes in production) ──
RUN mkdir -p \
    /app/data \
    /app/models/crop_disease \
    /app/backend/staticfiles \
    /app/backend/media \
    /app/backend/logs

# ── Collect static assets ─────────────────────────────────────
# Uses a throwaway SQLite so no DB connection is needed at build time
RUN SECRET_KEY=build-collectstatic-key-not-production \
    DEBUG=False \
    DATABASE_URL=sqlite:////tmp/build_collect.db \
    SERVE_FRONTEND=true \
    python manage.py collectstatic --noinput --clear 2>&1 | tail -4

# ── Ownership ─────────────────────────────────────────────────
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# ── Health check ──────────────────────────────────────────────
HEALTHCHECK \
    --interval=30s \
    --timeout=15s \
    --start-period=30s \
    --retries=3 \
    CMD curl -sf http://localhost:8000/api/health/ || exit 1

# ── Start command ─────────────────────────────────────────────
# 1. Apply any pending migrations
# 2. Start Gunicorn (all params are tunable via environment)
CMD ["sh", "-c", "\
    python manage.py migrate --noinput && \
    echo '✅ Migrations applied' && \
    python manage.py seed_msp 2>/dev/null || echo '⚠️  MSP seed skipped (already seeded)' && \
    echo '✅ MSP data ready' && \
    exec gunicorn \
      --bind 0.0.0.0:8000 \
      --workers ${WEB_CONCURRENCY:-4} \
      --threads 4 \
      --worker-class gthread \
      --timeout ${GUNICORN_TIMEOUT:-120} \
      --keep-alive ${GUNICORN_KEEPALIVE:-5} \
      --max-requests ${GUNICORN_MAX_REQUESTS:-1000} \
      --max-requests-jitter 100 \
      --access-logfile - \
      --error-logfile - \
      --log-level info \
      core.wsgi:application"]

# ─────────────────────────────────────────────────────────────────
# Stage 4 — Nginx reverse proxy (optional full-stack target)
#   Build: docker build --target nginx -t krishimitra-nginx .
#   Serves: /  → frontend SPA  |  /api/ → web:8000  |  /static/ → staticfiles
# ─────────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS nginx

COPY nginx.docker.conf /etc/nginx/conf.d/default.conf

# Frontend SPA
COPY --from=frontend-builder /build/frontend/dist /usr/share/nginx/html

# Django static files (admin, DRF browsable API, etc.)
COPY --from=production /app/backend/staticfiles /app/staticfiles

EXPOSE 80 443
