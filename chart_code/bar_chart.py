import os, pandas as pd, matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
OUT_DIR = "charts"; os.makedirs(OUT_DIR, exist_ok=True)

# ТОП-10 городов по числу уникальных заказов
sql = """
SELECT c.customer_city AS city, COUNT(DISTINCT o.order_id) AS orders_count
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('delivered','shipped','invoiced')
GROUP BY city
ORDER BY orders_count DESC
LIMIT 10
"""
df = pd.read_sql_query(text(sql), engine)

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(df["city"], df["orders_count"])
ax.set_title("Top 10 cities by number of orders")
ax.set_xlabel("City"); ax.set_ylabel("Orders")
plt.xticks(rotation=30, ha="right")
fig.savefig(f"{OUT_DIR}/bar_chart.png", dpi=200, bbox_inches="tight")
print(f"Bar chart saved, {len(df)} rows")
