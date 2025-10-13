# новый заказ добавляем в таблицу orders

import os, time, random, uuid
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

CFG = {
    "host": os.getenv("PG_HOST", "127.0.0.1"),
    "port": int(os.getenv("PG_PORT", "5433")),
    "dbname": os.getenv("PG_DB", "postgres"),
    "user": os.getenv("PG_USER", "postgres"),
    "password": os.getenv("PG_PASS", "postgres"),
}
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "5"))
INTERVAL_MAX = int(os.getenv("INTERVAL_MAX", "10"))

STATUSES = ["created", "approved", "canceled"]  

def connect():
    return psycopg2.connect(**CFG)

def existing_customers(cur):
    cur.execute("""
        SELECT DISTINCT customer_id
        FROM orders
        WHERE customer_id IS NOT NULL
        LIMIT 10000
    """)
    return [r[0] for r in cur.fetchall()]

def fallback_customers(n=100):
    return [f"CUST{str(i).zfill(4)}" for i in range(1, n+1)]

def main():
    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    customers = existing_customers(cur)
    if not customers:
        customers = fallback_customers()  

    print(f"[init] known_customers={len(customers)}")

    while True:
        try:
            order_id = str(uuid.uuid4())
            customer_id = random.choice(customers)

            now = datetime.now(timezone.utc)
            purchase_ts = now - timedelta(seconds=random.randint(0, 2))  

            # выберем статус (чаще created/approved)
            roll = random.random()
            if roll < 0.65:
                status = "created"
            elif roll < 0.95:
                status = "approved"
            else:
                status = "canceled"

            approved_at = None
            if status == "approved":
                approved_at = purchase_ts + timedelta(seconds=random.randint(5, 120))

            # для новых заказов доставка ещё не началась
            delivered_carrier = None
            delivered_customer = None

            estimated_delivery = purchase_ts + timedelta(days=random.randint(2, 10))

            cur.execute("""
                INSERT INTO orders (
                    order_id,
                    customer_id,
                    order_status,
                    order_purchase_timestamp,
                    order_approved_at,
                    order_delivered_carrier_date,
                    order_delivered_customer_date,
                    order_estimated_delivery_date
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                order_id,
                customer_id,
                status,
                purchase_ts,
                approved_at,
                delivered_carrier,
                delivered_customer,
                estimated_delivery
            ))
            conn.commit()

            print(f"[insert] id={order_id} cust={customer_id} status={status} "
                  f"purchase={purchase_ts.isoformat()} est_deliv={estimated_delivery.date()}")

        except Exception as e:
            conn.rollback()
            print("[error]", e)

        time.sleep(random.randint(INTERVAL_MIN, INTERVAL_MAX))

if __name__ == "__main__":
    main()
