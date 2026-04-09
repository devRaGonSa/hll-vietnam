FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HLL_BACKEND_HOST=0.0.0.0 \
    HLL_BACKEND_PORT=8000 \
    HLL_BACKEND_STORAGE_PATH=/app/data/hll_vietnam_dev.sqlite3 \
    HLL_BACKEND_POSTGRES_HOST=postgres \
    HLL_BACKEND_POSTGRES_PORT=5432 \
    HLL_BACKEND_POSTGRES_DB=hll_vietnam \
    HLL_BACKEND_POSTGRES_USER=hll_vietnam \
    HLL_BACKEND_POSTGRES_PASSWORD=hll_vietnam_dev \
    HLL_BACKEND_POSTGRES_SSLMODE=disable \
    HLL_BACKEND_POSTGRES_CONNECT_TIMEOUT_SECONDS=5

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY app ./app
COPY db ./db
COPY scripts ./scripts

RUN mkdir -p /app/data/snapshots

EXPOSE 8000

CMD ["python", "-m", "app.main"]
