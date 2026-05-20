from flask import Flask, render_template, redirect, url_for, request, flash, session, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import sqlite3
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-later'


# ── Database connection ───────────────────────────────────────

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ── Create tables ─────────────────────────────────────────────

def create_tables():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            normal_price REAL NOT NULL DEFAULT 0.0,
            image_path TEXT NOT NULL DEFAULT 'placeholder.png',
            category TEXT NOT NULL DEFAULT 'Ingen kategori',
            stock INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            change INTEGER NOT NULL,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    """)
    conn.commit()
    conn.close()


# ── Helper function ───────────────────────────────────────────

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return user
    return None


# ── Auth routes ───────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()

        # Check if username already exists
        existing_user = conn.execute(
            "SELECT * FROM user WHERE username = ?", (username,)
        ).fetchone()

        if existing_user:
            conn.close()
            flash('Brugernavnet er allerede taget. Prøv et andet.')
            return redirect(url_for('register'))

        # Check if email already exists
        existing_email = conn.execute(
            "SELECT * FROM user WHERE email = ?", (email,)
        ).fetchone()

        if existing_email:
            conn.close()
            flash('E-mail er allerede registreret. Prøv at logge ind.')
            return redirect(url_for('register'))

        # Hash the password before saving
        hashed_password = generate_password_hash(password)

        # Insert the new user into the database
        conn.execute(
            "INSERT INTO user (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed_password)
        )
        conn.commit()
        conn.close()

        flash('Konto oprettet! Log venligst ind.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM customers WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        # Check user exists and password matches
        if not user or not check_password_hash(user['password_hash'], password):
            flash('Forkert e-mail eller adgangskode.')
            return redirect(url_for('login'))

        # Save user id in session
        session['user_id'] = user['id']
        return redirect(url_for('get_products'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


# ── Images ────────────────────────────────────────────────────

@app.route('/images/<filename>')
def get_image(filename):
    return send_from_directory('Databasebillederne', filename)


# ── Product routes ────────────────────────────────────────────

@app.route('/products')
def get_products():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    return render_template('products.html', products=products, user=current_user)


@app.route('/product/<int:product_id>')
def get_product(product_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()

    if product is None:
        return {'error': 'Produkt ikke fundet'}, 404

    return render_template('product_detail.html', product=product, user=current_user)


@app.route('/product/barcode/<barcode>')
def get_product_by_barcode(barcode):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()
    conn.close()

    if product is None:
        return jsonify({'error': 'Produkt ikke fundet'}), 404

    return jsonify(dict(product))


# ── Scan route ────────────────────────────────────────────────

@app.route('/scan', methods=['POST'])
def scan_product():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Ingen data modtaget'}), 400

    barcode = data.get('barcode')
    action  = data.get('action')
    amount  = data.get('amount', 1)

    if not barcode or not action:
        return jsonify({'error': 'Mangler stregkode eller handling'}), 400

    if action not in ('scan_in', 'scan_out'):
        return jsonify({'error': 'Handling skal være scan_in eller scan_out'}), 400

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()

    if product is None:
        conn.close()
        return jsonify({'error': f'Intet produkt fundet for stregkode {barcode}'}), 404

    # Calculate new stock
    if action == 'scan_in':
        new_stock = product['stock'] + amount
    elif action == 'scan_out':
        if product['stock'] < amount:
            conn.close()
            return jsonify({'error': 'Ikke nok på lager'}), 400
        new_stock = product['stock'] - amount

    # Update stock in database
    conn.execute(
        "UPDATE products SET stock = ? WHERE barcode = ?",
        (new_stock, barcode)
    )

    # Log the change
    change = amount if action == 'scan_in' else -amount
    conn.execute(
        "INSERT INTO stock_log (product_id, change, action) VALUES (?, ?, ?)",
        (product['id'], change, action)
    )

    conn.commit()
    conn.close()

    # Calculate 40% discount price
    normal_price   = float(product['normal_price'])
    discount_price = round(normal_price * 0.60, 2)

    return jsonify({
        'message': 'Datovare oprettet',
        'barcode': product['barcode'],
        'name': product['name'],
        'normal_price': normal_price,
        'discount_price': discount_price,
        'new_stock': new_stock,
        'action': action
    }), 200


# ── API routes ────────────────────────────────────────────────

@app.route('/api/products')
def api_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])


@app.route('/api/product/<int:product_id>')
def api_product(product_id):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    conn.close()
    if not product:
        return jsonify({'error': 'Produkt ikke fundet'}), 404
    return jsonify(dict(product))


@app.route('/api/product/barcode/<barcode>')
def api_product_by_barcode(barcode):
    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()
    conn.close()
    if not product:
        return jsonify({'error': 'Produkt ikke fundet'}), 404
    return jsonify(dict(product))


# ── Profile route ─────────────────────────────────────────────

@app.route('/profile')
def profile():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    conn = get_db_connection()
    purchases = conn.execute(
        """SELECT purchases.*, products.name as product_name
           FROM purchases
           JOIN products ON purchases.product_id = products.id
           WHERE purchases.customer_id = ?
           ORDER BY purchases.purchase_date DESC
           LIMIT 20""",
        (current_user['id'],)
    ).fetchall()
    conn.close()

    return render_template('profile.html', user=current_user, purchases=purchases)


# ── Create tables and run ─────────────────────────────────────

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)