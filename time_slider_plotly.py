# time_slider_plotly_db_frames.py
import os
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres")
engine = create_engine(DB_URL)
N = int(os.getenv("TOP_N", "8"))

SQL = text("""
WITH base AS (
  SELECT
    date_trunc('month', o.order_purchase_timestamp)::date AS month,
    LOWER(TRIM(COALESCE(t.product_category_name_english, p.product_category_name, '(unknown)'))) AS cat,
    (oi.price + oi.freight_value) AS revenue
  FROM public.orders o
  JOIN public.order_items oi ON oi.order_id = o.order_id
  JOIN public.products p ON p.product_id = oi.product_id
  LEFT JOIN public.product_category_name_translation t
         ON t.product_category_name = p.product_category_name
  WHERE o.order_status IN ('delivered','shipped','invoiced')
),
topcats AS (
  SELECT cat
  FROM base
  GROUP BY cat
  ORDER BY SUM(revenue) DESC
  LIMIT 8
),
monthly AS (
  SELECT month, cat, SUM(revenue) AS revenue
  FROM base
  WHERE cat IN (SELECT cat FROM topcats)
  GROUP BY month, cat
),
-- все месяцы и категории, чтобы построить «растущие» кадры
months AS (SELECT DISTINCT month FROM monthly),
cats   AS (SELECT DISTINCT cat   FROM monthly),
grid AS (
  SELECT fm.month AS frame_month, m.month, c.cat
  FROM months fm
  JOIN months m ON m.month <= fm.month
  CROSS JOIN cats c
),
filled AS (
  SELECT g.frame_month, g.month, g.cat, COALESCE(m.revenue, 0) AS revenue
  FROM grid g
  LEFT JOIN monthly m
    ON m.month = g.month AND m.cat = g.cat
),
cum AS (
  SELECT
    frame_month,
    month,
    cat,
    SUM(revenue) OVER (PARTITION BY frame_month, cat ORDER BY month) AS cum_revenue
  FROM filled
)
SELECT frame_month, month, cat, cum_revenue
FROM cum
ORDER BY frame_month, cat, month;
""")

df = pd.read_sql_query(SQL, engine, params={"N": N})
df["month"] = pd.to_datetime(df["month"])
df["frame_month"] = pd.to_datetime(df["frame_month"])
df["frame_str"] = df["frame_month"].dt.strftime("%Y-%m")

fig = px.line(
    df,
    x="month", y="cum_revenue",
    color="cat",
    animation_frame="frame_str",
    line_group="cat",
    title=f"Monthly Revenue (CUMULATIVE) by Top {df['cat'].nunique()} Categories",
    labels={"month":"Date", "cum_revenue":"Cumulative revenue", "cat":"Category", "frame_str":"Month"}
)

fig.update_layout(
    width=1000, height=600, title_font_size=18,
    xaxis=dict(type="date"),
    yaxis=dict(rangemode="tozero"),
    legend_title_text="Category",
    margin=dict(l=40, r=20, t=60, b=40),
    updatemenus=[{
        "type":"buttons","showactive":False,
        "buttons":[
            {"label":"► Play","method":"animate",
             "args":[None,{"fromcurrent":True,"frame":{"duration":500,"redraw":True},"transition":{"duration":0}}]},
            {"label":"❚❚ Pause","method":"animate",
             "args":[[None],{"mode":"immediate","frame":{"duration":0},"transition":{"duration":0}}]}
        ]
    }],
    sliders=[{"currentvalue":{"prefix":"Month: "}}]
)

os.makedirs("charts", exist_ok=True)
fig.write_html("charts/line_timeslider_categories.html", include_plotlyjs="cdn")
print("Saved: charts/line_timeslider_categories.html")
