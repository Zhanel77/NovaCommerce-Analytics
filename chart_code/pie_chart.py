import os
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
OUT_DIR = "charts"; os.makedirs(OUT_DIR, exist_ok=True)

sql = """
SELECT COALESCE(t.product_category_name_english, p.product_category_name, '(unknown)') AS category,
       SUM(oi.price) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN product_category_name_translation t
       ON t.product_category_name = p.product_category_name
WHERE o.order_status IN ('delivered','shipped','invoiced')
GROUP BY category
HAVING SUM(oi.price) > 0
ORDER BY revenue DESC
LIMIT 12
"""
df = pd.read_sql_query(text(sql), engine)

fig, ax = plt.subplots(figsize=(8, 8))
ax.pie(df["revenue"], labels=df["category"], autopct="%1.1f%%", startangle=90)
ax.set_title("Revenue share by product category")
fig.savefig(f"{OUT_DIR}/pie_chart1.png", dpi=200, bbox_inches="tight")
print(f"Pie chart saved, {len(df)} rows")
