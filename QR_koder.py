
import qrcode

members = [
    "Lukas"
]

for member in members:

    img = qrcode.make(member)

    img.save(f"{member}.png")

print("QR koder oprettet")