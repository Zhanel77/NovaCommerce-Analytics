FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir prometheus_client psycopg2-binary
COPY custom_exporter.py .
EXPOSE 9101
CMD ["python", "custom_exporter.py"]
