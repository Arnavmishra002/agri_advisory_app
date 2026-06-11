"""
Gunicorn configuration for KrishiMitra AI.
Render/Railway run gunicorn from the repo root; this file changes
the working directory to backend/ so 'core' module is importable.
"""
import os

# Change into the backend directory before starting workers
chdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")

# Workers
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
threads = 4
worker_class = "gthread"

# Timeouts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Logging
accesslog = "-"
errorlog  = "-"
loglevel  = "info"

# Bind
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
