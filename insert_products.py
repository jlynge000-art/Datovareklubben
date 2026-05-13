import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

products = [
    (None, "Spegepølse", 34.95, "Databasebillederne/Spegepølse Image 12. maj 2026, 16.33.50.png", "Pålæg"),
    (None, "Rugbrød", 24.95, "Databasebillederne/Rugbrød Image 12. maj 2026, 16.34.11.png", "Brød"),
    (None, "Rejesalat", 29.95, "Databasebillederne/Rejesalat Image 12. maj 2026, 17.43.34.png", "Pålægssalater"),
    (None, "Pastasalat", 34.95, "Databasebillederne/Pastasalat Image 12. maj 2026, 18.00.18.png", "Færdigretter"),
    (None, "Russisk salat", 24.95, "Databasebillederne/Russisksalat Image 12. maj 2026, 18.22.12.png", "Pålægssalater")
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