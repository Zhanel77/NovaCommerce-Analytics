import os
import csv
import psycopg2

# === соединение с БД ===
conn = psycopg2.connect(
    host="localhost", port="5433",
    dbname="postgres",  # если твои таблицы в другой БД, поменяй здесь
    user="postgres", password="postgres"
)

# куда сохранять CSV
EXPORTS_DIR = "exports"
os.makedirs(EXPORTS_DIR, exist_ok=True)

# === запросы ===
sqls = {
    # 1. Помесячные заказы и выручка
    "monthly_orders_revenue": """
        SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
               COUNT(*) AS total_orders,
               SUM(oi.price + oi.freight_value) AS total_revenue
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        GROUP BY month
        ORDER BY month;
    """,

    # 2. Среднее время доставки заказа
    "avg_delivery_time": """
        SELECT AVG(order_delivered_customer_date - order_purchase_timestamp) AS avg_delivery_time
        FROM orders
        WHERE order_delivered_customer_date IS NOT NULL;
    """,

    # 3. Топ-10 городов по числу заказов
    "top_cities_orders": """
        SELECT c.customer_city, COUNT(o.order_id) AS order_count
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        GROUP BY c.customer_city
        ORDER BY order_count DESC
        LIMIT 10;
    """,

    # 4. Категории товаров с наибольшей выручкой
    "top_categories_revenue": """
        SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
               SUM(oi.price) AS revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN product_category_name_translation t
               ON t.product_category_name = p.product_category_name
        GROUP BY category
        ORDER BY revenue DESC
        LIMIT 10;
    """,

    # 5. Средняя оценка покупателей по категориям
    "avg_review_score_by_category": """
        SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
               ROUND(AVG(r.review_score), 2) AS avg_score,
               COUNT(r.review_id) AS n_reviews
        FROM order_reviews r
        JOIN orders o ON r.order_id = o.order_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN product_category_name_translation t
               ON t.product_category_name = p.product_category_name
        GROUP BY category
        HAVING COUNT(r.review_id) > 50
        ORDER BY avg_score DESC
        LIMIT 10;
    """,

    # 6. Способы оплаты и их доля
    "payment_types_share": """
        SELECT payment_type,
               ROUND(SUM(payment_value), 2) AS total_value,
               ROUND(100.0 * SUM(payment_value) /
                     SUM(SUM(payment_value)) OVER(), 2) AS pct_share
        FROM order_payments
        GROUP BY payment_type
        ORDER BY total_value DESC;
    """,

    # 7. Топ-10 продавцов по выручке
    "top_sellers_revenue": """
        SELECT s.seller_id,
               SUM(oi.price + oi.freight_value) AS revenue
        FROM order_items oi
        JOIN sellers s ON oi.seller_id = s.seller_id
        GROUP BY s.seller_id
        ORDER BY revenue DESC
        LIMIT 10;
    """,

    # 8. Количество заказов по дням недели
    "orders_by_weekday": """
        SELECT TO_CHAR(order_purchase_timestamp, 'Day') AS weekday,
               COUNT(*) AS total_orders
        FROM orders
        GROUP BY weekday
        ORDER BY total_orders DESC;
    """,

    # 9. Доставка вовремя vs с опозданием
    "on_time_vs_late": """
        SELECT
          SUM(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) AS on_time,
          SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) AS late
        FROM orders
        WHERE order_delivered_customer_date IS NOT NULL;
    """,

    # 10. Средний чек по штатам
    "avg_order_value_by_state": """
        WITH order_totals AS (
            SELECT oi.order_id, SUM(oi.price + oi.freight_value) AS order_sum
            FROM order_items oi
            GROUP BY oi.order_id
        )
        SELECT c.customer_state,
               ROUND(AVG(ot.order_sum), 2) AS avg_order_value
        FROM orders o
        JOIN order_totals ot ON ot.order_id = o.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        GROUP BY c.customer_state
        ORDER BY avg_order_value DESC;
    """,
}

def save_csv(name: str, rows: list, columns: list):
    """Сохранить результат в exports/<name>.csv с заголовками колонок."""
    path = os.path.join(EXPORTS_DIR, f"{name}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for r in rows:
            # приводим значения к строкам где нужно (даты/Decimal и т.п.)
            writer.writerow([str(v) if v is not None else "" for v in r])
    return path

def run():
    with conn, conn.cursor() as cur:
        for i, (name, q) in enumerate(sqls.items(), 1):
            print(f"\n=== Query {i}: {name} ===")
            cur.execute(q)
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]

            # превью в консоль
            for row in rows[:10]:
                print(row)
            print(f"... total rows: {len(rows)}")

            # сохранение в CSV
            out_csv = save_csv(name, rows, cols)
            print(f"[OK] saved → {out_csv}")

if __name__ == "__main__":
    run()
