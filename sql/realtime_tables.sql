-- Realtime table for auto-refresh demo
CREATE TABLE IF NOT EXISTS public.sales_stream (
  id           BIGSERIAL PRIMARY KEY,
  event_time   TIMESTAMPTZ NOT NULL DEFAULT now(),
  product_id   TEXT NOT NULL REFERENCES public.products(product_id),
  customer_id  TEXT NOT NULL REFERENCES public.customers(customer_id),
  qty          INT  NOT NULL CHECK (qty > 0),
  unit_price   NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_sales_stream_event_time ON public.sales_stream(event_time DESC);
CREATE INDEX IF NOT EXISTS idx_sales_stream_product   ON public.sales_stream(product_id);
CREATE INDEX IF NOT EXISTS idx_sales_stream_customer  ON public.sales_stream(customer_id);

-- Minute aggregation view for charts
CREATE OR REPLACE VIEW public.sales_stream_minute AS
SELECT date_trunc('minute', event_time) AS minute_ts,
       COUNT(*)                       AS events_cnt,
       SUM(qty * unit_price)          AS gross_sales
FROM public.sales_stream
GROUP BY 1
ORDER BY 1;
