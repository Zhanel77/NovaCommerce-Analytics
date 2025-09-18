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
