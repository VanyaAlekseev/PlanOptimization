## Офлайн развёртывание через Docker (сборка дома → перенос на предприятие)

Цель: на предприятии (Astra Linux, без интернета) поднять приложение **без установки Python/PostgreSQL/Redis/Node/Nginx в ОС**.
Нужно только установить Docker Engine + docker compose plugin и заранее привезти **готовые образы**.

В проект добавлен отдельный compose‑файл: `docker-compose.offline.yml` — он **не собирает** образы, а использует только `image:`.

---

## 1) На домашней машине (есть интернет): сборка и экспорт образов

### 1.1. Требования

- Docker Engine установлен
- доступ в интернет (скачать базовые образы и зависимости)

### 1.2. Выбрать тег сборки (версия пакета)

Тег используется для имен образов и tar-архива (по умолчанию `offline`).
Пример тега: `2026-03-18`.

### 1.3. Собрать образы приложения

В корне репозитория:

PowerShell (рекомендуется вам на “дома”):

```powershell
.\scripts\docker_offline_export.ps1 2026-03-18
```

Если вы запускаете в bash:

```bash
./scripts/docker_offline_export.sh 2026-03-18
```

Скрипт делает всё автоматически:

- собирает compose‑образы (`docker compose build`);
- **автоматически определяет реальные имена образов** `web/worker/frontend` через `docker compose images`;
- тэгирует их в стандартные:
  - `planopt/web:${PLANOPT_TAG}`
  - `planopt/frontend:${PLANOPT_TAG}`
- подтягивает базовые образы (postgres/redis/nginx/python/node);
- экспортирует всё в один tar: `planopt-images-${PLANOPT_TAG}.tar`.

Примечание по времени:
- шаг `docker compose build` и “pull базовых образов” могут занять несколько минут (первый запуск особенно дольше).
- если на вашей машине уже есть `postgres:14`, `redis:7`, `nginx:1.27-alpine`, `python:3.12-slim`, `node:20-alpine`, можно ускорить, запустив:

PowerShell:
```powershell
$env:SKIP_PULL_BASE="true"
.\scripts\docker_offline_export.sh 2026-03-18
```

Bash:
```bash
SKIP_PULL_BASE=true ./scripts/docker_offline_export.sh 2026-03-18
```

Если скрипт не смог определить имена образов (редко, но возможно), он выведет таблицу:

```bash
docker compose images
```

и завершится с ошибкой.

### 1.4. Скачать (pull) базовые образы, которые нужны офлайн

Этот шаг уже включён в `scripts/docker_offline_export.sh`. Если вы делаете всё вручную, то:

```bash
docker pull postgres:14
docker pull redis:7
docker pull nginx:1.27-alpine
docker pull python:3.12-slim
docker pull node:20-alpine
```

### 1.5. Экспортировать образы в один tar

Этот шаг тоже включён в `scripts/docker_offline_export.sh`. Если нужно вручную:

```bash
docker save -o planopt-images-${PLANOPT_TAG}.tar \
  planopt/web:2026-03-18 \
  planopt/frontend:2026-03-18 \
  postgres:14 redis:7 nginx:1.27-alpine python:3.12-slim node:20-alpine
```

Скопируйте на флешку:

- `planopt-images-${PLANOPT_TAG}.tar`
- архив с исходниками проекта (нужны compose‑файлы и `db/init/*`):
  - например, `PlanOptimization.tar.gz`

---

## 2) На предприятии (без интернета): импорт и запуск

### 2.1. Установить Docker

На Astra Linux без интернета Docker ставится из:

- ISO/локального репозитория предприятия, или
- заранее привезённых `.deb`.

Вам нужен:

- `docker` (engine)
- `docker compose` (plugin)

Проверка:

```bash
docker version
docker compose version
```

### 2.2. Импортировать образы

Скопируйте `planopt-images-2026-03-18.tar` на сервер и выполните:

```bash
docker load -i planopt-images-2026-03-18.tar
```

На bash/ Linux можно явно указать тег:

```bash
docker load -i planopt-images-2026-03-18.tar
```

Проверьте:

```bash
docker images | grep planopt
```

### 2.3. Распаковать проект (compose‑файлы)

```bash
mkdir -p ~/planopt
tar xzf /path/to/PlanOptimization.tar.gz -C ~/planopt
cd ~/planopt/PlanOptimization
```

### 2.4. Запустить compose офлайн

```bash
PLANOPT_TAG=2026-03-18 docker compose -f docker-compose.offline.yml up -d --no-build --pull never
```

Открыть:

- Frontend: `http://<ip>:8080/`
- Backend: `http://<ip>:8000/`
- Admin: `http://<ip>:8000/admin/`

### 2.5. Проверка логов

```bash
docker compose -f docker-compose.offline.yml ps
docker compose -f docker-compose.offline.yml logs -f --tail=200 web
docker compose -f docker-compose.offline.yml logs -f --tail=200 worker
```

---

## 3) Важно про БД и миграции

При старте контейнера `web` выполняет:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

Это означает, что база данных будет создана/обновлена автоматически при первом запуске, а Django начнёт читать/писать данные через ORM.

---

## 4) Режим “строго офлайн” (без попыток pull)

Запускайте с параметром:

```bash
docker compose -f docker-compose.offline.yml up -d --no-build --pull never
```

Так вы гарантируете, что Docker не будет пытаться что‑то скачать.

