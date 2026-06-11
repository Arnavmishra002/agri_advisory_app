# KrishiMitra AI — Procfile
# Used by Render, Railway, Heroku, and other Procfile-based platforms.
#
# IMPORTANT: Render may override this with dashboard settings.
# If getting "No module named 'core'", set these in Render dashboard:
#   Start Command: cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 4 --threads 4 --worker-class gthread --timeout 120 core.wsgi:application
#   Build Command: pip install -r requirements-production.txt && cd backend && python manage.py collectstatic --noinput

release: cd backend && python manage.py migrate --noinput

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
