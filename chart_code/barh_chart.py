import os, pandas as pd, matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
OUT_DIR = "charts"; os.makedirs(OUT_DIR, exist_ok=True)

# считает среднюю цену товаров по категориям и выводит топ-12 самых дорогих категорий
sql = """
SELECT COALESCE(t.product_category_name_english, p.product_category_name, '(unknown)') AS category,
       AVG(oi.price) AS avg_price
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_name_translation t
       ON t.product_category_name = p.product_category_name
WHERE o.order_status IN ('delivered','shipped','invoiced')
GROUP BY category
HAVING COUNT(*) >= 50
ORDER BY avg_price DESC
LIMIT 12
"""
df = pd.read_sql_query(text(sql), engine).sort_values("avg_price")

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(df["category"], df["avg_price"])
ax.set_title("Average item price by category")
ax.set_xlabel("Average price")
fig.savefig(f"{OUT_DIR}/barh_chart.png", dpi=200, bbox_inches="tight")
print(f"Barh chart saved, {len(df)} rows")
