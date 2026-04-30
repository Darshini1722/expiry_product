from flask import Flask, render_template, request, redirect, jsonify
import mysql.connector
from datetime import date

app = Flask(__name__)

# DATABASE CONNECTION
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="aadhi",
    database="expiry_system"
)

def get_cursor():
    return db.cursor()

# ================= DASHBOARD =================
@app.route('/')
def dashboard():
    cursor = get_cursor()
    cursor.execute("SELECT expiry_date FROM stock")
    data = cursor.fetchall()

    today = date.today()
    expired = tomorrow = month = safe = 0

    for row in data:
        expiry = row[0]
        days = (expiry - today).days

        if expiry <= today:
            expired += 1
        elif days == 1:
            tomorrow += 1
        elif days <= 30:
            month += 1
        else:
            safe += 1

    return render_template("dashboard.html",
        expired=expired,
        tomorrow=tomorrow,
        month=month,
        safe=safe
    )
# ================= ADD STOCK =================
@app.route('/add_stock')
def add_stock():
    return render_template("add_stock.html")

@app.route('/save_stock', methods=['POST'])
def save_stock():
    cursor = get_cursor()

    barcode = request.form['barcode']
    name = request.form['name']
    batch = request.form['batch']
    expiry = request.form['expiry']
    quantity = request.form['quantity']

    cursor.execute("SELECT id FROM products WHERE barcode=%s", (barcode,))
    product = cursor.fetchone()

    if product:
        product_id = product[0]
    else:
        cursor.execute("INSERT INTO products (barcode,name) VALUES (%s,%s)", (barcode, name))
        db.commit()
        product_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO stock (product_id,batch_no,expiry_date,quantity)
        VALUES (%s,%s,%s,%s)
    """, (product_id, batch, expiry, quantity))

    db.commit()
    return redirect("/")

# ================= VIEW EXPIRY =================
@app.route('/view_expiry')
def view_expiry():
    cursor = get_cursor()

    filter_type = request.args.get("type")

    cursor.execute("""
    SELECT products.name, stock.batch_no, stock.expiry_date
    FROM stock
    JOIN products ON stock.product_id = products.id
    """)

    data = cursor.fetchall()
    today = date.today()

    expired = []
    tomorrow = []
    month = []
    safe = []

    for row in data:
        name, batch, expiry = row
        days = (expiry - today).days

        item = {
            "name": name,
            "batch": batch,
            "expiry": expiry,
            "days": days
        }

        if expiry <= today:
            expired.append(item)
        elif days == 1:
            tomorrow.append(item)
        elif days <= 30:
            month.append(item)
        else:
            safe.append(item)

    return render_template("view_expiry.html",
        expired=expired,
        tomorrow=tomorrow,
        month=month,
        safe=safe,
        show=filter_type if filter_type else "all"
    )

# ================= BILLING =================
@app.route('/billing')
def billing():
    return render_template("billing.html")

# ================= BARCODE API =================
@app.route('/getproduct/<barcode>')
def getproduct(barcode):
    cursor = get_cursor()

    cursor.execute("""
    SELECT products.name, stock.batch_no, stock.expiry_date
    FROM stock
    JOIN products ON stock.product_id = products.id
    WHERE products.barcode=%s
    LIMIT 1
    """, (barcode,))

    product = cursor.fetchone()

    if product is None:
        return jsonify({"error": "Product not found"})

    today = date.today()
    expiry = product[2]

    status = "OK"
    if expiry < today:
        status = "EXPIRED"
    elif (expiry - today).days == 1:
        status = "EXPIRING TOMORROW"

    return jsonify({
        "name": product[0],
        "batch": product[1],
        "expiry": str(expiry),
        "status": status
    })

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)