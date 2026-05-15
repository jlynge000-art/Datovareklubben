import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

products = [
    (None, "Spegepølse", 34.95, "Databasebillederne/spegepoelse.png", "Pålæg"),
    (None, "Rugbrød", 24.95, "Databasebillederne/rugbroed.png", "Brød"),
    (None, "Rejesalat", 29.95, "Databasebillederne/rejesalat.png", "Pålægssalater"),
    (None, "Pastasalat", 34.95, "Databasebillederne/pastasalat.png", "Færdigretter"),
    (None, "Russisk salat", 24.95, "Databasebillederne/russisk_salat.png", "Pålægssalater")
]

cursor.executemany("""
INSERT INTO products (
    barcode,
    name,
    normal_price,
    image_path,
    category
)
VALUES (?, ?, ?, ?, ?)
""", products)

conn.commit()

print("Produktliste oprettet")

conn.close()