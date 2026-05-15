import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

products = [
    ("2700000000001", "Spegepølse", 34.95, "Databasebillederne/spegepoelse.png", "Pålæg"),
    ("2700000000002", "Rugbrød", 24.95, "Databasebillederne/rugbroed.png", "Brød"),
    ("2700000000003", "Rejesalat", 29.95, "Databasebillederne/rejesalat.png", "Pålægssalater"),
    ("2700000000004", "Pastasalat", 34.95, "Databasebillederne/pastasalat.png", "Færdigretter"),
    ("2700000000005", "Russisk salat", 24.95, "Databasebillederne/russisk_salat.png", "Pålægssalater")
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