import os, pandas as pd, matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
OUT_DIR = "charts"; os.makedirs(OUT_DIR, exist_ok=True)

# динамика месячной выручки магазина
sql = """
SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
       SUM(oi.price + oi.freight_value) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
WHERE o.order_status IN ('delivered','shipped','invoiced')
GROUP BY month
ORDER BY month
"""
df = pd.read_sql_query(text(sql), engine)
df["month"] = pd.to_datetime(df["month"])

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(df["month"], df["revenue"], marker="o")
ax.set_title("Monthly revenue")
ax.set_xlabel("Month"); ax.set_ylabel("Revenue")
fig.savefig(f"{OUT_DIR}/line_chart.png", dpi=200, bbox_inches="tight")
print(f"Line chart saved, {len(df)} rows")
