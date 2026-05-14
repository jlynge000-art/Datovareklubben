"""Print a barcode label on the Brother QL-570 over USB."""
import logging
logging.getLogger("brother_ql.devicedependent").setLevel(logging.ERROR)

from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from PIL import Image, ImageDraw, ImageFont

PRINTER = "usb://0x04f9:0x2028"
LABEL = "62"

PRODUCT_NAME = "Coffee Beans"
PRODUCT_ID = "123456789012"
PRICE = 12.99


def build_label_image(name, product_id, price):
    ean = barcode.get('ean13', product_id, writer=ImageWriter())
    buffer = BytesIO()
    ean.write(buffer, options={'module_height': 15.0, 'font_size': 10, 'quiet_zone': 2.0})
    buffer.seek(0)
    bc_img = Image.open(buffer).convert("RGB")

    target_width = 600
    ratio = target_width / bc_img.width
    bc_img = bc_img.resize((target_width, int(bc_img.height * ratio)), Image.LANCZOS)

    label = Image.new("RGB", (696, 250), "white")
    draw = ImageDraw.Draw(label)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    draw.text((20, 10), name, fill="black", font=ImageFont.truetype(font_path, 36))
    draw.text((20, 55), f"${price:.2f}", fill="black", font=ImageFont.truetype(font_path, 44))
    label.paste(bc_img, ((696 - bc_img.width) // 2, 115))
    return label


def print_barcode(name, product_id, price):
    img = build_label_image(name, product_id, price)
    qlr = BrotherQLRaster("QL-570")
    qlr.exception_on_warning = True
    instructions = convert(
        qlr=qlr,
        images=[img],
        label=LABEL,
        rotate="auto",
        threshold=70.0,
        dither=False,
        compress=False,
    )
    send(
        instructions=instructions,
        printer_identifier=PRINTER,
        backend_identifier="pyusb",
        blocking=True,
    )
    print(f"Printed: {name} - ${price:.2f}")


if __name__ == "__main__":
    print_barcode(PRODUCT_NAME, PRODUCT_ID, PRICE)
