# loader/Dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir psycopg2-binary
WORKDIR /app
