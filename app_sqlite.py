from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
from datetime import date, datetime
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'expiry_system.db')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            batch_no TEXT,
            expiry_date TEXT,
            quantity INTEGER,
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# DASHBOARD
@app.route('/')
def dashboard():
    conn = get_db_connection()
    data = conn.execute("SELECT expiry_date FROM stock").fetchall()
    conn.close()

    today = date.today()

    expired = 0
    tomorrow = 0
    month = 0
    safe = 0

    for row in data:
        # SQLite stores dates as strings, so we parse them back to date objects
        expiry_str = row['expiry_date']
        try:
            expiry = datetime.strptime(expiry_str, '%Y-%m-%d').date()
        except ValueError:
            continue
            
        days = (expiry - today).days

        if expiry <= today:
            expired += 1
        elif days == 1:
            tomorrow += 1
        elif days <= 30:
            month += 1
        else:
            safe += 1

    return render_template(
        "dashboard.html",
        expired=expired,
        tomorrow=tomorrow,
        month=month,
        safe=safe
    )


# ADD STOCK PAGE
@app.route('/add_stock')
def add_stock():
    return render_template("add_stock.html")


# SAVE STOCK
@app.route('/save_stock', methods=['POST'])
def save_stock():
    barcode = request.form['barcode']
    name = request.form['name']
    batch = request.form['batch']
    expiry = request.form['expiry']
    quantity = request.form['quantity']

    conn = get_db_connection()
    cursor = conn.cursor()
    
    product = cursor.execute("SELECT id FROM products WHERE barcode=?", (barcode,)).fetchone()

    if product:
        product_id = product['id']
    else:
        cursor.execute(
            "INSERT INTO products (barcode,name) VALUES (?,?)",
            (barcode, name)
        )
        product_id = cursor.lastrowid

    cursor.execute("""
    INSERT INTO stock (product_id,batch_no,expiry_date,quantity)
    VALUES (?,?,?,?)
    """, (product_id, batch, expiry, quantity))

    conn.commit()
    conn.close()

    return redirect("/")


# VIEW EXPIRY TABLE
@app.route('/view_expiry')
def view_expiry():
    conn = get_db_connection()
    data = conn.execute("""
    SELECT products.name, stock.batch_no, stock.expiry_date
    FROM stock
    JOIN products ON stock.product_id = products.id
    """).fetchall()
    conn.close()

    today = date.today()
    products = []

    for row in data:
        name = row['name']
        batch = row['batch_no']
        expiry_str = row['expiry_date']
        
        try:
            expiry = datetime.strptime(expiry_str, '%Y-%m-%d').date()
        except ValueError:
            continue

        days = (expiry - today).days

        if expiry <= today:
            color = "red"
        elif days == 1:
            color = "orange"
        elif days <= 30:
            color = "yellow"
        else:
            color = "green"

        products.append({
            "name": name,
            "batch": batch,
            "expiry": expiry,
            "days": days,
            "color": color
        })

    return render_template("view_expiry.html", products=products)


# BILLING PAGE
@app.route('/billing')
def billing():
    return render_template("billing.html")


# BARCODE API
@app.route('/getproduct/<barcode>')
def getproduct(barcode):
    conn = get_db_connection()
    product = conn.execute("""
    SELECT products.name, stock.batch_no, stock.expiry_date
    FROM stock
    JOIN products ON stock.product_id=products.id
    WHERE products.barcode=?
    LIMIT 1
    """, (barcode,)).fetchone()
    conn.close()

    if product is None:
        return jsonify({"error": "Product not found"})

    today = date.today()
    expiry_str = product['expiry_date']
    try:
        expiry = datetime.strptime(expiry_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format in DB"})

    status = "OK"

    if expiry < today:
        status = "EXPIRED"
    elif (expiry - today).days == 1:
        status = "EXPIRING TOMORROW"

    return jsonify({
        "name": product['name'],
        "batch": product['batch_no'],
        "expiry": str(expiry),
        "status": status
    })


if __name__ == '__main__':
    app.run(debug=True)
