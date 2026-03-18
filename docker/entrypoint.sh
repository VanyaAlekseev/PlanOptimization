#!/usr/bin/env sh
set -e

echo "Waiting for database..."
python -c "import os, time; import psycopg; 
host=os.getenv('POSTGRES_HOST','db'); port=os.getenv('POSTGRES_PORT','5432'); 
db=os.getenv('POSTGRES_DB','production_planner'); user=os.getenv('POSTGRES_USER','planner'); pw=os.getenv('POSTGRES_PASSWORD','planner'); 
for i in range(60):
  try:
    psycopg.connect(host=host, port=port, dbname=db, user=user, password=pw).close()
    break
  except Exception:
    time.sleep(1)
else:
  raise SystemExit('DB not ready')"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static..."
python manage.py collectstatic --noinput

exec "$@"

