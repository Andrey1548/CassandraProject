from flask import Flask, request, render_template_string, redirect, url_for
from cassandra_client import add_order, get_orders_by_user, delete_order, get_orders_by_status, update_order_status, get_all_products, get_product, add_product_by_category
from uuid import uuid4, UUID

app = Flask(__name__)

@app.route("/")
def index():
    return render_template_string("""
    <h1>📦 Система замовлень</h1>
    <a href='/form-order'><button>🛒 Створити замовлення</button></a>
    <a href='/add-product'><button>➕ Додати товар</button></a>
    <a href='/status-orders'><button>📋 Замовлення за статусом</button></a>
    <a href='/products-by-category'><button>🗂️ Перегляд товарів</button></a>
    """)

@app.route("/form-order", methods=["GET", "POST"])
def form_order():
    if request.method == "POST":
        form = request.form

        user_id = form.get("user_id") or str(uuid4())
        product_id = form["product_id"]
        product = get_product(UUID(product_id))
        if not product:
            return "Невірний product_id"

        status = form.get("status") or "pending"

        order_id = add_order(
            user_id=UUID(user_id),
            status=status,
            product_id=UUID(product_id),
            name=product["name"],
            quantity=int(form["quantity"]),
            price=float(product["price"])
        )
        return f"<p>Замовлення {order_id} створено!</p><a href=\"/form-order\">Назад</a>"

    products = get_all_products()
    options = "".join([
        f"<option value='{p['product_id']}'>{p['name']} ({p['category']}) - {p['price']} грн</option>"
        for p in products
    ])

    form_html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Додати замовлення</title>
    <script>
    function generateUserId() {{
      const newId = crypto.randomUUID();
      document.getElementById('user_id').value = newId;
      localStorage.setItem('user_id', newId);
      document.getElementById('user_display').innerText = newId;
    }}

    function loadUserId() {{
      const savedId = localStorage.getItem('user_id');
      const newId = savedId || crypto.randomUUID();
      document.getElementById('user_id').value = newId;
      document.getElementById('user_display').innerText = newId;
      if (!savedId) {{
        localStorage.setItem('user_id', newId);
      }}
    }}

    window.onload = loadUserId;
    </script>
    </head>
    <body>
      <h2>Форма створення замовлення</h2>
      <p><strong>User ID:</strong> <span id="user_display"></span></p>
      <button type="button" onclick="generateUserId()">Згенерувати новий User ID</button>
      <form method="POST">
        <input type="hidden" id="user_id" name="user_id">
        <input type="hidden" id="status" name="status" value="pending">

        <label>Товар:</label><br>
        <select name="product_id" required>{options}</select><br>

        <label>Кількість:</label><br>
        <input type="number" name="quantity" required><br><br>
        <input type="submit" value="Додати замовлення">
      </form>
    </body>
    </html>
    """
    return render_template_string(form_html)

@app.route("/add-product", methods=["GET", "POST"])
def add_product_route():
    if request.method == "POST":
        name = request.form["name"]
        category = request.form["category"]
        price = float(request.form["price"])
        description = request.form.get("description", "")

        attributes_raw = request.form.get("attributes", "")
        attributes = {}
        for pair in attributes_raw.split(","):
            if ":" in pair:
                k, v = pair.split(":", 1)
                attributes[k.strip()] = v.strip()

        product_id = add_product_by_category(category, name, description, price, attributes)
        return f"<p>Товар {name} додано з ID {product_id}</p><a href='/add-product'>Додати ще</a>"

    return render_template_string("""
    <h2>Додати товар</h2>
    <form method="POST">
        <label>Назва:</label><br>
        <input type="text" name="name" required><br>

        <label>Категорія:</label><br>
        <input type="text" name="category" required><br>

        <label>Ціна:</label><br>
        <input type="number" step="0.01" name="price" required><br>

        <label>Опис:</label><br>
        <textarea name="description"></textarea><br>

        <label>Атрибути (key:value, розділені комами):</label><br>
        <input type="text" name="attributes" placeholder="color:red, size:M"><br><br>

        <input type="submit" value="Додати товар">
    </form>
    """)

@app.route("/products-by-category")
def view_products_by_category():
    products = get_all_products()
    categories = {}
    for p in products:
        cat = p['category']
        categories.setdefault(cat, []).append(p)

    html = "<h2>Товари за категоріями</h2>"
    for category, items in categories.items():
        html += f"<h3>{category}</h3><ul>"
        for item in items:
            html += f"<li>{item['name']} — {item['price']} грн<br><small>{item.get('description', '')}</small></li>"
        html += "</ul>"

    return render_template_string(html)

@app.route("/status-orders", methods=["GET"])
def status_orders():
    status = request.args.get("status", "pending")
    orders = get_orders_by_status(status)
    html = f"<h2>Замовлення зі статусом: {status}</h2>"
    html += "<a href='/'><button>🏠 На головну</button></a><br><br>"
    html += """
    <form method='get'>
      <select name='status'>
        <option value='pending'>pending</option>
        <option value='delivered'>delivered</option>
        <option value='canceled'>canceled</option>
      </select>
      <button type='submit'>Показати</button>
    </form>
    <table border='1'>
    <tr><th>ID</th><th>User</th><th>Дата</th><th>Сума</th><th>Статус</th><th>Товар</th><th>Категорія</th><th>Attributes</th><th>Дії</th></tr>
    """
    for o in orders:
        product = get_product(o.get('product_id')) if o.get('product_id') else None
        name = product['name'] if product and 'name' in product else '-'
        category = product['category'] if product and 'category' in product else '-'
        attributes = product['attributes'] if product and 'attributes' in product else {}
        attr_str = ", ".join(f"{k}:{v}" for k, v in attributes.items()) if attributes else "-"
        html += f"<tr><td>{o['order_id']}</td><td>{o['user_id']}</td><td>{o['order_date']}</td><td>{o['total_price']} грн</td><td>{status}</td><td>{name}</td><td>{category}</td><td>{attr_str}</td>"
        html += f"<td><a href='/update-status?order_id={o['order_id']}&from={status}&to=delivered'>✅ Доставлено</a> "
        html += f"<a href='/update-status?order_id={o['order_id']}&from={status}&to=canceled'>❌ Скасувати</a></td></tr>"
    html += "</table>"
    return render_template_string(html)

@app.route("/update-status")
def update_status():
    order_id = request.args.get("order_id")
    old = request.args.get("from")
    new = request.args.get("to")
    update_order_status(UUID(order_id), old, new)
    return redirect(url_for('status_orders', status=new))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")