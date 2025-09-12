-- Schema for Olist e-commerce dataset
-- Run: psql -U postgres -d olistdb -f schema.sql

BEGIN;

CREATE SCHEMA IF NOT EXISTS olist;
SET search_path TO olist;

-- Customers
CREATE TABLE customers (
    customer_id            VARCHAR PRIMARY KEY,
    customer_unique_id     VARCHAR,
    customer_zip_code_prefix VARCHAR,
    customer_city          TEXT,
    customer_state         CHAR(2)
);

-- Sellers
CREATE TABLE sellers (
    seller_id              VARCHAR PRIMARY KEY,
    seller_zip_code_prefix VARCHAR,
    seller_city            TEXT,
    seller_state           CHAR(2)
);

-- Geolocation
CREATE TABLE geolocation (
    geolocation_zip_code_prefix VARCHAR,
    geolocation_lat     NUMERIC,
    geolocation_lng     NUMERIC,
    geolocation_city    TEXT,
    geolocation_state   CHAR(2)
);

-- Orders
CREATE TABLE orders (
    order_id              VARCHAR PRIMARY KEY,
    customer_id           VARCHAR REFERENCES customers(customer_id),
    order_status          TEXT,
    order_purchase_timestamp TIMESTAMP,
    order_approved_at     TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

-- Order Items
CREATE TABLE order_items (
    order_id              VARCHAR REFERENCES orders(order_id),
    order_item_id         INT,
    product_id            VARCHAR,
    seller_id             VARCHAR REFERENCES sellers(seller_id),
    shipping_limit_date   TIMESTAMP,
    price                 NUMERIC,
    freight_value         NUMERIC,
    PRIMARY KEY (order_id, order_item_id)
);

-- Products
CREATE TABLE products (
    product_id            VARCHAR PRIMARY KEY,
    product_category_name TEXT,
    product_name_lenght   INT,
    product_description_lenght INT,
    product_photos_qty    INT,
    product_weight_g      INT,
    product_length_cm     INT,
    product_height_cm     INT,
    product_width_cm      INT
);

-- Product category name translation
CREATE TABLE product_category_name_translation (
    product_category_name        TEXT,
    product_category_name_english TEXT
);

-- Order Payments
CREATE TABLE order_payments (
    order_id              VARCHAR REFERENCES orders(order_id),
    payment_sequential    INT,
    payment_type          TEXT,
    payment_installments  INT,
    payment_value         NUMERIC
);

-- Order Reviews
CREATE TABLE order_reviews (
    id BIGSERIAL PRIMARY KEY,
    review_id VARCHAR,
    order_id  VARCHAR REFERENCES orders(order_id),
    review_score INT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP
);
CREATE INDEX order_reviews_rid_idx ON order_reviews(review_id);


COMMIT;
