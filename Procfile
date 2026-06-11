# KrishiMitra AI — Procfile
# Used by Render, Railway, Heroku.
# Render runs 'release' before each deploy, then starts 'web'.

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
