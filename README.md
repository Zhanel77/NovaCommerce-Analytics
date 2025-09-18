# 🌎 NovaCommerce Analytics — E-commerce Insights for Brazil

NovaCommerce — маркетплейс, который объединяет тысячи продавцов и миллионов покупателей по всей Бразилии. 

Мы помогаем мерчантам выходить к новой аудитории, а покупателям — получать широкий выбор, быструю доставку и удобные способы оплаты.

Роль аналитика: я работаю аналитиком в команде Revenue & Operations. Мои задачи:

- собирать и поддерживать витрины данных (PostgreSQL) под продуктовую и операционную аналитику;

- строить отчёты и дашборды (Apache Superset) по продажам, конверсиям, логистике и оплатам;

- находить точки роста: топ-категории, эффективность продавцов, узкие места доставки, паттерны оплат;

- отвечать на ad-hoc вопросы бизнеса SQL-запросами и Python-скриптами.

В качестве учебного корпоративного DWH используется открытый датасет Brazilian E-Commerce (Olist). На нём я показываю полный цикл: от схемы БД и загрузки до аналитики и дашбордов.


## Архитектура и стек

- База данных: PostgreSQL 16 (контейнер Docker, схема olist)

- Витрины/SQL: schema.sql, queries.sql

- Загрузка данных: load_olist.py (COPY из CSV), post_load.sql (добавляет недостающие категории и валидирует FK)

- BI/дашборды: Apache Superset (по желанию; скриншот в docs/dashboard.png)

- Аналитические выгрузки: main.py (Python + pandas/SQLAlchemy)

## Структура репозитория

```bash
NovaCommerce-Analytics/
├─ docker-compose.yml               # Postgres (и, при желании, Superset/pgAdmin)
├─ schema.sql                       # схема БД с PK/FK
├─ post_load.sql                    # дополнение словаря категорий + валидация FK
├─ load_olist.py                    # загрузка CSV → таблицы (COPY)
├─ queries.sql                      # 10 тем аналитики (SQL)
├─ main.py                          # Python: выполняет SQL и сохраняет CSV
├─ data/                            # CSV-файлы датасета Olist
│   ├─ olist_customers_dataset.csv
│   ├─ olist_geolocation_dataset.csv
│   ├─ olist_order_items_dataset.csv
│   ├─ olist_order_payments_dataset.csv
│   ├─ olist_order_reviews_dataset.csv
│   ├─ olist_orders_dataset.csv
│   ├─ olist_products_dataset.csv
│   ├─ olist_sellers_dataset.csv
│   └─ product_category_name_translation.csv
└─ docs/
    ├─ er.png                       # ER-диаграмма (DBeaver/dbdiagram)
    └─ dashboard.png                # скрин дашборда (Superset)
```

## Быстрый запуск (Windows/PowerShell)

***Требуется установленный Docker Desktop (WSL2) и Python 3.11+. Команды ниже – для PowerShell.***

### 1) Поднять PostgreSQL в Docker
```bash
docker compose up -d
docker ps       
```
***schema.sql применится автоматически при первом старте (чистый volume).***

### 2) Загрузить данные

```bash
pip install psycopg2-binary

python .\load_olist.py --host 127.0.0.1 --port 5433 --db e-commercedb --user postgres --password secret --data-dir .\data --truncate
```

****Ожидаемые логи: [OK] customers: 99441 rows, …, [OK] order_items: 112650 rows и т.д.****

### 3) Постобработка и валидacja FK

***Иногда в CSV встречаются категории, которых нет в переводе. Скрипт post_load.sql добавит недостающие категории и валидирует внешний ключ:***

```bash
type .\post_load.sql | docker exec -i olist_pg psql -U postgres -d e-commercedb
```

### 4) Проверки в pgAdmin/psql

pgAdmin:

Подключение: 
- Host 127.0.0.1
- Port 5433 
- DB e-commercedb 
- User postgres 
- Pass secret

***Найди Schemas → olist → Tables, открой данные через View/Edit Data.***

psql через docker:
```bash
docker exec -it olist_pg psql -U postgres -d e-commercedb
\dt olist.*
SELECT COUNT(*) FROM olist.orders;
\q
```

### 5) Выполнить базовые SQL и аналитики

Проверки по заданию:

```bash
-- LIMIT 10
SELECT * FROM olist.orders LIMIT 10;

-- WHERE + ORDER BY
SELECT order_id, order_status, order_purchase_timestamp
FROM olist.orders
WHERE order_status IN ('delivered','shipped')
ORDER BY order_purchase_timestamp DESC
LIMIT 10;

-- GROUP BY + COUNT/AVG/MIN/MAX
SELECT payment_type,
       COUNT(*) AS cnt,
       ROUND(AVG(payment_value),2) AS avg_payment,
       ROUND(MIN(payment_value),2) AS min_payment,
       ROUND(MAX(payment_value),2) AS max_payment
FROM olist.order_payments
GROUP BY payment_type
ORDER BY cnt DESC;

-- JOIN (orders + customers + order_items)
SELECT o.order_id, c.customer_state, ROUND(SUM(oi.price),2) AS order_sum
FROM olist.orders o
JOIN olist.customers c ON c.customer_id = o.customer_id
JOIN olist.order_items oi ON oi.order_id = o.order_id
GROUP BY o.order_id, c.customer_state
ORDER BY order_sum DESC
LIMIT 10;
```
### 6) Python-скрипт для выгрузок
```bash
pip install pandas SQLAlchemy psycopg2-binary
python .\main.py
```

***Скрипт выполнит 2–3 аналитических запроса, выведет первые строки в консоль и сохранит CSV рядом (top_categories_revenue.csv, payment_types_share.csv, …).***

---

***Student - Kuandyk Zhanel.***

***Group - IT-2303.***