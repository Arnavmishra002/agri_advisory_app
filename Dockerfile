# ═══════════════════════════════════════════════════════════════
# KrishiMitra AI — Production Dockerfile v2.0
# Multi-stage: Vite frontend → Python deps → Django API → Nginx
#
# Quick start:
#   docker build -t krishimitra-ai .
#   docker run -p 8000:8000 \
#     -e SECRET_KEY=<your-secret-key> \
#     -e DATABASE_URL=postgresql://user:pass@db:5432/krishimitra \
#     -e DATA_GOV_IN_API_KEY=<your-key> \
#     krishimitra-ai
#
# Full stack (recommended):
#   docker compose up
# ═══════════════════════════════════════════════════════════════

# ── Stage 1: Vite Frontend Build ────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend

# Cache node_modules layer
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund --silent

# Build (copies app.js, i18n.js, index.html, styles.css → dist/)
COPY frontend/ ./
RUN npm run build && \
    echo "✅ Frontend built: $(du -sh dist/ | cut -f1)"

# ── Stage 2: Python Dependency Cache ────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libmagic1 libmagic-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    echo "✅ Python deps installed"

# ── Stage 3: Production API Image ───────────────────────────────
FROM python:3.11-slim AS production

LABEL org.opencontainers.image.title="KrishiMitra AI"
LABEL org.opencontainers.image.description="Precision Agriculture Advisory for Indian Farmers — 80 crops, 22 languages, IoT sensors, real-time mandi prices"
LABEL org.opencontainers.image.source="https://github.com/arnav-mishra/agri_advisory_app"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings \
    # Tunable at runtime
    WEB_CONCURRENCY=4 \
    GUNICORN_TIMEOUT=120 \
    GUNICORN_KEEPALIVE=5 \
    GUNICORN_MAX_REQUESTS=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libmagic1 curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root security
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

WORKDIR /app/backend

# Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
                    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Application source
COPY backend/ /app/backend/

# Frontend static assets
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# Runtime directories
RUN mkdir -p \
    /app/data \
    /app/models/crop_disease \
    /app/backend/staticfiles \
    /app/backend/media \
    /app/backend/logs

# Collect static files (dummy key — no secrets at build time)
RUN SECRET_KEY=build-collectstatic-only \
    DEBUG=False \
    DATABASE_URL=sqlite:////tmp/build.db \
    SERVE_FRONTEND=true \
    python manage.py collectstatic --noinput --clear 2>&1 | tail -3

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=15s --start-period=20s --retries=3 \
    CMD curl -sf http://localhost:8000/api/health/ || exit 1

# Startup: migrate → serve
CMD ["sh", "-c", "\
    python manage.py migrate --noinput && \
    echo '✅ Migrations complete' && \
    gunicorn \
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

# ── Stage 4: Nginx Reverse Proxy (optional full-stack target) ───
# Build: docker build --target nginx -t krishimitra-nginx .
FROM nginx:1.27-alpine AS nginx

COPY nginx.docker.conf /etc/nginx/conf.d/default.conf
COPY --from=frontend-builder /build/frontend/dist /usr/share/nginx/html
COPY --from=production /app/backend/staticfiles /app/staticfiles

EXPOSE 80 443
