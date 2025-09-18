-- post_load.sql
-- 1) Добавляем недостающие категории из products в перевод
INSERT INTO olist.product_category_name_translation (product_category_name, product_category_name_english)
SELECT DISTINCT p.product_category_name, NULL
FROM olist.products p
LEFT JOIN olist.product_category_name_translation t
  ON t.product_category_name = p.product_category_name
WHERE p.product_category_name IS NOT NULL
  AND t.product_category_name IS NULL;

-- 2) Удаляем старый FK, если он был
ALTER TABLE olist.products DROP CONSTRAINT IF EXISTS products_cat_fk;

-- 3) Создаём FK заново как NOT VALID
ALTER TABLE olist.products
  ADD CONSTRAINT products_cat_fk
  FOREIGN KEY (product_category_name)
  REFERENCES olist.product_category_name_translation(product_category_name)
  ON DELETE SET NULL
  NOT VALID;

-- 4) Валидируем FK
ALTER TABLE olist.products VALIDATE CONSTRAINT products_cat_fk;
