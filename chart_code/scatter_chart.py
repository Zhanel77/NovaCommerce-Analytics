import os, pandas as pd, matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
OUT_DIR = "charts"; os.makedirs(OUT_DIR, exist_ok=True)

sql = """
SELECT oi.price, oi.freight_value
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_name_translation t
       ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered'
  AND oi.price > 0
  AND oi.freight_value >= 0
LIMIT 5000
"""
df = pd.read_sql_query(text(sql), engine)

fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df["price"], df["freight_value"], alpha=0.5, s=12)
ax.set_title("Item price vs freight cost")
ax.set_xlabel("Item price"); ax.set_ylabel("Freight value")
fig.savefig(f"{OUT_DIR}/scatter_chart.png", dpi=200, bbox_inches="tight")
print(f"Scatter chart saved, {len(df)} rows")
