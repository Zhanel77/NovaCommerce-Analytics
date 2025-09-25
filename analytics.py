import os
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text

# строка подключения (подправь, если у тебя другая БД)
DB_URL = os.getenv(
    "DB_URL",
    "postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/postgres"
)

os.makedirs("charts", exist_ok=True)
os.makedirs("exports", exist_ok=True)

plt.rcParams.update({
    "figure.figsize": (10, 6),
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 10
})

SQL = {
 # 1. Pie – распределение выручки по категориям
 "pie_category_revenue": """
  SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
         ROUND(SUM(oi.price),2) AS revenue
  FROM order_items oi
  JOIN products p ON p.product_id = oi.product_id
  LEFT JOIN product_category_name_translation t
    ON t.product_category_name = p.product_category_name
  JOIN orders o ON o.order_id = oi.order_id
  GROUP BY category
  ORDER BY revenue DESC
  LIMIT 12;
 """,
 # Показывает топ-12 товарных категорий по общей выручке.
 # Подходит для круговой диаграммы (pie).

 # 2. Bar – средний чек по штатам (AOV = Average Order Value)
 "bar_aov_by_state": """
  WITH order_totals AS (
    SELECT oi.order_id, SUM(oi.price) AS order_sum
    FROM order_items oi GROUP BY oi.order_id
  )
  SELECT c.customer_state, ROUND(AVG(ot.order_sum),2) AS avg_order_value
  FROM orders o
  JOIN order_totals ot ON ot.order_id = o.order_id
  JOIN customers c ON c.customer_id = o.customer_id
  GROUP BY c.customer_state HAVING COUNT(*)>=50
  ORDER BY avg_order_value DESC LIMIT 15;
 """,
 # Считает средний чек по каждому штату, исключая редкие штаты (<50 заказов).
 # Хорошо идёт в bar chart.

 # 3. HBar – топ-15 продавцов по выручке
 "hbar_top_sellers": """
  SELECT s.seller_id, ROUND(SUM(oi.price),2) AS revenue
  FROM order_items oi
  JOIN sellers s ON s.seller_id = oi.seller_id
  JOIN orders o  ON o.order_id = oi.order_id
  GROUP BY s.seller_id HAVING SUM(oi.price)>0
  ORDER BY revenue DESC LIMIT 15;
 """,
 # Топ продавцов по общей выручке. Отлично подходит для горизонтального bar chart.

 # 4. Line – тренд выручки по месяцам
 "line_monthly_revenue": """
  SELECT DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
         ROUND(SUM(oi.price),2) AS revenue
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  JOIN products p ON p.product_id = oi.product_id
  GROUP BY 1 ORDER BY 1;
 """,
 # Строит помесячную динамику выручки. Подходит для line chart.

 # 5. Hist – распределение сумм заказов
 "hist_order_totals": """
  WITH order_totals AS (
    SELECT o.order_id, SUM(oi.price) AS order_sum
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY o.order_id
  )
  SELECT order_sum FROM order_totals WHERE order_sum IS NOT NULL;
 """,
 # Берём все суммы заказов и строим гистограмму (hist).

 # 6. Scatter – связь между скоростью доставки и оценкой
 "scatter_delivery_vs_review": """
  SELECT EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp))/86400.0 AS delivery_days,
         r.review_score
  FROM orders o
  JOIN order_reviews r ON r.order_id = o.order_id
  WHERE o.order_delivered_customer_date IS NOT NULL
    AND r.review_score IS NOT NULL;
 """,
 # Смотрим, как влияет количество дней доставки на выставленную клиентом оценку (scatter plot).

 # === Новые интересные запросы ===

 # 7. Среднее время доставки по штатам
 "avg_delivery_time_by_state": """
  SELECT c.customer_state,
         ROUND(AVG(order_delivered_customer_date - order_purchase_timestamp),2) AS avg_days
  FROM orders o
  JOIN customers c ON o.customer_id = c.customer_id
  WHERE order_delivered_customer_date IS NOT NULL
  GROUP BY c.customer_state
  ORDER BY avg_days;
 """,
 # Показывает среднее время доставки в днях по каждому штату.

 # 8. Доля способов оплаты
 "payment_share": """
  SELECT payment_type,
         ROUND(SUM(payment_value),2) AS total_value,
         ROUND(100.0 * SUM(payment_value) /
               SUM(SUM(payment_value)) OVER(),2) AS pct_share
  FROM order_payments
  GROUP BY payment_type
  ORDER BY total_value DESC;
 """,
 # Распределение заказов по способам оплаты (credit_card, boleto, etc.).

 # 9. Средняя оценка по категориям товаров
 "avg_review_by_category": """
  SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
         ROUND(AVG(r.review_score),2) AS avg_score,
         COUNT(r.review_id) AS reviews
  FROM order_reviews r
  JOIN orders o ON r.order_id = o.order_id
  JOIN order_items oi ON o.order_id = oi.order_id
  JOIN products p ON oi.product_id = p.product_id
  LEFT JOIN product_category_name_translation t
    ON t.product_category_name = p.product_category_name
  GROUP BY category HAVING COUNT(r.review_id) >= 50
  ORDER BY avg_score DESC
  LIMIT 15;
 """,
 # Сравнение категорий товаров по средним оценкам (оставляем категории с достаточным числом отзывов).

 # 10. Доставка вовремя vs с опозданием
 "on_time_vs_late": """
  SELECT
    SUM(CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1 ELSE 0 END) AS on_time,
    SUM(CASE WHEN order_delivered_customer_date > order_estimated_delivery_date THEN 1 ELSE 0 END) AS late
  FROM orders
  WHERE order_delivered_customer_date IS NOT NULL;
 """,
 # Считает, сколько заказов доставлено вовремя, а сколько с опозданием.
}


def run():
    eng = create_engine(DB_URL)

    # 1. Pie
    df = pd.read_sql(text(SQL["pie_category_revenue"]), eng)
    df.set_index("category")["revenue"].plot.pie(
        autopct="%1.1f%%", ylabel="", title="Revenue Share by Category"
    )
    plt.savefig("charts/01_pie_category_revenue.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"[OK] pie_category_revenue: {len(df)} rows")

    # 2. Bar
    df = pd.read_sql(text(SQL["bar_aov_by_state"]), eng)
    ax = df.plot.bar(x="customer_state", y="avg_order_value", legend=False, title="Average Order Value by State")
    ax.set_xlabel("State"); ax.set_ylabel("Avg order value")
    plt.savefig("charts/02_bar_aov_by_state.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"[OK] bar_aov_by_state: {len(df)} rows")

    # 3. HBar
    df = pd.read_sql(text(SQL["hbar_top_sellers"]), eng)
    ax = df.plot.barh(x="seller_id", y="revenue", legend=False, title="Top Sellers by Revenue")
    ax.set_xlabel("Revenue"); ax.set_ylabel("Seller")
    plt.savefig("charts/03_hbar_top_sellers.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"[OK] hbar_top_sellers: {len(df)} rows")

    # 4. Line
    df = pd.read_sql(text(SQL["line_monthly_revenue"]), eng)
    ax = df.plot.line(x="month", y="revenue", title="Monthly Revenue Trend")
    ax.set_xlabel("Month"); ax.set_ylabel("Revenue")
    plt.savefig("charts/04_line_monthly_revenue.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"[OK] line_monthly_revenue: {len(df)} rows")

    # 5. Hist
    df = pd.read_sql(text(SQL["hist_order_totals"]), eng)
    ax = df["order_sum"].plot.hist(bins=30, title="Distribution of Order Totals")
    ax.set_xlabel("Order total")
    plt.savefig("charts/05_hist_order_totals.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"[OK] hist_order_totals: {len(df)} rows")

    # 6. Scatter
    df = pd.read_sql(text(SQL["scatter_delivery_vs_review"]), eng)
    ax = df.plot.scatter(x="delivery_days", y="review_score", title="Delivery Days vs Review Score")
    ax.set_xlabel("Delivery days"); ax.set_ylabel("Review score")
    plt.savefig("charts/06_scatter_delivery_vs_review.png", dpi=150, bbox_inches="tight"); plt.close()
    print(f"[OK] scatter_delivery_vs_review: {len(df)} rows")

if __name__ == "__main__":
    run()
