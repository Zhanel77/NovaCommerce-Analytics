import os
import time
import psycopg2
import requests
from prometheus_client import start_http_server, Gauge, Counter

# --------- настройки БД ---------
DB = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433"),  # локально 5433, в докере ты передаёшь 5432
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
}

# --------- настройки погоды ---------
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_CITY = os.getenv("WEATHER_CITY", "Almaty")

# === ТВОИ МЕТРИКИ ИЗ БД (как были) ===
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

# === НОВЫЕ МЕТРИКИ ПО ПОГОДЕ ===
w_temp     = Gauge('nc_weather_temp_c', 'Current temperature in C')
w_feels    = Gauge('nc_weather_feelslike_c', 'Feels like temperature in C')
w_hum      = Gauge('nc_weather_humidity', 'Humidity percent')
w_press    = Gauge('nc_weather_pressure_hpa', 'Pressure in hPa')
w_wind     = Gauge('nc_weather_wind_mps', 'Wind speed m/s')
w_clouds   = Gauge('nc_weather_clouds_pct', 'Cloudiness percent')
w_up       = Gauge('nc_weather_up', '1 if weather API ok else 0')
w_updated  = Gauge('nc_weather_last_update_unixtime', 'Unix time of last weather update')

SQL = {
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
    "review_avg_30d": """
    SELECT AVG(review_score)::float
    FROM olist.order_reviews r
    JOIN olist.orders o ON o.order_id = r.order_id
    WHERE o.order_purchase_timestamp >= CURRENT_DATE - INTERVAL '30 day';
    """,
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

def fetch_weather():
    """Тянем погоду из OpenWeather и пишем в метрики."""
    if not WEATHER_API_KEY:
        # если ключ не передали — просто ставим 0
        w_up.set(0)
        return
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={WEATHER_CITY}&appid={WEATHER_API_KEY}&units=metric"
        resp = requests.get(url, timeout=5)
        data = resp.json()

        main = data.get("main", {})
        wind = data.get("wind", {})
        clouds = data.get("clouds", {})

        if "temp" in main:
            w_temp.set(float(main["temp"]))
        if "feels_like" in main:
            w_feels.set(float(main["feels_like"]))
        if "humidity" in main:
            w_hum.set(float(main["humidity"]))
        if "pressure" in main:
            w_press.set(float(main["pressure"]))
        if "speed" in wind:
            w_wind.set(float(wind["speed"]))
        if "all" in clouds:
            w_clouds.set(float(clouds["all"]))

        w_up.set(1)
        w_updated.set(time.time())
    except Exception:
        w_up.set(0)

def loop():
    # 1. БД
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()

        cnt, rev = fetch_one(cur, "orders_today")
        g_orders_today.set(cnt or 0)
        g_revenue_today.set(float(rev or 0))

        cnt, rev = fetch_one(cur, "orders_7d")
        g_orders_7d.set(cnt or 0)
        g_revenue_7d.set(float(rev or 0))

        cnt, rev, aov = fetch_one(cur, "orders_30d")
        g_orders_30d.set(cnt or 0)
        g_revenue_30d.set(float(rev or 0))
        g_aov_30d.set(float(aov or 0))

        (on_time_rate,) = fetch_one(cur, "on_time_30d")
        g_on_time_rate_30d.set(float(on_time_rate or 0))

        (avg_score,) = fetch_one(cur, "review_avg_30d")
        g_review_score_avg_30d.set(float(avg_score or 0))

        (card_share,) = fetch_one(cur, "card_share_30d")
        g_fx_card_share_30d.set(float(card_share or 0))

        row = fetch_one(cur, "top_category_30d")
        if row:
            category, revenue = row
            g_top_cat_rev.labels(category=category).set(float(revenue or 0))

        g_last_update.set(time.time())
        g_up.set(1)
        c_ok.inc()

        cur.close()
        conn.close()
    except Exception:
        g_up.set(0)
        c_fail.inc()

    # 2. Погода
    fetch_weather()

if __name__ == "__main__":
    start_http_server(9101)
    while True:
        loop()
        time.sleep(20)
