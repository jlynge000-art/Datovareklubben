import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

products = [
    ("27000000000014", "Spegepølse", 34.95, "Databasebillederne/spegepoelse.png", "Pålæg"),
    ("27000000000021", "Rugbrød", 24.95, "Databasebillederne/rugbroed.png", "Brød"),
    ("27000000000038", "Rejesalat", 29.95, "Databasebillederne/rejesalat.png", "Pålægssalater"),
    ("27000000000045", "Pastasalat", 34.95, "Databasebillederne/pastasalat.png", "Færdigretter"),
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