# Базовый образ с Python
FROM python:3.11-slim

# Установим зависимости системы (чтобы psycopg2 нормально собрался)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Скопируем файлы зависимостей
COPY requirements.txt .

# Установим Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируем код проекта внутрь контейнера
COPY . .

# По умолчанию запускать main.py
CMD ["python", "main.py"]
