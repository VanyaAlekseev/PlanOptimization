#!/usr/bin/env sh
set -eu

echo "=== ps ==="
docker compose -f docker-compose.offline.yml ps

echo "=== logs web (last 200) ==="
docker logs --tail=200 planoptimization-web-1 || true

echo "=== logs worker (last 200) ==="
docker logs --tail=200 planoptimization-worker-1 || true

echo "=== logs frontend (last 200) ==="
docker logs --tail=200 planoptimization-frontend-1 || true

echo "=== compose services check ==="
docker compose -f docker-compose.offline.yml config --services

