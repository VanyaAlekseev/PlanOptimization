## PostgreSQL: “код базы” и как подключить приложение к БД

В этом проекте **код базы данных** состоит из двух частей:

- **SQL для инфраструктуры БД**: создание расширений/пользователей/БД (опционально).
- **Схема таблиц приложения**: генерируется и поддерживается **Django миграциями** (`planner/migrations/...`).

То есть таблицы (Project/Product/Component/…) создаются не вручную SQL‑скриптом, а командой:

```bash
python manage.py migrate
```

---

## 1) SQL-файлы для PostgreSQL (инфраструктура)

### В Docker

Файл `db/init/001_extensions.sql` подключен в `docker-compose.yml` как:

- `./db/init:/docker-entrypoint-initdb.d:ro`

PostgreSQL контейнер автоматически выполнит эти SQL‑файлы **только при первом создании volume** (когда база пустая).

Сейчас там включается расширение:

- `pgcrypto` (часто полезно для криптографических функций/UUID).

TimescaleDB пока оставлен закомментированным (его подключим позже, когда выберем образ/пакеты).

---

## 2) Как сделать, чтобы приложение читало/писало в PostgreSQL

### Ключевой факт

Django читает/пишет данные в PostgreSQL автоматически через ORM, если:

- в `production_planner/settings.py` выставлен `DATABASES['default']` на PostgreSQL;
- запущена сама БД;
- применены миграции (`migrate`).

### Переменные окружения

Подключение управляется переменными:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `POSTGRES_HOST`, `POSTGRES_PORT`

Пример для Docker (они уже проставлены в `docker-compose.yml`):

- `POSTGRES_HOST=db`
- `POSTGRES_PORT=5432`

Пример для локальной установки:

- `POSTGRES_HOST=127.0.0.1`
- `POSTGRES_PORT=5432`

### Команды, которые “включают” БД для Django

1) Создать/обновить миграции (когда меняются модели):

```bash
python manage.py makemigrations
```

2) Применить миграции (создать/обновить таблицы):

```bash
python manage.py migrate
```

После `migrate` Django начинает:

- **читать**: `Model.objects.filter(...)`
- **писать**: `Model.objects.create(...)`, `obj.save()`, репозитории/сервисы

Никакого дополнительного “кода доступа к БД” писать не нужно — он уже в ORM Django.

---

## 3) Быстрый сценарий: запустить всё через Docker

1) В корне проекта:

```bash
docker compose up --build
```

2) Открыть:

- Backend (Django): `http://localhost:8000/`
- Admin: `http://localhost:8000/admin/`
- Frontend: `http://localhost:8080/`

### Где происходит migrate/collectstatic

В `docker/entrypoint.sh` автоматически выполняются:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

после чего запускается `gunicorn`.

---

## 4) Если нужно “ручное” SQL для создания пользователя/БД (вне Docker)

Если вы ставите PostgreSQL как сервис в ОС, то обычно делаете один раз:

```sql
CREATE USER planner WITH ENCRYPTED PASSWORD 'planner';
CREATE DATABASE production_planner OWNER planner;
GRANT ALL PRIVILEGES ON DATABASE production_planner TO planner;
```

После этого на стороне Django достаточно выставить `POSTGRES_*` и выполнить `python manage.py migrate`.


