import os
import pandas as pd
import plotly.express as px

BASE="data"

# ===== Загрузка и подготовка =====
orders   = pd.read_csv(f"{BASE}/olist_orders_dataset.csv", parse_dates=["order_purchase_timestamp"])
items    = pd.read_csv(f"{BASE}/olist_order_items_dataset.csv")
products = pd.read_csv(f"{BASE}/olist_products_dataset.csv")
trans    = pd.read_csv(f"{BASE}/product_category_name_translation.csv")
customers= pd.read_csv(f"{BASE}/olist_customers_dataset.csv")  # на случай альтернативного графика

df = (orders.merge(items, on="order_id")
             .merge(products, on="product_id")
             .merge(trans, on="product_category_name", how="left")
             .merge(customers[["customer_id","customer_state"]], on="customer_id", how="left"))

df["cat"] = (df["product_category_name_english"]
             .fillna(df["product_category_name"])
             .fillna("unknown")
             .astype(str).str.strip().str.lower())

df["month"]   = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
df["revenue"] = df["price"].fillna(0) + df["freight_value"].fillna(0)

# ===== Агрегация по категориям =====
monthly = (df.groupby(["month","cat"], dropna=False)
             .agg(revenue=("revenue","sum"))
             .reset_index())

# Топ-N категорий по всей истории (N=8)
N = 8
top_cats = (monthly.groupby("cat")["revenue"]
                    .sum().sort_values(ascending=False)
                    .head(N).index.tolist())
monthly_top = monthly[monthly["cat"].isin(top_cats)].copy()

print(f"Найдено уникальных категорий: {monthly['cat'].nunique()}, в топ-{N}: {len(top_cats)} -> {top_cats}")
all_months = pd.period_range(monthly_top["month"].min(), monthly_top["month"].max(), freq="M").to_timestamp()
cats = sorted(monthly_top["cat"].unique())

full_grid = (
    pd.MultiIndex.from_product([all_months, cats], names=["month", "cat"])
      .to_frame(index=False)
)

monthly_full = (
    full_grid
    .merge(monthly_top, on=["month","cat"], how="left")
    .fillna({"revenue": 0.0})
    .sort_values(["month","cat"])
)

# ---- Формируем кадры «накопительно до месяца m», чтобы линии рисовались плавно ----
frames = []
for m in all_months:
    part = monthly_full[monthly_full["month"] <= m].copy()
    part["frame_month"] = m
    frames.append(part)

anim = pd.concat(frames, ignore_index=True)
anim["frame_month_str"] = pd.to_datetime(anim["frame_month"]).dt.strftime("%Y-%m")

import plotly.express as px
fig = px.line(
    anim,
    x="month", y="revenue",
    color="cat",
    animation_frame="frame_month_str",
    line_group="cat",
    title=f"Monthly Revenue by Top {len(cats)} Categories (Animated)",
    labels={"month":"Date","revenue":"Revenue","cat":"Category","frame_month_str":"Month"},
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
print("✅ Saved: charts/line_timeslider_categories.html")