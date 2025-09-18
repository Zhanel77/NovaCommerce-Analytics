import argparse
import os
import sys
import psycopg2
from psycopg2.extras import execute_values

TABLE_FILES = {
    # порядок загрузки с учётом FK
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",  
    "products": "olist_products_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
}

SCHEMA = "olist"

COPY_SQL = {
    "customers": f"""
        COPY {SCHEMA}.customers
        (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "sellers": f"""
        COPY {SCHEMA}.sellers
        (seller_id, seller_zip_code_prefix, seller_city, seller_state)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "geolocation": f"""
        COPY {SCHEMA}.geolocation
        (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "products": f"""
        COPY {SCHEMA}.products
        (product_id, product_category_name, product_name_lenght, product_description_lenght,
         product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "product_category_name_translation": f"""
        COPY {SCHEMA}.product_category_name_translation
        (product_category_name, product_category_name_english)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "orders": f"""
        COPY {SCHEMA}.orders
        (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at,
         order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "order_items": f"""
        COPY {SCHEMA}.order_items
        (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "order_payments": f"""
        COPY {SCHEMA}.order_payments
        (order_id, payment_sequential, payment_type, payment_installments, payment_value)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "order_reviews": f"""
        COPY {SCHEMA}.order_reviews
        (review_id, order_id, review_score, review_comment_title, review_comment_message,
         review_creation_date, review_answer_timestamp)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
}

TRUNCATE_ORDER = [
    # чтобы перезаливка не упиралась в FK
    "order_reviews",
    "order_payments",
    "order_items",
    "orders",
    "products",
    "product_category_name_translation",
    "geolocation",
    "sellers",
    "customers",
]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    p.add_argument("--port", default=os.getenv("PGPORT", "5432"))
    p.add_argument("--db",   default=os.getenv("PGDATABASE", "e-commercedb"))
    p.add_argument("--user", default=os.getenv("PGUSER", "postgres"))
    p.add_argument("--password", default=os.getenv("PGPASSWORD", "secret"))
    p.add_argument("--data-dir", default="./data")
    p.add_argument("--truncate", action="store_true", help="Очистить таблицы перед загрузкой")
    return p.parse_args()

def connect(args):
    conn = psycopg2.connect(
        host=args.host, port=args.port, dbname=args.db,
        user=args.user, password=args.password
    )
    conn.autocommit = False
    return conn

def table_count(cur, table):
    cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.{table}")
    return cur.fetchone()[0]

def main():
    args = parse_args()
    if not os.path.isdir(args.data_dir):
        print(f"[ERR] data-dir not found: {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    conn = connect(args)
    cur = conn.cursor()

    # проверка схемы
    cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name=%s", (SCHEMA,))
    if cur.fetchone() is None:
        print(f"[WARN] Schema '{SCHEMA}' not found. Убедись, что выполнила schema.sql до загрузки.")
        # не выходим; вдруг таблицы в public — но по нашему проекту лучше применить schema.sql заранее

    # опционально очистим (для повторных прогонов)
    if args.truncate:
        print("[INFO] TRUNCATE tables (cascade in correct order)…")
        for t in TRUNCATE_ORDER:
            cur.execute(f"TRUNCATE TABLE {SCHEMA}.{t} CASCADE")
        conn.commit()

    # По очереди загружаем таблицы
    for table, filename in TABLE_FILES.items():
        path = os.path.join(args.data_dir, filename)
        if not os.path.exists(path):
            print(f"[SKIP] {table}: файл не найден {path}")
            continue

        print(f"[LOAD] {table} <- {filename}")
        with open(path, "r", encoding="utf-8") as f:
            cur.copy_expert(COPY_SQL[table], f)
        conn.commit()

        cnt = table_count(cur, table)
        print(f"[OK] {table}: {cnt} rows")

    # Мини-проверки для отчёта (из п.4 задания)
    print("\n[CHECK] Базовые проверки")
    cur.execute(f"SELECT * FROM {SCHEMA}.orders LIMIT 10")
    ten = cur.fetchall()
    print(f"orders LIMIT 10 -> {len(ten)} строк")

    cur.execute(f"""
        SELECT product_id, COUNT(*) AS n_items
        FROM {SCHEMA}.order_items
        GROUP BY product_id
        ORDER BY n_items DESC
        LIMIT 5
    """)
    print("Top-5 product_id by items:", cur.fetchall())

    cur.close()
    conn.commit()
    conn.close()
    print("\n[DONE] Загрузка завершена.")

if __name__ == "__main__":
    main()