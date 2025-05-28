from cassandra.cluster import Cluster
from uuid import uuid4
from datetime import datetime
import time

# Підключення до Cassandra з повторними спробами
for attempt in range(10):
    try:
        cluster = Cluster(['cassandra'])
        session = cluster.connect()
        break
    except Exception as e:
        print(f"Спроба {attempt+1}: Cassandra ще не готова ({e}), чекаємо...")
        time.sleep(3)
else:
    raise RuntimeError("Неможливо підключитися до Cassandra після кількох спроб.")

# Створення keyspace
session.execute("""
    CREATE KEYSPACE IF NOT EXISTS shop
    WITH REPLICATION = { 'class': 'SimpleStrategy', 'replication_factor': 1 }
""")
session.set_keyspace('shop')

# Таблиця замовлень користувачів
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

# Таблиця замовлень за статусом
session.execute("""
    CREATE TABLE IF NOT EXISTS orders_by_status (
        status TEXT,
        order_id UUID,
        user_id UUID,
        order_date TIMESTAMP,
        total_price DECIMAL,
        product_id UUID,
        PRIMARY KEY (status, order_id)
    )
""")

# Таблиця товарів за категоріями
session.execute("""
    CREATE TABLE IF NOT EXISTS products_by_category (
        category TEXT,
        product_id UUID,
        name TEXT,
        description TEXT,
        price DECIMAL,
        attributes MAP<TEXT, TEXT>,
        PRIMARY KEY (category, product_id)
    )
""")

# Додавання замовлення
def add_order(user_id, status, product_id, name, quantity, price):
    order_id = uuid4()
    order_date = datetime.now()
    total_price = price * quantity

    session.execute("""
        INSERT INTO orders_by_user (user_id, order_id, order_date, status, product_id, name, quantity, price)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, order_id, order_date, status, product_id, name, quantity, price))

    session.execute("""
        INSERT INTO orders_by_status (status, order_id, user_id, order_date, total_price, product_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (status, order_id, user_id, order_date, total_price, product_id))

    return str(order_id)

# Отримання замовлень користувача
def get_orders_by_user(user_id):
    rows = session.execute("SELECT * FROM orders_by_user WHERE user_id = %s", (user_id,))
    return [dict(row._asdict()) for row in rows]

# Видалення замовлення
def delete_order(user_id, order_id):
    session.execute("DELETE FROM orders_by_user WHERE user_id = %s AND order_id = %s", (user_id, order_id))
    result = session.execute("SELECT status FROM orders_by_user WHERE user_id = %s AND order_id = %s", (user_id, order_id)).one()
    if result:
        session.execute("DELETE FROM orders_by_status WHERE status = %s AND order_id = %s", (result.status, order_id))

# Отримання замовлень за статусом
def get_orders_by_status(status):
    rows = session.execute("SELECT * FROM orders_by_status WHERE status = %s", (status,))
    return [dict(row._asdict()) for row in rows]

# Оновлення статусу замовлення
def update_order_status(order_id, old_status, new_status):
    row = session.execute("SELECT * FROM orders_by_status WHERE status = %s AND order_id = %s", (old_status, order_id)).one()
    if row:
        session.execute("DELETE FROM orders_by_status WHERE status = %s AND order_id = %s", (old_status, order_id))
        session.execute("""
            INSERT INTO orders_by_status (status, order_id, user_id, order_date, total_price, product_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (new_status, order_id, row.user_id, row.order_date, row.total_price, row.product_id))

# Додавання товару за категорією
def add_product_by_category(category, name, description, price, attributes):
    product_id = uuid4()
    session.execute("""
        INSERT INTO products_by_category (category, product_id, name, description, price, attributes)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (category, product_id, name, description, price, attributes))
    return product_id

# Отримання всіх товарів
def get_all_products():
    rows = session.execute("SELECT * FROM products_by_category")
    return [dict(row._asdict()) for row in rows]

# Отримання товару за product_id
def get_product(product_id):
    rows = session.execute("SELECT * FROM products_by_category")
    for row in rows:
        if row.product_id == product_id:
            return dict(row._asdict())
    return None
