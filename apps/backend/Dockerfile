# Backend API image for the Aviation Intelligence Platform.
# Build from repo root: docker compose build backend
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UPLOAD_DIR=/data/uploads \
    LLM_CACHE_PATH=/data/cache/llm_cache.json \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000

COPY apps/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/backend/app ./app

RUN mkdir -p /data/uploads /data/cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
