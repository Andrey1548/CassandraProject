from cassandra.cluster import Cluster
from uuid import uuid4
from datetime import datetime
import time

for attempt in range(10):
    try:
        cluster = Cluster(['cassandra'])
        session = cluster.connect()
        break
    except Exception as e:
        print(f"⏳ Спроба {attempt+1}: Cassandra ще не готова ({e}), чекаємо...")
        time.sleep(3)
else:
    raise RuntimeError("❌ Неможливо підключитися до Cassandra після кількох спроб.")

session.execute("""
    CREATE KEYSPACE IF NOT EXISTS shop
    WITH REPLICATION = { 'class': 'SimpleStrategy', 'replication_factor': 1 }
""")

session.set_keyspace('shop')

session.execute("""
    CREATE TABLE IF NOT EXISTS orders_by_user (
        user_id UUID,
        order_id UUID,
        order_date TIMESTAMP,
        status TEXT,
        product_id UUID,
        name TEXT,
        quantity INT,
        price DECIMAL,
        PRIMARY KEY (user_id, order_id)
    )
""")

session.execute("""
    CREATE TABLE IF NOT EXISTS orders_by_status (
        status TEXT,
        order_id UUID,
        user_id UUID,
        order_date TIMESTAMP,
        total_price DECIMAL,
        PRIMARY KEY (status, order_id)
    )
""")

session.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id UUID PRIMARY KEY,
        name TEXT,
        category TEXT,
        price DECIMAL
    )
""")

def add_order(user_id, status, product_id, name, quantity, price):
    order_id = uuid4()
    order_date = datetime.now()
    total_price = price * quantity

    session.execute("""
        INSERT INTO orders_by_user (user_id, order_id, order_date, status, product_id, name, quantity, price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, order_id, order_date, status, product_id, name, quantity, price))

    session.execute("""
        INSERT INTO orders_by_status (status, order_id, user_id, order_date, total_price)
        VALUES (%s, %s, %s, %s, %s)
    """, (status, order_id, user_id, order_date, total_price))

    return str(order_id)

def get_orders_by_user(user_id):
    rows = session.execute("SELECT * FROM orders_by_user WHERE user_id = %s", (user_id,))
    return [dict(row._asdict()) for row in rows]

def delete_order(user_id, order_id):
    session.execute("DELETE FROM orders_by_user WHERE user_id = %s AND order_id = %s", (user_id, order_id))
    result = session.execute("SELECT status FROM orders_by_user WHERE user_id = %s AND order_id = %s", (user_id, order_id)).one()
    if result:
        session.execute("DELETE FROM orders_by_status WHERE status = %s AND order_id = %s", (result.status, order_id))

def get_orders_by_status(status):
    rows = session.execute("SELECT * FROM orders_by_status WHERE status = %s", (status,))
    return [dict(row._asdict()) for row in rows]

def update_order_status(order_id, old_status, new_status):
    row = session.execute("SELECT * FROM orders_by_status WHERE status = %s AND order_id = %s", (old_status, order_id)).one()
    if row:
        session.execute("DELETE FROM orders_by_status WHERE status = %s AND order_id = %s", (old_status, order_id))
        session.execute("INSERT INTO orders_by_status (status, order_id, user_id, order_date, total_price) VALUES (%s, %s, %s, %s, %s)",
                        (new_status, order_id, row.user_id, row.order_date, row.total_price))
        
def get_all_products():
    rows = session.execute("SELECT * FROM products")
    return [dict(row._asdict()) for row in rows]

def add_product(name, category, price):
    product_id = uuid4()
    session.execute("INSERT INTO products (product_id, name, category, price) VALUES (%s, %s, %s, %s)",
                    (product_id, name, category, price))
    return product_id


def get_product(product_id):
    row = session.execute("SELECT * FROM products WHERE product_id = %s", (product_id,)).one()
    return dict(row._asdict()) if row else None