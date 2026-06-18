"""
Gunicorn configuration for KrishiMitra AI.
Render/Railway run gunicorn from the repo root; this file changes
the working directory to backend/ so 'core' module is importable.
"""
import os

# Change into the backend directory before starting workers
chdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")

# ── Workers ────────────────────────────────────────────────────────────────────
# PERF FIX: Default to 2 workers instead of 4.
# With TensorFlow EfficientNet-B3 (~400MB per process) and preload_app=True (CoW),
# 2 workers is safe on 1 GB RAM. On Render free (512MB) set WEB_CONCURRENCY=1.
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = 4
worker_class = "gthread"

# ── Memory: preload_app ─────────────────────────────────────────────────────────
# CRIT FIX: preload_app=True makes the master process load Django + ML models ONCE
# and then forks workers. Linux copy-on-write (CoW) means workers share read-only
# pages, reducing per-worker RAM usage from ~500MB to ~50MB for the TF model.
# Without this, each worker independently loads TF → OOM on Render free/starter.
preload_app = True

# ── Timeouts ───────────────────────────────────────────────────────────────────
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# ── Logging ────────────────────────────────────────────────────────────────────
accesslog = "-"
errorlog  = "-"
loglevel  = "info"

# ── Bind ───────────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# ── Forward proxy headers from Render/Railway/Heroku ──────────────────────────
# Without this Django sees plain HTTP internally → SECURE_SSL_REDIRECT causes 400
forwarded_allow_ips = "*"
proxy_allow_ips = "*"

# ── Temp dir for worker heartbeats ─────────────────────────────────────────────
# PERF FIX: Use /dev/shm (RAM-backed tmpfs) for worker temp files.
# This avoids disk I/O for the heartbeat file that workers write every ~0.1s,
# which can cause latency spikes on slow disks in containers.
worker_tmp_dir = "/dev/shm"
