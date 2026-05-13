#!/usr/bin/env bash
set -euo pipefail

cd /app

wait_for_db() {
    echo "[entrypoint] PostgreSQL 접속 대기..."
    python - <<'PY'
import os, time, sys
import psycopg
host = os.getenv("PG_HOST", "postgres_db")
port = int(os.getenv("PG_PORT", "5432"))
user = os.getenv("PG_USER")
pw   = os.getenv("PG_PASSWORD")
db   = os.getenv("PG_DB", "prepared_blog")
for i in range(60):
    try:
        psycopg.connect(host=host, port=port, user=user, password=pw, dbname=db, connect_timeout=2).close()
        print("[entrypoint] PostgreSQL OK")
        sys.exit(0)
    except Exception as e:
        print(f"[entrypoint] retry {i+1}/60: {e}")
        time.sleep(2)
sys.exit(1)
PY
}

case "${1:-web}" in
    web)
        wait_for_db
        python manage.py migrate --noinput
        python manage.py collectstatic --noinput
        exec gunicorn prepared_blog.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-3}" \
            --threads "${GUNICORN_THREADS:-2}" \
            --timeout 60 \
            --max-requests 1000 \
            --max-requests-jitter 50 \
            --graceful-timeout 30 \
            --forwarded-allow-ips='*' \
            --access-logfile - \
            --error-logfile -
        ;;
    worker)
        wait_for_db
        exec celery -A prepared_blog worker -l "${CELERY_LOG_LEVEL:-INFO}" --concurrency "${CELERY_CONCURRENCY:-2}"
        ;;
    beat)
        wait_for_db
        exec celery -A prepared_blog beat -l "${CELERY_LOG_LEVEL:-INFO}" --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    manage)
        shift
        exec python manage.py "$@"
        ;;
    bash|shell)
        exec bash
        ;;
    *)
        exec "$@"
        ;;
esac
