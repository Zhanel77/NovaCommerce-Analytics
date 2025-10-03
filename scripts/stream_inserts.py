#!/usr/bin/env python3
"""
Insert meaningful streaming rows into `sales_stream` every N seconds.
Usage:
  export DB_URL='postgresql://user:pass@host:port/dbname'
  python scripts/stream_inserts.py --interval 10 --max-rows 0
"""
import os, time, argparse, random
import psycopg2

def get_conn():
    url = os.getenv("DB_URL", "postgresql://postgres:postgres@127.0.0.1:5433/postgres")
    return psycopg2.connect(url)

def ensure_tables(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS public.sales_stream (
      id BIGSERIAL PRIMARY KEY,
      event_time   TIMESTAMPTZ NOT NULL DEFAULT now(),
      product_id   TEXT NOT NULL REFERENCES public.products(product_id),
      customer_id  TEXT NOT NULL REFERENCES public.customers(customer_id),
      qty          INT  NOT NULL CHECK (qty > 0),
      unit_price   NUMERIC(10,2) NOT NULL CHECK (unit_price >= 0)
    );
    CREATE INDEX IF NOT EXISTS idx_sales_stream_event_time ON public.sales_stream(event_time DESC);
    """
    with conn, conn.cursor() as cur:
        cur.execute(ddl)

def pick(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return row[0] if row else None

def insert_row(conn):
    product_id  = pick(conn, "SELECT product_id FROM public.products ORDER BY random() LIMIT 1")
    customer_id = pick(conn, "SELECT customer_id FROM public.customers ORDER BY random() LIMIT 1")
    unit_price  = pick(conn, "SELECT price FROM public.order_items WHERE price > 0 ORDER BY random() LIMIT 1")
    if unit_price is None or product_id is None or customer_id is None:
        return None
    qty = random.randint(1, 3)
    with conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO public.sales_stream (product_id, customer_id, qty, unit_price) VALUES (%s,%s,%s,%s)",
            (product_id, customer_id, qty, unit_price)
        )
    return {"product_id": product_id, "customer_id": customer_id, "qty": qty, "unit_price": float(unit_price)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--max-rows", type=int, default=0, help="0 = infinite")
    args = parser.parse_args()

    conn = get_conn()
    ensure_tables(conn)
    i = 0
    try:
        while True:
            rec = insert_row(conn)
            if rec:
                i += 1
                print(f"[{time.strftime('%H:%M:%S')}] inserted product={rec['product_id']} "
                      f"qty={rec['qty']} price={rec['unit_price']:.2f} cust={rec['customer_id']}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] skipped (no source rows)")
            if args.max_rows and i >= args.max_rows:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped by user")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
