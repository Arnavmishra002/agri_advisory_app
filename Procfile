# KrishiMitra AI — Procfile
# Used by Render, Railway, Heroku, and other Procfile-based PaaS.
#
# Render auto-runs the release command before each deploy.
# Set environment variables in the Render dashboard (not here).

# Release: run migrations before the web process starts
release: cd backend && python manage.py migrate --noinput

# Web: start Django with Gunicorn
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
