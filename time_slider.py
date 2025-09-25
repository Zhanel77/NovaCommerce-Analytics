# time_slider.py
import os
import pandas as pd
import plotly.express as px
import plotly.io as pio
from sqlalchemy import create_engine, text
from pathlib import Path
import subprocess

# 1) коннект к БД
DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
eng = create_engine(DB_URL)

# 2) запрос: выручка по месяцам и штатам (для слайдера по month)
sql = """
SELECT DATE_TRUNC('month', o.order_purchase_timestamp)::date AS month,
       c.customer_state,
       SUM(oi.price) AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers c     ON o.customer_id = c.customer_id
GROUP BY month, c.customer_state
ORDER BY month, c.customer_state;
"""

df = pd.read_sql(text(sql), eng)
df["month"] = df["month"].astype(str)  # анимация ожидает строку

# 3) рендерер: просим открывать в системном браузере
pio.renderers.default = "browser"

fig = px.bar(
    df, x="customer_state", y="revenue",
    animation_frame="month",
    title="Выручка по штатам (анимация по месяцам)",
    labels={"customer_state": "State", "revenue": "Revenue", "month": "Month"}
)
fig.update_layout(bargap=0.2)

# 4) путь сохранения
Path("charts").mkdir(exist_ok=True)
html_path = Path("charts/time_slider.html").resolve()

# 5) сохраняем HTML и пытаемся открыть
fig.write_html(str(html_path), include_plotlyjs="cdn")
print(f"✅ Saved interactive chart → {html_path}")

# в WSL удобно открыть через explorer.exe (Windows)
try:
    win_path = subprocess.check_output(["wslpath", "-w", str(html_path)], text=True).strip()
    subprocess.Popen(["explorer.exe", win_path])
    print("🧭 Opening in Windows browser via explorer.exe …")
except Exception as e:
    # если не получилось — просто подсказываем, как открыть вручную
    print("ℹ️  If it didn't open automatically, open this file in your browser:")
    print(html_path)
