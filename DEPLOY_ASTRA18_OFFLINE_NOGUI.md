## Развёртывание на Astra Linux 1.8 без интернета и без GUI (без Docker)

Этот документ — “боевой” сценарий развёртывания на предприятии:

- Astra Linux 1.8 (Debian‑совместимая), **без графического интерфейса**.
- **Нет интернета**.
- На системе **не установлены** Docker / Python / PostgreSQL / Redis / Node.js / Nginx.
- Разворачиваем: Django (Gunicorn) + Celery + PostgreSQL + Redis + Nginx (раздача frontend + reverse proxy на backend).

Важно: в таких условиях ключевое — заранее подготовить офлайн‑артефакты и/или иметь доступ к установочному ISO/локальному репозиторию предприятия.

---

## 0) Что (минимально) нужно подготовить заранее

На машине с интернетом подготовьте “офлайн‑пакет” (лучше как один архив):

### 0.1. Исходники проекта

- Архив проекта `PlanOptimization.tar.gz` (включая `frontend/`, `requirements.txt`, миграции, инструкции).

### 0.2. Python для Astra (два варианта)

**Вариант A (рекомендуется): поставить Python из репозитория/ISO Astra**

- Нужны пакеты: `python3`, `python3-venv`, `python3-dev`, `build-essential`, `libpq-dev`.
- Этот вариант проще, но зависит от доступности пакетов на предприятии (ISO/локальный репозиторий).

**Вариант B (если нет пакетов Python): привезти Python как архив**

- Привезти исходники CPython (например, `Python-3.11.x.tgz`) и собрать на месте.
- Понадобятся системные dev‑пакеты (gcc/make, zlib, ssl, ffi и т.д.). Без них сборка не пройдёт.

### 0.3. Python wheels (зависимости проекта)

На машине с интернетом, **на Linux x86_64** (важно!), собрать wheels:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
mkdir -p offline/python-wheels
pip wheel -r requirements.txt -w offline/python-wheels
```

> Колёса, собранные на Windows, почти всегда **не подойдут** для Linux. Делайте сборку wheels на Linux.

### 0.4. Node.js (frontend)

Для запуска на сервере Node.js **не обязателен**, если вы привезёте уже собранный фронт.

- Соберите фронтенд на машине с интернетом:

```bash
cd frontend
npm ci
npm run build
```

- В офлайн‑пакет положите **только** `frontend/dist/` (и при необходимости `frontend/nginx.conf`).

Node.js понадобится только если вы хотите пересобирать фронт на месте.

### 0.5. PostgreSQL / Redis / Nginx пакеты (офлайн)

На предприятии это обычно ставится:

- либо с установочного ISO Astra,
- либо из внутреннего локального репозитория,
- либо администратор выдаёт набор `.deb`.

Вам понадобятся пакеты:

- PostgreSQL сервер и клиент (`postgresql`, `postgresql-client`, `postgresql-contrib`)
- Redis (`redis-server`)
- Nginx (`nginx`)

---

## 1) Развёртывание на Astra Linux (на предприятии)

Далее команды выполняются в терминале. Предполагается, что у вас есть `sudo`.

### 1.1. Создать пользователя приложения и каталоги

```bash
sudo useradd -r -m -d /opt/planopt -s /usr/sbin/nologin planopt || true
sudo mkdir -p /opt/planopt/app
sudo mkdir -p /opt/planopt/venv
sudo mkdir -p /opt/planopt/logs
sudo chown -R planopt:planopt /opt/planopt
```

### 1.2. Установить системные пакеты (из ISO/локального репо)

Пример (названия пакетов могут отличаться, но обычно такие):

```bash
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-dev \
  build-essential libpq-dev \
  postgresql postgresql-contrib \
  redis-server \
  nginx
```

Если на вашей Astra Python версии < 3.11 — это не всегда критично на старте, но в идеале держать Python 3.11+.

### 1.3. Развернуть код приложения

Скопируйте архив проекта на сервер и распакуйте:

```bash
sudo -u planopt tar xzf /path/to/PlanOptimization_offline.tar.gz -C /opt/planopt/app --strip-components=1
```

Проверьте, что в `/opt/planopt/app` есть `manage.py`, `production_planner/`, `planner/`, `frontend/dist/` (если привезли сборку).

### 1.4. Создать виртуальное окружение и поставить зависимости (только локальные wheels)

```bash
sudo -u planopt python3 -m venv /opt/planopt/venv
sudo -u planopt /opt/planopt/venv/bin/pip install --no-index --find-links=/opt/planopt/app/offline/python-wheels -r /opt/planopt/app/requirements.txt
```

### 1.5. Настроить PostgreSQL

Запуск сервиса:

```bash
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

Создать пользователя/БД (один раз):

```bash
sudo -u postgres createuser planner --createdb --no-superuser --no-createrole || true
sudo -u postgres psql -c "ALTER USER planner WITH ENCRYPTED PASSWORD 'planner';"
sudo -u postgres createdb production_planner -O planner || true
```

Опционально включить расширения:

```bash
sudo -u postgres psql -d production_planner -c 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";'
```

### 1.6. Настроить Redis

```bash
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 1.7. Настроить переменные окружения приложения

Создайте файл окружения:

```bash
sudo -u planopt cp /opt/planopt/app/.env.example /opt/planopt/app/.env
sudo -u planopt sed -i 's/^DJANGO_DEBUG=.*/DJANGO_DEBUG=0/' /opt/planopt/app/.env
sudo -u planopt sed -i 's/^POSTGRES_HOST=.*/POSTGRES_HOST=127.0.0.1/' /opt/planopt/app/.env
sudo -u planopt sed -i 's/^REDIS_CACHE_URL=.*/REDIS_CACHE_URL=redis:\\/\\/127.0.0.1:6379\\/1/' /opt/planopt/app/.env
sudo -u planopt sed -i 's/^CELERY_BROKER_URL=.*/CELERY_BROKER_URL=redis:\\/\\/127.0.0.1:6379\\/0/' /opt/planopt/app/.env
sudo -u planopt sed -i 's/^CELERY_RESULT_BACKEND=.*/CELERY_RESULT_BACKEND=redis:\\/\\/127.0.0.1:6379\\/0/' /opt/planopt/app/.env
```

Важно: задайте `DJANGO_SECRET_KEY` (свой уникальный).

### 1.8. Миграции и статика

```bash
cd /opt/planopt/app
sudo -u planopt /opt/planopt/venv/bin/python manage.py migrate --noinput
sudo -u planopt /opt/planopt/venv/bin/python manage.py collectstatic --noinput
```

---

## 2) Настройка systemd (Gunicorn + Celery)

В репозитории есть шаблоны:

- `deploy/systemd/planopt-web.service`
- `deploy/systemd/planopt-worker.service`

Скопируйте их:

```bash
sudo cp /opt/planopt/app/deploy/systemd/planopt-web.service /etc/systemd/system/planopt-web.service
sudo cp /opt/planopt/app/deploy/systemd/planopt-worker.service /etc/systemd/system/planopt-worker.service
sudo systemctl daemon-reload
sudo systemctl enable planopt-web planopt-worker
sudo systemctl start planopt-web planopt-worker
```

Проверка:

```bash
sudo systemctl status planopt-web
sudo systemctl status planopt-worker
sudo journalctl -u planopt-web -n 200 --no-pager
sudo journalctl -u planopt-worker -n 200 --no-pager
```

---

## 3) Настройка Nginx (frontend + reverse proxy /api → backend)

В репозитории есть конфиг:

- `deploy/nginx/planopt.conf`

Скопируйте:

```bash
sudo cp /opt/planopt/app/deploy/nginx/planopt.conf /etc/nginx/sites-available/planopt.conf
sudo ln -sf /etc/nginx/sites-available/planopt.conf /etc/nginx/sites-enabled/planopt.conf
sudo nginx -t
sudo systemctl reload nginx
```

Порты по умолчанию:

- Nginx: `80`
- Gunicorn (локально): `127.0.0.1:8000`

---

## 4) Мини‑проверка сценариев (без GUI)

Проверить API:

```bash
curl -s http://127.0.0.1/api/projects/ | head
curl -s http://127.0.0.1/api/reports/gantt/?project_id=1 | head
```

Проверить фронт (отдачу статических файлов):

```bash
curl -I http://127.0.0.1/
```

---

## 5) Нужно ли редактировать проект под эти условия?

Минимально — уже готово:

- Backend использует переменные окружения `POSTGRES_*`/`REDIS_*`, то есть не “зашит” под Docker.
- Добавлен `STATIC_ROOT` и WhiteNoise (можно и без него, если статику отдаёт Nginx).
- Есть `requirements.txt`, wheels можно собрать офлайн.

Что **желательно** сделать перед развёртыванием:

- **Собирать Python wheels на Linux**, максимально близком к Astra (Debian‑подобный), чтобы избежать проблем с бинарными зависимостями.
- Держать `DJANGO_DEBUG=0` и корректный `DJANGO_ALLOWED_HOSTS`.
- (Опционально) добавить отдельный `requirements.lock` (пины версий) — чтобы на предприятии сборка была повторяемой.

