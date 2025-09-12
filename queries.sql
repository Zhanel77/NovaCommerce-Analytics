-- 1) Топ-категории по выручке
-- revenue по category (перевод на английский), сортировка по выручке
SELECT t.product_category_name_english AS category,
       ROUND(SUM(oi.price),2) AS revenue
FROM olist.order_items oi
JOIN olist.products p  ON p.product_id = oi.product_id
LEFT JOIN olist.product_category_name_translation t
       ON t.product_category_name = p.product_category_name
GROUP BY t.product_category_name_english
ORDER BY revenue DESC
LIMIT 20;

-- 2) Топ-продавцы по выручке
SELECT s.seller_id,
       s.seller_city, s.seller_state,
       ROUND(SUM(oi.price),2) AS revenue
FROM olist.order_items oi
JOIN olist.sellers s ON s.seller_id = oi.seller_id
GROUP BY s.seller_id, s.seller_city, s.seller_state
ORDER BY revenue DESC
LIMIT 20;

-- 3) Средний чек (AOV) по штатам клиентов
SELECT c.customer_state,
       ROUND(SUM(oi.price)/COUNT(DISTINCT o.order_id),2) AS avg_order_value
FROM olist.orders o
JOIN olist.customers c ON c.customer_id = o.customer_id
JOIN olist.order_items oi ON oi.order_id = o.order_id
GROUP BY c.customer_state
ORDER BY avg_order_value DESC;

-- 4) Доля способов оплаты
SELECT payment_type,
       COUNT(*) AS cnt,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),2) AS pct
FROM olist.order_payments
GROUP BY payment_type
ORDER BY cnt DESC;

-- 5) Скорость доставки (в днях) по штатам клиентов (только доставленные)
SELECT c.customer_state,
       ROUND(AVG(EXTRACT(EPOCH FROM (o.order_delivered_customer_date - o.order_purchase_timestamp))/86400.0),2) AS avg_days
FROM olist.orders o
JOIN olist.customers c ON c.customer_id = o.customer_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_days;

-- 6) Оценки отзывов: средняя оценка по категориям
SELECT t.product_category_name_english AS category,
       ROUND(AVG(r.review_score),2) AS avg_score,
       COUNT(*) AS n_reviews
FROM olist.order_reviews r
JOIN olist.orders o        ON o.order_id = r.order_id
JOIN olist.order_items oi  ON oi.order_id = o.order_id
JOIN olist.products p      ON p.product_id = oi.product_id
LEFT JOIN olist.product_category_name_translation t
       ON t.product_category_name = p.product_category_name
GROUP BY t.product_category_name_english
HAVING COUNT(*) >= 50
ORDER BY avg_score DESC
LIMIT 20;

-- 7) Тренд заказов по месяцам
SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month,
       COUNT(*) AS n_orders
FROM olist.orders
GROUP BY 1
ORDER BY 1;

-- 8) «Дорого/дёшево»: распределение цены позиций
SELECT CASE
         WHEN price < 50 THEN '< 50'
         WHEN price < 100 THEN '50–100'
         WHEN price < 200 THEN '100–200'
         WHEN price < 500 THEN '200–500'
         ELSE '>= 500'
       END AS bucket,
       COUNT(*) AS cnt
FROM olist.order_items
GROUP BY 1
ORDER BY cnt DESC;

-- 9) Топ-товары по количеству продаж (по item-строкам)
SELECT product_id, COUNT(*) AS n_items
FROM olist.order_items
GROUP BY product_id
ORDER BY n_items DESC
LIMIT 20;

-- 10) Cancellations/Delivered: статусная воронка
SELECT order_status, COUNT(*) AS cnt
FROM olist.orders
GROUP BY order_status
ORDER BY cnt DESC;
