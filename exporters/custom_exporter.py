import os, time, psycopg2
from prometheus_client import start_http_server, Gauge, Counter

DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433"),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

# === Метрики (10+ штук) ===
g_orders_today         = Gauge('nc_orders_today', 'Заказов за сегодня')
g_revenue_today        = Gauge('nc_revenue_today', 'Выручка за сегодня (BRL)')
g_orders_7d            = Gauge('nc_orders_7d', 'Заказов за 7 дней')
g_revenue_7d           = Gauge('nc_revenue_7d', 'Выручка за 7 дней (BRL)')
g_orders_30d           = Gauge('nc_orders_30d', 'Заказов за 30 дней')
g_revenue_30d          = Gauge('nc_revenue_30d', 'Выручка за 30 дней (BRL)')
g_aov_30d              = Gauge('nc_avg_order_value_30d', 'Средний чек за 30 дней (BRL)')
g_on_time_rate_30d     = Gauge('nc_on_time_rate_30d', 'Доля доставок вовремя за 30 дней (0..1)')
g_review_score_avg_30d = Gauge('nc_avg_review_score_30d', 'Средняя оценка отзывов (0..5) за 30 дней')
g_top_cat_rev          = Gauge('nc_top_category_revenue', 'Выручка топ-категории за 30 дней (BRL)', ['category'])
g_fx_card_share_30d    = Gauge('nc_payment_card_share_30d', 'Доля карточных оплат за 30 дней (0..1)')
g_last_update          = Gauge('nc_last_update_unixtime', 'UNIX время последнего обновления')
g_up                   = Gauge('nc_exporter_up', 'Статус успеха последнего обновления (1/0)')
c_ok                   = Counter('nc_exporter_ok_total', 'Успешные циклы обновления')
c_fail                 = Counter('nc_exporter_fail_total', 'Неуспешные циклы обновления')

SQL = {
# Заказы/выручка за сегодня/7/30 дней — по таблицам orders + order_items
"orders_today": """
SELECT COUNT(DISTINCT o.order_id) AS cnt, COALESCE(SUM(oi.price),0) AS revenue
FROM olist.orders o
LEFT JOIN olist.order_items oi ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp::date = CURRENT_DATE;
""",
"orders_7d": """
SELECT COUNT(DISTINCT o.order_id) AS cnt, COALESCE(SUM(oi.price),0) AS revenue
FROM olist.orders o
LEFT JOIN olist.order_items oi ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '7 day';
""",
"orders_30d": """
SELECT COUNT(DISTINCT o.order_id) AS cnt, COALESCE(SUM(oi.price),0) AS revenue,
       COALESCE(SUM(oi.price),0) / NULLIF(COUNT(DISTINCT o.order_id),0) AS aov
FROM olist.orders o
LEFT JOIN olist.order_items oi ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '30 day';
""",
# Вовремя/опоздавшие: сравнение promised vs delivered
"on_time_30d": """
WITH t AS (
  SELECT o.order_id,
         CASE WHEN o.order_delivered_customer_date IS NOT NULL
                AND o.order_estimated_delivery_date IS NOT NULL
                AND o.order_delivered_customer_date <= o.order_estimated_delivery_date
              THEN 1 ELSE 0 END AS on_time
  FROM olist.orders o
  WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '30 day'
)
SELECT AVG(on_time::float) FROM t;
""",
# Средняя оценка отзывов за 30 дней
"review_avg_30d": """
SELECT AVG(review_score)::float
FROM olist.order_reviews r
JOIN olist.orders o ON o.order_id = r.order_id
WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '30 day';
""",
# Доля карточных оплат за 30 дней
"card_share_30d": """
WITH p AS (
  SELECT payment_type, COUNT(*) AS c
  FROM olist.order_payments pay
  JOIN olist.orders o ON o.order_id = pay.order_id
  WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '30 day'
  GROUP BY payment_type
)
SELECT COALESCE( (SELECT c FROM p WHERE payment_type='credit_card')::float
       / NULLIF( (SELECT SUM(c) FROM p), 0 ), 0.0);
""",
# Топ-категория по выручке за 30 дней (для лейбл-метрики); берём одну top-1
"top_category_30d": """
SELECT COALESCE(t.product_category_name_english,'(unknown)') AS category,
       SUM(oi.price) AS revenue
FROM olist.order_items oi
JOIN olist.products p ON p.product_id = oi.product_id
LEFT JOIN olist.product_category_name_translation t
  ON t.product_category_name = p.product_category_name
JOIN olist.orders o ON o.order_id = oi.order_id
WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '30 day'
GROUP BY category
ORDER BY revenue DESC
LIMIT 1;
"""
}

def fetch_one(cur, name):
    cur.execute(SQL[name])
    return cur.fetchone()

def loop():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    try:
        # today
        cnt, rev = fetch_one(cur, "orders_today")
        g_orders_today.set(cnt or 0); g_revenue_today.set(float(rev or 0))
        # 7d
        cnt, rev = fetch_one(cur, "orders_7d")
        g_orders_7d.set(cnt or 0); g_revenue_7d.set(float(rev or 0))
        # 30d + AOV
        cnt, rev, aov = fetch_one(cur, "orders_30d")
        g_orders_30d.set(cnt or 0); g_revenue_30d.set(float(rev or 0)); g_aov_30d.set(float(aov or 0))
        # on-time rate
        (on_time_rate,) = fetch_one(cur, "on_time_30d")
        g_on_time_rate_30d.set(float(on_time_rate or 0))
        # review avg
        (avg_score,) = fetch_one(cur, "review_avg_30d")
        g_review_score_avg_30d.set(float(avg_score or 0))
        # card share
        (card_share,) = fetch_one(cur, "card_share_30d")
        g_fx_card_share_30d.set(float(card_share or 0))
        # top category label metric
        row = fetch_one(cur, "top_category_30d")
        if row:
            category, revenue = row
            g_top_cat_rev.labels(category=category).set(float(revenue or 0))

        g_last_update.set(time.time())
        g_up.set(1); c_ok.inc()
    except Exception as e:
        g_up.set(0); c_fail.inc()
    finally:
        cur.close(); conn.close()

if __name__ == "__main__":
    # Если запускаешь внутри docker-сети, host/port берутся из env и DB_PORT="5432"
    # Локально — поменяй DB_PORT=5433
    start_http_server(9101)
    while True:
        loop()
        time.sleep(20)   # обновление каждые ~20 секунд
