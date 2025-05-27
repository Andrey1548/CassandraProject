from flask import Flask, request, render_template_string, redirect, url_for
from cassandra_client import add_order, get_orders_by_user, delete_order, get_orders_by_status, update_order_status, get_all_products, get_product, add_product
from uuid import uuid4, UUID

app = Flask(__name__)

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
    options = "".join([f"<option value='{p['product_id']}'>{p['name']} ({p['category']}) - {p['price']} грн</option>" for p in products])

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
      <button type="button" onclick="generateUserId()">🔄 Згенерувати новий User ID</button>
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
        product_id = add_product(name, category, price)
        return f"<p>Товар {name} додано з ID {product_id}</p><a href='/add-product'>Додати ще</a>"

    return render_template_string("""
    <h2>Додати товар</h2>
    <form method="POST">
        <label>Назва:</label><br>
        <input type="text" name="name" required><br>

        <label>Категорія:</label><br>
        <input type="text" name="category" required><br>

        <label>Ціна:</label><br>
        <input type="number" step="0.01" name="price" required><br><br>

        <input type="submit" value="Додати товар">
    </form>
    """)

@app.route("/status-orders", methods=["GET"])
def status_orders():
    status = request.args.get("status", "pending")
    orders = get_orders_by_status(status)
    table = "".join([
        f"<tr><td>{o['order_id']}</td><td>{o['user_id']}</td><td>{o['order_date']}</td><td>{o['total_price']}</td>"
        f"<td>{status}</td><td>"
        f"<a href='/update-status?order_id={o['order_id']}&from={status}&to=delivered'>✅ Доставлено</a> "
        f"<a href='/update-status?order_id={o['order_id']}&from={status}&to=canceled'>❌ Скасувати</a>"
        f"</td></tr>" for o in orders
    ])
    return f"""
    <h2>Замовлення зі статусом: {status}</h2>
    <form method='get'>
      <select name='status'>
        <option value='pending'>pending</option>
        <option value='delivered'>delivered</option>
        <option value='canceled'>canceled</option>
      </select>
      <button type='submit'>Показати</button>
    </form>
    <table border='1'><tr><th>ID</th><th>User</th><th>Дата</th><th>Сума</th><th>Статус</th><th>Дії</th></tr>
    {table}</table>"""

@app.route("/update-status")
def update_status():
    order_id = request.args.get("order_id")
    old = request.args.get("from")
    new = request.args.get("to")
    update_order_status(UUID(order_id), old, new)
    return redirect(url_for('status_orders', status=new))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")