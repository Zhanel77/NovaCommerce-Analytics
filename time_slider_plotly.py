import pandas as pd
import plotly.express as px
import os

# --- 1. Загружаем датасеты ---
base = "data"  
orders = pd.read_csv(f"{base}/olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
items = pd.read_csv(f"{base}/olist_order_items_dataset.csv")
products = pd.read_csv(f"{base}/olist_products_dataset.csv")
trans = pd.read_csv(f"{base}/product_category_name_translation.csv")

# --- 2. Объединяем (JOIN через pandas.merge) ---
df = (orders.merge(items, on="order_id")
             .merge(products, on="product_id")
             .merge(trans, on="product_category_name", how="left"))

df["month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()

# --- 3. Считаем выручку по категориям/месяцам ---
df["revenue"] = df["price"] + df["freight_value"]
monthly = (df.groupby(["month","product_category_name_english"])
             .agg(revenue=("revenue","sum"))
             .reset_index())

# --- 4. Берём топ-6 категорий по общей выручке ---
top_cats = (monthly.groupby("product_category_name_english")["revenue"].sum()
                    .sort_values(ascending=False)
                    .head(6).index)
monthly = monthly[monthly["product_category_name_english"].isin(top_cats)]

# --- 5. Строим интерактивный line chart с time slider ---
fig = px.line(
    monthly,
    x="month",
    y="revenue",
    color="product_category_name_english",
    title="Monthly Revenue by Top Product Categories",
    labels={"month":"Date","revenue":"Revenue","product_category_name_english":"Category"},
)

# Добавляем слайдер/анимацию
fig.update_layout(
    xaxis=dict(rangeslider=dict(visible=True), type="date"),
    width=1000, height=600,
)

# --- 6. Сохраняем ---
os.makedirs("charts", exist_ok=True)
out_html = "charts/line_timeslider.html"
fig.write_html(out_html, include_plotlyjs="cdn", auto_open=False)
print(f"✅ Saved interactive chart to {out_html}")
