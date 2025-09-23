web: bash -lc "alembic upgrade head && gunicorn -w 2 -k gthread -b 0.0.0.0:$PORT app:app"
