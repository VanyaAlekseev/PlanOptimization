FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    fonts-dejavu-core \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Normalize line endings (helps if files were created/edited on Windows).
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh || true

EXPOSE 8000

CMD ["gunicorn", "production_planner.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

