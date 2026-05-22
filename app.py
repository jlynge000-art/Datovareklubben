from flask import Flask, render_template, redirect, url_for, request, flash, session, send_from_directory, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import sqlite3
import os
import qrcode
import uuid
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-later'


# ── Database connection ───────────────────────────────────────

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ── Create tables og seed ────────────────────────────────────
def create_tables():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT,
            normal_price REAL,
            discount_price REAL,
            image_path TEXT,
            category TEXT,
            stock INTEGER DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_code TEXT UNIQUE,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            email_verified INTEGER DEFAULT 0,
            verification_token TEXT,
            points INTEGER DEFAULT 0,
            qr_code_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            purchase_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            change INTEGER NOT NULL,
            action TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    existing = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]

    if existing == 0:
        products = [
            ("2700000000014", "Spegepølse",    34.95, round(34.95 * 0.60, 2), "Databasebillederne/spegepoelse.png",   "Pålæg",         5),
            ("2700000000021", "Rugbrød",       24.95, round(24.95 * 0.60, 2), "Databasebillederne/rugbroed.png",      "Brød",          3),
            ("2700000000038", "Rejesalat",     29.95, round(29.95 * 0.60, 2), "Databasebillederne/rejesalat.png",     "Pålægssalater", 2),
            ("2700000000045", "Pastasalat",    34.95, round(34.95 * 0.60, 2), "Databasebillederne/pastasalat.png",    "Færdigretter",  1),
            ("2700000000052", "Russisk salat", 24.95, round(24.95 * 0.60, 2), "Databasebillederne/russisk_salat.png", "Pålægssalater", 1),
        ]
        conn.executemany("""
            INSERT OR IGNORE INTO products
                (barcode, name, normal_price, discount_price, image_path, category, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, products)
        print("Produkter tilføjet")

    conn.commit()
    conn.close()
    print("Database og tabeller oprettet")

# ── Helper function ───────────────────────────────────────────

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
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
        name     = request.form.get('name')
        email    = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()

        # Check if email already exists
        existing_email = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if existing_email:
            conn.close()
            flash('E-mail er allerede registreret. Prøv at logge ind.')
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Generate a unique 8 character member code
        member_code = str(uuid.uuid4())[:8].upper()

        # Generate and save the QR code image
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(member_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image to static/qrcodes/
        os.makedirs(os.path.join('static', 'qrcodes'), exist_ok=True)
        qr_filename = f"{member_code}.png"
        qr_path     = os.path.join('static', 'qrcodes', qr_filename)
        img.save(qr_path)

        # Insert the new customer into the database
        conn.execute(
            """INSERT INTO users
               (name, email, password_hash, member_code, qr_code_path)
               VALUES (?, ?, ?, ?, ?)""",
            (name, email, hashed_password, member_code, qr_path)
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
            "SELECT * FROM users WHERE email = ?", (email,)
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

    # Get full purchase history with product details
    purchases = conn.execute(
        """SELECT
               purchases.id,
               purchases.quantity,
               purchases.total_price,
               purchases.purchase_date,
               products.name as product_name,
               products.normal_price,
               products.discount_price,
               products.image_path
           FROM purchases
           JOIN products ON purchases.product_id = products.id
           WHERE purchases.customer_id = ?
           ORDER BY purchases.purchase_date DESC""",
        (current_user['id'],)
    ).fetchall()

    # Calculate total spent
    total_spent = sum(p['total_price'] for p in purchases)

    conn.close()

    return render_template(
        'profile.html',
        user=current_user,
        purchases=purchases,
        total_spent=round(total_spent, 2)
    )

# ── Salg routes ───────────────────────────────────────────────

@app.route('/open_sale', methods=['POST'])
def open_sale():
    data        = request.get_json()
    member_code = data.get('member_code')

    if not member_code:
        return jsonify({'error': 'Ingen medlemskode modtaget'}), 400

    conn = get_db_connection()
    customer = conn.execute(
        "SELECT * FROM users WHERE member_code = ?", (member_code,)
    ).fetchone()
    conn.close()

    if not customer:
        return jsonify({'error': 'Kunde ikke fundet'}), 404

    with open('active_sale.txt', 'w') as f:
        f.write(str(customer['id']))

    return jsonify({
        'success': True,
        'message': f"Salg åbnet for {customer['name']}",
        'customer_id': customer['id'],
        'customer_name': customer['name']
    }), 200


@app.route('/purchase', methods=['POST'])
def purchase():
    data    = request.get_json()
    barcode = data.get('barcode')
    amount  = data.get('amount', 1)

    if not barcode:
        return jsonify({'error': 'Ingen stregkode modtaget'}), 400

    try:
        with open('active_sale.txt', 'r') as f:
            customer_id = int(f.read().strip())
    except FileNotFoundError:
        return jsonify({'error': 'Intet aktivt salg — scan medlemskort først'}), 400

    conn = get_db_connection()
    product = conn.execute(
        "SELECT * FROM products WHERE barcode = ?", (barcode,)
    ).fetchone()

    if not product:
        conn.close()
        return jsonify({'error': f'Produkt ikke fundet for stregkode {barcode}'}), 404

    if product['stock'] < amount:
        conn.close()
        return jsonify({'error': 'Ikke nok på lager'}), 400

    total_price = round(product['discount_price'] * amount, 2)

    conn.execute(
        """INSERT INTO purchases (customer_id, product_id, quantity, total_price, purchase_date)
           VALUES (?, ?, ?, ?, ?)""",
        (customer_id, product['id'], amount, total_price,
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )

    new_stock = product['stock'] - amount
    conn.execute(
        "UPDATE products SET stock = ? WHERE barcode = ?",
        (new_stock, barcode)
    )

    conn.execute(
        "INSERT INTO stock_log (product_id, change, action) VALUES (?, ?, ?)",
        (product['id'], -amount, 'purchase')
    )

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'product': product['name'],
        'quantity': amount,
        'total_price': total_price,
        'new_stock': new_stock
    }), 200


@app.route('/close_sale', methods=['POST'])
def close_sale():
    try:
        os.remove('active_sale.txt')
    except FileNotFoundError:
        pass
    return jsonify({'success': True, 'message': 'Salg lukket'}), 200

# ── Create tables and run ─────────────────────────────────────
create_tables()

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)