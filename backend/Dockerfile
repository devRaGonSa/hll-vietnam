FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HLL_BACKEND_HOST=0.0.0.0 \
    HLL_BACKEND_PORT=8000 \
    HLL_BACKEND_STORAGE_PATH=/app/data/hll_vietnam_dev.sqlite3

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY app ./app

RUN mkdir -p /app/data/snapshots

EXPOSE 8000

CMD ["python", "-m", "app.main"]
