# main.py
import pandas as pd
from sqlalchemy import create_engine

DB_URL = "postgresql+psycopg2://postgres:secret@localhost:5433/e-commercedb"

sqls = {
 "top_categories_revenue": """
SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
       ROUND(SUM(oi.price),2) AS revenue
FROM olist.order_items oi
JOIN olist.products p  ON p.product_id = oi.product_id
LEFT JOIN olist.product_category_name_translation t
       ON t.product_category_name = p.product_category_name
GROUP BY category
ORDER BY revenue DESC
LIMIT 20;""",
 "payment_types_share": """
SELECT payment_type,
       COUNT(*) AS cnt,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),2) AS pct
FROM olist.order_payments
GROUP BY payment_type
ORDER BY cnt DESC;""",
 "delivery_speed_by_state": """
SELECT c.customer_state,
       ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp))/86400.0),2) AS avg_days
FROM olist.orders o
JOIN olist.customers c ON c.customer_id = o.customer_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_days;"""
}

def run():
    eng = create_engine(DB_URL)
    for name, q in sqls.items():
        df = pd.read_sql(q, eng)
        print(f"\n== {name} ==\n", df.head(10))
        df.to_csv(f"{name}.csv", index=False)
    print("\nDone.")

if __name__ == "__main__":
    run()
