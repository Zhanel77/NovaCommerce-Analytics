import os, pandas as pd, matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
OUT_DIR = "charts"; os.makedirs(OUT_DIR, exist_ok=True)

# список цен всех доставленных товаров.
sql = """
SELECT oi.price
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_name_translation t
       ON t.product_category_name = p.product_category_name
WHERE o.order_status = 'delivered' AND oi.price > 0 AND oi.price <= 1000 
"""
df = pd.read_sql_query(text(sql), engine)

fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(df["price"], bins=50, alpha=0.8)
ax.set_title("Distribution of item prices (delivered orders)")
ax.set_xlabel("Item price"); ax.set_ylabel("Frequency"); ax.set_xlim(0, 1000)
fig.savefig(f"{OUT_DIR}/hist_chart.png", dpi=200, bbox_inches="tight")
print(f"Histogram saved, {len(df)} rows")
