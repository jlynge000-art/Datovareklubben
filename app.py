from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ── App setup ─────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)


# ── Database models ───────────────────────────────────────────
# Each class is one table in the database

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    barcode  = db.Column(db.String(50), unique=True, nullable=False)
    stock    = db.Column(db.Integer, default=0)

class StockLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    change     = db.Column(db.Integer, nullable=False)
    action     = db.Column(db.String(20), nullable=False)
    timestamp  = db.Column(db.DateTime, server_default=db.func.now())


# ── Helper function ───────────────────────────────────────────
# Call this at the top of any route that requires login
# Returns the logged in User object, or None if not logged in

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None


# ── Auth routes ───────────────────────────────────────────────

@app.route('/')
def index():
    # Just redirect the front page to login
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Brugernavnet er allerede taget.')
            return redirect(url_for('register'))

        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('E-mail er allerede registreret.')
            return redirect(url_for('register'))

        # Hash the password so it is not stored as plain text
        hashed_password = generate_password_hash(password)

        # Create the new user and save to database
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Konto oprettet! Log venligst ind.')
        return redirect(url_for('login'))

    # GET request — just show the register form
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Look up the user in the database
        user = User.query.filter_by(username=username).first()

        # Check user exists and password matches the stored hash
        if not user or not check_password_hash(user.password, password):
            flash('Forkert brugernavn eller adgangskode.')
            return redirect(url_for('login'))

        # Save user id in the session so we know who is logged in
        session['user_id'] = user.id
        return redirect(url_for('products'))

    # GET request — just show the login form
    return render_template('login.html')


@app.route('/logout')
def logout():
    # Remove the user from the session
    session.pop('user_id', None)
    return redirect(url_for('login'))


# ── Product routes ────────────────────────────────────────────

@app.route('/products')
def products():
    # Redirect to login if not logged in
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    # Get all products from the database
    all_products = Product.query.all()
    return render_template('products.html', products=all_products, user=current_user)


@app.route('/scan', methods=['POST'])
def scan():
    # This route is called by the Raspberry Pi, not the browser
    data = request.get_json()

    if not data:
        return {'error': 'No data received'}, 400

    barcode = data.get('barcode')
    action  = data.get('action')
    amount  = data.get('amount', 1)

    if not barcode or not action:
        return {'error': 'Missing barcode or action'}, 400

    if action not in ('scan_in', 'scan_out'):
        return {'error': 'Action must be scan_in or scan_out'}, 400

    # Find the product with this barcode
    product = Product.query.filter_by(barcode=barcode).first()

    if not product:
        return {'error': f'No product found for barcode {barcode}'}, 404

    # Update the stock number
    if action == 'scan_in':
        product.stock += amount
    elif action == 'scan_out':
        if product.stock < amount:
            return {'error': 'Not enough stock'}, 400
        product.stock -= amount

    # Save a log entry so we have a history of changes
    log = StockLog(
        product_id=product.id,
        change=amount if action == 'scan_in' else -amount,
        action=action
    )
    db.session.add(log)
    db.session.commit()

    return {
        'success': True,
        'product': product.name,
        'new_stock': product.stock
    }, 200


# ── User profile route ────────────────────────────────────────

@app.route('/profile')
def profile():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login'))

    # Get the last 20 stock changes as history
    logs = StockLog.query.order_by(StockLog.timestamp.desc()).limit(20).all()
    return render_template('profile.html', user=current_user, logs=logs)


# ── Create tables and run ─────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)