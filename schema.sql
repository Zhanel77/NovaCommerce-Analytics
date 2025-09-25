-- schema.sql — Olist e-commerce (FK как NOT VALID)
BEGIN;

CREATE SCHEMA IF NOT EXISTS olist;
SET search_path TO olist;

-- 1) Customers
CREATE TABLE IF NOT EXISTS customers (
  customer_id                VARCHAR PRIMARY KEY,
  customer_unique_id         VARCHAR,
  customer_zip_code_prefix   VARCHAR,
  customer_city              TEXT,
  customer_state             CHAR(2)
);

-- 2) Sellers
CREATE TABLE IF NOT EXISTS sellers (
  seller_id                  VARCHAR PRIMARY KEY,
  seller_zip_code_prefix     VARCHAR,
  seller_city                TEXT,
  seller_state               CHAR(2)
);

-- 3) Geolocation (без PK)
CREATE TABLE IF NOT EXISTS geolocation (
  geolocation_zip_code_prefix VARCHAR,
  geolocation_lat             NUMERIC,
  geolocation_lng             NUMERIC,
  geolocation_city            TEXT,
  geolocation_state           CHAR(2)
);

-- 4) Products
CREATE TABLE IF NOT EXISTS products (
  product_id                  VARCHAR PRIMARY KEY,
  product_category_name       TEXT,
  product_name_lenght         INT,
  product_description_lenght  INT,
  product_photos_qty          INT,
  product_weight_g            INT,
  product_length_cm           INT,
  product_height_cm           INT,
  product_width_cm            INT
);

-- 5) Product category translation
CREATE TABLE IF NOT EXISTS product_category_name_translation (
  product_category_name         TEXT PRIMARY KEY,
  product_category_name_english TEXT
);

-- 6) Orders
CREATE TABLE IF NOT EXISTS orders (
  order_id                      VARCHAR PRIMARY KEY,
  customer_id                   VARCHAR NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
  order_status                  TEXT,
  order_purchase_timestamp      TIMESTAMP,
  order_approved_at             TIMESTAMP,
  order_delivered_carrier_date  TIMESTAMP,
  order_delivered_customer_date TIMESTAMP,
  order_estimated_delivery_date TIMESTAMP
);
CREATE INDEX IF NOT EXISTS orders_customer_idx     ON orders(customer_id);
CREATE INDEX IF NOT EXISTS orders_purchase_ts_idx  ON orders(order_purchase_timestamp);

-- 7) Order items
CREATE TABLE IF NOT EXISTS order_items (
  order_id            VARCHAR NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  order_item_id       INT NOT NULL,
  product_id          VARCHAR NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
  seller_id           VARCHAR NOT NULL REFERENCES sellers(seller_id) ON DELETE RESTRICT,
  shipping_limit_date TIMESTAMP,
  price               NUMERIC,
  freight_value       NUMERIC,
  PRIMARY KEY (order_id, order_item_id)
);
CREATE INDEX IF NOT EXISTS order_items_product_idx ON order_items(product_id);
CREATE INDEX IF NOT EXISTS order_items_seller_idx  ON order_items(seller_id);

-- 8) Order payments
CREATE TABLE IF NOT EXISTS order_payments (
  order_id             VARCHAR NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  payment_sequential   INT NOT NULL,
  payment_type         TEXT,
  payment_installments INT,
  payment_value        NUMERIC,
  PRIMARY KEY (order_id, payment_sequential)
);

-- 9) Order reviews (surrogate PK)
CREATE TABLE IF NOT EXISTS order_reviews (
  id                      BIGSERIAL PRIMARY KEY,
  review_id               VARCHAR,
  order_id                VARCHAR REFERENCES orders(order_id) ON DELETE CASCADE,
  review_score            INT,
  review_comment_title    TEXT,
  review_comment_message  TEXT,
  review_creation_date    TIMESTAMP,
  review_answer_timestamp TIMESTAMP
);
CREATE INDEX IF NOT EXISTS order_reviews_rid_idx   ON order_reviews(review_id);
CREATE INDEX IF NOT EXISTS order_reviews_order_idx ON order_reviews(order_id);

-- 10) FK products -> product_category_name_translation (NOT VALID, чтобы не мешал импорту)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'products_cat_fk'
  ) THEN
    ALTER TABLE products
      ADD CONSTRAINT products_cat_fk
      FOREIGN KEY (product_category_name)
      REFERENCES product_category_name_translation(product_category_name)
      ON DELETE SET NULL
      NOT VALID;  -- <-- ключевое, не проверяем прошлые строки прямо сейчас
  END IF;
END$$;

COMMIT;


-- 03_copy.sql
-- Идемпотентная загрузка: COPY -> *_stg (без ограничений) -> INSERT ... ON CONFLICT DO NOTHING

-- ВАЖНО: сначала указываем схему, чтобы все объекты искались в olist
SET search_path TO olist, public;

-- Уникальные индексы, которые нужны для ON CONFLICT
-- (создаются только если их ещё нет)

-- Геолокация: уникальность по всем 5 колонкам (в CSV полно дублей)
CREATE UNIQUE INDEX IF NOT EXISTS geolocation_uq
  ON geolocation(geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state);

-- Переводы категорий: уникальность по имени категории
CREATE UNIQUE INDEX IF NOT EXISTS product_category_name_translation_uq
  ON product_category_name_translation(product_category_name);

-- Платежи: конфликт определяем по (order_id, payment_sequential)
CREATE UNIQUE INDEX IF NOT EXISTS order_payments_uq
  ON order_payments(order_id, payment_sequential);

BEGIN;

-------------------------------------------------------------------------------
-- 1) customers
-------------------------------------------------------------------------------
CREATE TEMP TABLE customers_stg (LIKE customers INCLUDING DEFAULTS) ON COMMIT DROP;

COPY customers_stg (
  customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state
) FROM '/data/olist_customers_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO customers (
  customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state
)
SELECT
  customer_id, customer_unique_id, customer_zip_code_prefix, customer_city, customer_state
FROM customers_stg
ON CONFLICT (customer_id) DO NOTHING;

-------------------------------------------------------------------------------
-- 2) geolocation  (staging без ограничений; в основную — DISTINCT + ON CONFLICT)
-------------------------------------------------------------------------------
CREATE TEMP TABLE geolocation_stg (LIKE geolocation INCLUDING DEFAULTS) ON COMMIT DROP;

COPY geolocation_stg (
  geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state
) FROM '/data/olist_geolocation_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO geolocation (
  geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state
)
SELECT DISTINCT
  geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state
FROM geolocation_stg
ON CONFLICT (geolocation_zip_code_prefix, geolocation_lat, geolocation_lng, geolocation_city, geolocation_state)
DO NOTHING;

-------------------------------------------------------------------------------
-- 3) product_category_name_translation (загружаем ДО products)
-------------------------------------------------------------------------------
CREATE TEMP TABLE product_category_name_translation_stg (LIKE product_category_name_translation INCLUDING DEFAULTS) ON COMMIT DROP;

COPY product_category_name_translation_stg (
  product_category_name, product_category_name_english
) FROM '/data/product_category_name_translation.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO product_category_name_translation (
  product_category_name, product_category_name_english
)
SELECT
  product_category_name, product_category_name_english
FROM product_category_name_translation_stg
ON CONFLICT (product_category_name) DO NOTHING;

-------------------------------------------------------------------------------
-- 4) products
-------------------------------------------------------------------------------
CREATE TEMP TABLE products_stg (LIKE products INCLUDING DEFAULTS) ON COMMIT DROP;

COPY products_stg (
  product_id, product_category_name, product_name_lenght, product_description_lenght,
  product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm
) FROM '/data/olist_products_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO products (
  product_id, product_category_name, product_name_lenght, product_description_lenght,
  product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm
)
SELECT
  product_id, product_category_name, product_name_lenght, product_description_lenght,
  product_photos_qty, product_weight_g, product_length_cm, product_height_cm, product_width_cm
FROM products_stg
ON CONFLICT (product_id) DO NOTHING;

-------------------------------------------------------------------------------
-- 5) sellers
-------------------------------------------------------------------------------
CREATE TEMP TABLE sellers_stg (LIKE sellers INCLUDING DEFAULTS) ON COMMIT DROP;

COPY sellers_stg (
  seller_id, seller_zip_code_prefix, seller_city, seller_state
) FROM '/data/olist_sellers_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO sellers (
  seller_id, seller_zip_code_prefix, seller_city, seller_state
)
SELECT
  seller_id, seller_zip_code_prefix, seller_city, seller_state
FROM sellers_stg
ON CONFLICT (seller_id) DO NOTHING;

-------------------------------------------------------------------------------
-- 6) orders
-------------------------------------------------------------------------------
CREATE TEMP TABLE orders_stg (LIKE orders INCLUDING DEFAULTS) ON COMMIT DROP;

COPY orders_stg (
  order_id, customer_id, order_status,
  order_purchase_timestamp, order_approved_at,
  order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date
) FROM '/data/olist_orders_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO orders (
  order_id, customer_id, order_status,
  order_purchase_timestamp, order_approved_at,
  order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date
)
SELECT
  order_id, customer_id, order_status,
  order_purchase_timestamp, order_approved_at,
  order_delivered_carrier_date, order_delivered_customer_date, order_estimated_delivery_date
FROM orders_stg
ON CONFLICT (order_id) DO NOTHING;

-------------------------------------------------------------------------------
-- 7) order_items (конфликт по (order_id, order_item_id))
-------------------------------------------------------------------------------
CREATE TEMP TABLE order_items_stg (LIKE order_items INCLUDING DEFAULTS) ON COMMIT DROP;

COPY order_items_stg (
  order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value
) FROM '/data/olist_order_items_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO order_items (
  order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value
)
SELECT
  order_id, order_item_id, product_id, seller_id, shipping_limit_date, price, freight_value
FROM order_items_stg
ON CONFLICT (order_id, order_item_id) DO NOTHING;

-------------------------------------------------------------------------------
-- 8) order_payments (конфликт по (order_id, payment_sequential))
-------------------------------------------------------------------------------
CREATE TEMP TABLE order_payments_stg (LIKE order_payments INCLUDING DEFAULTS) ON COMMIT DROP;

COPY order_payments_stg (
  order_id, payment_sequential, payment_type, payment_installments, payment_value
) FROM '/data/olist_order_payments_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO order_payments (
  order_id, payment_sequential, payment_type, payment_installments, payment_value
)
SELECT
  order_id, payment_sequential, payment_type, payment_installments, payment_value
FROM order_payments_stg
ON CONFLICT (order_id, payment_sequential) DO NOTHING;

-------------------------------------------------------------------------------
-- 9) order_reviews (конфликт по review_id)
-------------------------------------------------------------------------------
CREATE TEMP TABLE order_reviews_stg (LIKE order_reviews INCLUDING DEFAULTS) ON COMMIT DROP;

COPY order_reviews_stg (
  review_id, order_id, review_score, review_comment_title, review_comment_message,
  review_creation_date, review_answer_timestamp
) FROM '/data/olist_order_reviews_dataset.csv'
  CSV HEADER ENCODING 'UTF8';

INSERT INTO order_reviews (
  review_id, order_id, review_score, review_comment_title, review_comment_message,
  review_creation_date, review_answer_timestamp
)
SELECT
  review_id, order_id, review_score, review_comment_title, review_comment_message,
  review_creation_date, review_answer_timestamp
FROM order_reviews_stg
ON CONFLICT (review_id) DO NOTHING;

COMMIT;
