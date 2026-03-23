FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/frontend

COPY . /srv/frontend

EXPOSE 8080

CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0", "--directory", "/srv/frontend"]
