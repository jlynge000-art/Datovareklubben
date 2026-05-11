import sqlite3

conn = sqlite3.connect("database.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barcode TEXT,
    name TEXT,
    normal_price REAL,
    discount_price REAL
)
""")

conn.commit()

print("Database og tabel oprettet")

conn.close()