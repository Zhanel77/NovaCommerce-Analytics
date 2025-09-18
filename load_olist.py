#!/usr/bin/env python3
import argparse, os, sys, psycopg2

TABLE_FILES = {
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

COPY_SQL = {
    "customers": """
        COPY olist.customers
        (customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "sellers": """
        COPY olist.sellers
        (seller_id, seller_zip_code_prefix, seller_city, seller_state)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "geolocation": """
        COPY olist.geolocation
        (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "products": """
        COPY olist.products
        (product_id, product_category_name, product_name_lenght, product_description_lenght,
         product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "product_category_name_translation": """
        COPY olist.product_category_name_translation
        (product_category_name, product_category_name_english)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "orders": """
        COPY olist.orders
        (order_id, customer_id, order_status, order_purchase_timestamp, order_approved_at,
         order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "order_items": """
        COPY olist.order_items
        (order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "order_payments": """
        COPY olist.order_payments
        (order_id, payment_sequential, payment_type, payment_installments, payment_value)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
    "order_reviews": """
        COPY olist.order_reviews
        (review_id, order_id, review_score, review_comment_title, review_comment_message,
         review_creation_date, review_answer_timestamp)
        FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
    """,
}

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", default="5433")
    p.add_argument("--db",   default="e-commercedb")
    p.add_argument("--user", default="postgres")
    p.add_argument("--password", default="secret")
    p.add_argument("--data-dir", default="./data")
    p.add_argument("--truncate", action="store_true")
    return p.parse_args()

def connect(a):
    return psycopg2.connect(host=a.host, port=a.port, dbname=a.db, user=a.user, password=a.password)

def count(cur, t):
    cur.execute(f"SELECT COUNT(*) FROM olist.{t}"); return cur.fetchone()[0]

def main():
    a = parse_args()
    if not os.path.isdir(a.data_dir):
        print(f"[ERR] data dir not found: {a.data_dir}", file=sys.stderr); sys.exit(1)
    conn = connect(a); conn.autocommit = False; cur = conn.cursor()

    if a.truncate:
        for t in ["order_reviews","order_payments","order_items","orders","products",
                  "product_category_name_translation","geolocation","sellers","customers"]:
            cur.execute(f"TRUNCATE olist.{t} CASCADE")
        conn.commit()

    for t, fn in TABLE_FILES.items():
        path = os.path.join(a.data_dir, fn)
        if not os.path.exists(path):
            print(f"[SKIP] {t}: no file {path}"); continue
        print(f"[LOAD] {t} <- {fn}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                cur.copy_expert(COPY_SQL[t], f)
            conn.commit()
            print(f"[OK] {t}: {count(cur, t)} rows")
        except Exception as e:
            conn.rollback()
            print(f"[ERR] {t}: {e}")
            raise

    cur.close(); conn.close(); print("\n[DONE]")

if __name__ == "__main__":
    main()
