#!/usr/bin/env sh
set -eu

# Импорт Docker-образов из tar и запуск compose в офлайн-режиме.
#
# Использование:
#   ./scripts/docker_offline_import_run.sh /path/to/planopt-images-2026-03-18.tar 2026-03-18
# или (если используете переменную окружения):
#   PLANOPT_TAG=2026-03-18 ./scripts/docker_offline_import_run.sh /path/to/planopt-images-2026-03-18.tar

TAR_PATH="${1:-}"
if [ -z "${TAR_PATH}" ]; then
  echo "Usage: PLANOPT_TAG=... $0 /path/to/planopt-images-<tag>.tar"
  exit 2
fi

TAG="${2:-${PLANOPT_TAG:-offline}}"

echo "[1/2] Loading images from ${TAR_PATH}..."
if ! docker info >/dev/null 2>&1; then
  echo "Ошибка: Docker недоступен на этой машине."
  exit 11
fi
docker load -i "${TAR_PATH}"

echo "[2/2] Starting compose (offline)..."
PLANOPT_TAG="${TAG}" docker compose -f docker-compose.offline.yml up -d --no-build --pull never

echo "Done."
echo "Frontend: http://localhost:8080/"
echo "Backend:  http://localhost:8000/"

