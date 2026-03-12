## Инструкция по запуску проекта в Astra Linux без интернета

Этот документ описывает, как развернуть полностью готовый проект (Django + Celery + PostgreSQL + Redis + React/TypeScript фронтенд) **на отдельном рабочем месте под Astra Linux**, где:

- нет доступа в интернет;
- заранее не установлены Python‑пакеты, Node.js, PostgreSQL, Redis и т.д.;
- у вас есть **архив проекта** и возможность **заранее подготовить офлайн‑зависимости** на машине с интернетом.

Инструкция разбита на два этапа:

- **Этап A (дома/в институте, где есть интернет)** — подготовка офлайн‑пакетов.
- **Этап B (на предприятии, Astra Linux, без интернета)** — установка и запуск.

---

## Этап A. Подготовка офлайн‑зависимостей (там, где есть интернет)

### A1. Клонирование проекта и базовая проверка

- Склонируйте репозиторий или скопируйте текущую рабочую директорию `PlanOptimization`.
- Убедитесь, что в корне есть файлы:
  - `manage.py`, `production_planner/`, `planner/`
  - `requirements.txt`, `package.json` (когда появится фронтенд), `docker-compose.yml`
  - этот файл `OFFLINE_SETUP_ASTRA_LINUX.md`

### A2. Подготовка Python‑зависимостей

1. Создайте виртуальное окружение Python (на Linux/Windows — не принципиально):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. Установите зависимости бэкенда:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Соберите **колесо‑архивы** всех установленных пакетов в папку `offline/python-wheels`:

   ```bash
   mkdir -p offline/python-wheels
   pip wheel -r requirements.txt -w offline/python-wheels
   ```

   В результате в `offline/python-wheels/` появятся `.whl`‑файлы (`Django‑…whl`, `celery‑…whl`, `psycopg‑…whl` и т.д.).

### A3. Подготовка Node.js/Frontend‑зависимостей (React + TypeScript)

Предполагается, что фронтенд будет лежать, например, в каталоге `frontend/` (путь можно скорректировать под фактическую структуру).

1. В каталоге фронтенда выполните:

   ```bash
   cd frontend
   npm install
   npm run build        # или другая команда сборки, например: npm run dev/build
   cd ..
   ```

2. Скопируйте папку `node_modules` и артефакты сборки в общий `offline`‑каталог:

   ```bash
   mkdir -p offline/frontend
   cp -r frontend/node_modules offline/frontend/node_modules
   cp -r frontend/dist        offline/frontend/dist  # или build, в зависимости от конфигурации
   cp frontend/package.json   offline/frontend/
   cp frontend/package-lock.json offline/frontend/ 2>/dev/null || true
   ```

   > На целевой машине без интернета **не нужно** запускать `npm install`, если вы перенесёте `node_modules` вместе с проектом.

### A4. Подготовка архивов PostgreSQL/Redis (опционально)

На большинстве инсталляций Astra Linux есть доступ к штатным репозиториям, но по условию интернета нет. Обычно БД и Redis ставятся из **внутренних корпоративных репозиториев**. Если такой репозиторий недоступен, вам нужно:

- либо согласовать с админом предприятия офлайн‑установку пакетов `postgresql`, `postgresql-client`, `redis-server` (из их репозиториев/ISO‑носителей),
- либо подготовить `.deb`‑пакеты этих сервисов заранее (за рамками этого проекта).

В этом файле предполагается, что на Astra Linux будут доступны стандартные системные пакеты PostgreSQL и Redis (хотя бы с установочного ISO).

### A5. Подготовка финального архива для переноса

1. Убедитесь, что в корне проекта есть каталог `offline/` со всеми подготовленными зависимостями.
2. Создайте единый архив:

   ```bash
   cd ..
   tar czf PlanOptimization_offline.tar.gz PlanOptimization
   ```

3. Скопируйте `PlanOptimization_offline.tar.gz` на переносной носитель (флешка и т.п.).

---

## Этап B. Развёртывание на Astra Linux без интернета

Ниже — команды в стиле Debian/Ubuntu (Astra Linux совместима на уровне пакетов). При необходимости конкретные имена пакетов можно скорректировать под используемую редакцию Astra.

### B1. Распаковка проекта

1. Скопируйте `PlanOptimization_offline.tar.gz` на целевую машину.
2. Распакуйте:

   ```bash
   mkdir -p ~/projects
   cd ~/projects
   tar xzf /path/to/PlanOptimization_offline.tar.gz
   cd PlanOptimization
   ```

### B2. Установка системных пакетов (через локальный репозиторий/ISO)

Требуются (минимально):

- Python 3.11+ и dev‑заголовки;
- компилятор C (для возможных бинарных расширений);
- PostgreSQL 14+ и клиентские утилиты;
- Redis‑сервер;
- Node.js (если на сервере потребуется пересборка фронтенда).

Пример (имена пакетов могут отличаться):

```bash
sudo apt-get install \
  python3 python3-venv python3-dev build-essential \
  postgresql postgresql-contrib libpq-dev \
  redis-server \
  nodejs npm
```

> Если на предприятии есть ограничения на установку этих пакетов, этот шаг должен выполняться администратором, возможно, с использованием внутреннего репозитория или установочного ISO.

### B3. Настройка PostgreSQL

1. Убедитесь, что PostgreSQL запущен:

   ```bash
   sudo systemctl enable postgresql
   sudo systemctl start postgresql
   ```

2. Создайте пользователя и базу данных, соответствующие `POSTGRES_*` из `.env` (по умолчанию: `planner` / `planner` / `production_planner`):

   ```bash
   sudo -u postgres createuser planner --createdb --no-superuser --no-createrole
   sudo -u postgres psql -c "ALTER USER planner WITH ENCRYPTED PASSWORD 'planner';"
   sudo -u postgres createdb production_planner -O planner
   ```

### B4. Настройка Redis

1. Запустите Redis:

   ```bash
   sudo systemctl enable redis-server
   sudo systemctl start redis-server
   ```

2. Для внутренней сети по умолчанию достаточно локального доступа `127.0.0.1:6379`, который уже прописан в `settings.py`.

### B5. Настройка Python‑окружения и установка зависимостей из `offline/python-wheels`

1. Создайте виртуальное окружение:

   ```bash
   cd ~/projects/PlanOptimization
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Установите зависимости **без интернета**, только из локальной папки:

   ```bash
   pip install --no-index --find-links=offline/python-wheels -r requirements.txt
   ```

### B6. Подготовка переменных окружения

1. Создайте файл `.env` на основе `.env.example`:

   ```bash
   cp .env.example .env
   ```

2. При необходимости скорректируйте значения:

   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` (обычно `localhost`),
   - `REDIS_CACHE_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`,
   - `DJANGO_SECRET_KEY` (на боевой машине лучше сменить).

### B7. Применение миграций и создание суперпользователя

С активированным виртуальным окружением:

```bash
cd ~/projects/PlanOptimization
source .venv/bin/activate

python manage.py migrate
python manage.py createsuperuser
```

### B8. Подготовка и запуск фронтенда (React + TypeScript)

Есть два пути:

1. **Предварительно собранный фронтенд**:
   - Если вы перенесли `offline/frontend/dist` (или `build`) и настроите Django/NGINX так, чтобы он раздавал эти статические файлы, на целевой машине **не нужно** запускать `npm install`.
   - В этом случае достаточно настроить:
     - `STATIC_ROOT` / `STATICFILES_DIRS` в `settings.py` или отдельный NGINX‑виртуальный хост.

2. **Сборка на месте (если Node.js есть и разрешено)**:

   ```bash
   cd ~/projects/PlanOptimization/frontend
   # Используем скопированные node_modules:
   cp -r ../../offline/frontend/node_modules ./  # если нужно
   npm run build  # или другая команда сборки
   cd ..
   ```

   После сборки фронтенда снова нужно настроить раздачу статических файлов (например, через NGINX или `whitenoise`).

> Конкретная схема интеграции Django + фронтенда будет зависеть от финальной фронтовой структуры (SPA, SSR, отдельный домен). Эта инструкция предполагает, что фронтенд собирается в статический бандл и отдаётся из одного каталога.

### B9. Запуск Django‑сервера и Celery

1. **Django‑сервер** (для тестового запуска/демонстрации):

   ```bash
   cd ~/projects/PlanOptimization
   source .venv/bin/activate
   python manage.py runserver 0.0.0.0:8000
   ```

   - Панель администратора будет доступна по `http://<ip_машины>:8000/admin/`.

2. **Celery‑воркер** (фоновая обработка тяжёлых задач):

   ```bash
   cd ~/projects/PlanOptimization
   source .venv/bin/activate
   celery -A production_planner worker -l info
   ```

3. При необходимости в пром‑режиме рекомендуется:

   - использовать `gunicorn`/`uWSGI` + NGINX;
   - оформить службы systemd для:
     - Django‑приложения;
     - Celery‑воркера;
     - Redis и PostgreSQL (обычно уже оформлены).

---

## Краткий чек‑лист для запуска на предприятии (без интернета)

1. Распаковать `PlanOptimization_offline.tar.gz` в `~/projects/PlanOptimization`.
2. Установить системные пакеты: Python, PostgreSQL, Redis, (опционально) Node.js.
3. Создать пользователя/БД PostgreSQL (`planner` / `production_planner` или другие, согласованные в `.env`).
4. Активировать виртуальное окружение и установить зависимости из `offline/python-wheels`.
5. Создать `.env` из `.env.example` и проверить параметры подключения к БД/Redis.
6. Выполнить `python manage.py migrate` и `python manage.py createsuperuser`.
7. Подготовить фронтенд (использовать готовый `dist` или собрать на месте).
8. Запустить:
   - `python manage.py runserver 0.0.0.0:8000`
   - `celery -A production_planner worker -l info`

После выполнения этих шагов проект будет работоспособен на Astra Linux даже без доступа к интернету.

