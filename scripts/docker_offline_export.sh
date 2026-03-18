#!/usr/bin/env sh
set -eu

# Сборка и экспорт Docker-образов в один tar (для офлайн переноса).
#
# Использование:
#   ./scripts/docker_offline_export.sh 2026-03-18
# или
#   PLANOPT_TAG=2026-03-18 ./scripts/docker_offline_export.sh

TAG="${1:-${PLANOPT_TAG:-offline}}"
OUT="planopt-images-${TAG}.tar"

if ! docker info >/dev/null 2>&1; then
  echo "Ошибка: Docker недоступен. Проверьте, что Docker Engine запущен и доступен из терминала."
  exit 10
fi

echo "[1/4] Build compose images... (может занять несколько минут)"
docker compose build

echo "[2/4] Detect compose image names and tag..."

prefix="$(basename "$PWD")"
prefix_lc="$(echo "$prefix" | tr '[:upper:]' '[:lower:]')"
WEB_IMAGE="${prefix_lc}-web:latest"
WORKER_IMAGE="${prefix_lc}-worker:latest"
FRONTEND_IMAGE="${prefix_lc}-frontend:latest"

has_image() {
  docker image inspect "$1" >/dev/null 2>&1
}

if ! has_image "$WEB_IMAGE" || ! has_image "$WORKER_IMAGE" || ! has_image "$FRONTEND_IMAGE"; then
  echo "Compose image names were not found by expected prefix. Fallback to docker images scanning..."
  all_imgs="$(docker images --format '{{.Repository}}:{{.Tag}}')"
  WEB_IMAGE="$(echo "$all_imgs" | awk '$0 ~ /-web:latest$/ {print $0; exit}')"
  WORKER_IMAGE="$(echo "$all_imgs" | awk '$0 ~ /-worker:latest$/ {print $0; exit}')"
  FRONTEND_IMAGE="$(echo "$all_imgs" | awk '$0 ~ /-frontend:latest$/ {print $0; exit}')"
fi

if ! has_image "$WEB_IMAGE" || ! has_image "$WORKER_IMAGE" || ! has_image "$FRONTEND_IMAGE"; then
  echo "Не удалось определить имена образов web/worker/frontend."
  echo "Ожидались: ${prefix_lc}-web:latest / ${prefix_lc}-worker:latest / ${prefix_lc}-frontend:latest"
  echo "Текущее состояние docker images (фрагмент):"
  docker images | awk 'NR==1 || /web|worker|frontend/ {print}'
  exit 1
fi

if [ -z "${WEB_IMAGE}" ] || [ -z "${WORKER_IMAGE}" ] || [ -z "${FRONTEND_IMAGE}" ]; then
  echo "Не удалось автоматически определить имена образов web/worker/frontend."
  echo "Вывод docker compose images:"
  echo "${IMAGES_RAW}"
  exit 1
fi

docker tag "${WEB_IMAGE}" "planopt/web:${TAG}"
docker tag "${WORKER_IMAGE}" "planopt/web:${TAG}"
docker tag "${FRONTEND_IMAGE}" "planopt/frontend:${TAG}"

echo "[3/4] Ensure base images for offline mode..."

SKIP_PULL_BASE="${SKIP_PULL_BASE:-false}"

ensure_image() {
  img="$1"
  if docker image inspect "${img}" >/dev/null 2>&1; then
    echo "  - already present: ${img}"
    return 0
  fi
  if [ "${SKIP_PULL_BASE}" = "true" ]; then
    echo "  - missing and SKIP_PULL_BASE=true: ${img}"
    return 1
  fi
  echo "  - pulling: ${img}"
  docker pull "${img}"
}

ensure_image "postgres:14" || true
ensure_image "redis:7" || true
ensure_image "nginx:1.27-alpine" || true
ensure_image "python:3.12-slim" || true
ensure_image "node:20-alpine" || true

echo "[4/4] Export to ${OUT}..."
docker save -o "${OUT}" \
  "planopt/web:${TAG}" \
  "planopt/frontend:${TAG}" \
  postgres:14 redis:7 nginx:1.27-alpine python:3.12-slim node:20-alpine

echo "Done: ${OUT}"

