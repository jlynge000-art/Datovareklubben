from flask import Flask, jsonify, send_from_directory
import sqlite3

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return "Datovare API virker"

@app.route("/products")
def get_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()

    product_list = []
    for product in products:
        product_list.append(dict(product))

    return jsonify(product_list)

@app.route("/product/<int:product_id>")
def get_product(product_id):

    conn = get_db_connection()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    conn.close()

    if product is None:
        return {"error": "Produkt ikke fundet"}, 404

    product_dict = dict(product)

    image_filename = product_dict["image_path"].split("/")[-1]

    html = f"""
    <h1>{product_dict['name']}</h1>

    <p><b>Pris:</b> {product_dict['normal_price']} kr</p>

    <p><b>Kategori:</b> {product_dict['category']}</p>

    <img src="/images/{image_filename}" width="300">
    """

    return html

@app.route("/product/barcode/<barcode>")
def get_product_by_barcode(barcode):
    conn = get_db_connection()

    product = conn.execute(
        "SELECT * FROM products WHERE barcode = ?",
        (barcode,)
    ).fetchone()

    conn.close()

    if product is None:
        return {"error": "Produkt ikke fundet"}, 404

    return jsonify(dict(product))

@app.route("/images/<filename>")
def get_image(filename):
    return send_from_directory("Databasebillederne", filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)