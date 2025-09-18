# 🌎 NovaCommerce Analytics

NovaCommerce Analytics — это аналитический центр для крупнейшего онлайн-маркетплейса Бразилии.  
Наша цель — помочь бизнесу понять клиентов, продавцов и товары с помощью данных:  
кто покупает, что покупают, как доставляют и чем клиенты довольны.

---

## 📊 О проекте

Компания **NovaCommerce** специализируется на электронной коммерции и доставке товаров по всей стране.  
Мы анализируем более **100 000 заказов**:  
- динамику продаж,  
- топовые категории товаров,  
- методы оплаты и скорость доставки,  
- рейтинги и отзывы покупателей.  

Эта аналитика помогает улучшать клиентский опыт и повышать эффективность работы продавцов.

---

## Основная аналитика (скриншот)



## 🚀 Как запустить проект

1. **Поднять базу данных PostgreSQL**  
   ```bash
   docker compose up -d
- Это создаст контейнер с PostgreSQL и применит schema.sql.

Загрузить данные
Скопируй CSV из датасета Olist в папку ./data, затем:

```bash
python load_olist.py --host localhost --port 5433 --db e-commercedb --user postgres --password secret --data-dir ./data --truncate
```
Выполнить аналитические SQL-запросы

```bash
psql -h localhost -p 5433 -U postgres -d e-commercedb -f queries.sql
Запустить Python-скрипт (для экспорта результатов в CSV):
```

```bash
python main.py
```
Открыть Superset (опционально)
Подключи базу и открой готовый дашборд для визуализации.

## 🛠️ Используемые инструменты
- PostgreSQL 16 — основная СУБД для хранения и анализа данных

- Docker Compose — инфраструктура

- Python 3.11+ — загрузка данных и скрипты аналитики

- pandas, SQLAlchemy, psycopg2 — работа с БД и обработка данных

- Apache Superset — BI-дашборды

- DBeaver — SQL IDE и генерация ER-диаграммы

- dbdiagram.io — визуализация структуры БД

📂 Структура репозитория
graphql
```bash
.
├── docker-compose.yml      # окружение PostgreSQL
├── schema.sql              # схема базы данных
├── load_olist.py           # загрузка CSV в PostgreSQL
├── queries.sql             # 10 аналитических SQL-запросов
├── main.py                 # Python-скрипт для запуска запросов
├── docs/
│   ├── er.png              # ER-диаграмма
│   └── dashboard.png       # скриншот дашборда
└── data/                   # CSV-файлы Olist (локально, не в GitHub)
```



Как запускать после загрузки

Сначала загрузка CSV:

python load_olist.py --host 127.0.0.1 --port 5433 --db e-commercedb --user postgres --password secret --data-dir .\data --truncate


Потом применить post_load.sql:

type .\post_load.sql | docker exec -i olist_pg psql -U postgres -d e-commercedb