# /home/pi/datovare/printer.py
import logging
logging.getLogger("brother_ql.devicedependent").setLevel(logging.ERROR)

from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from brother_ql.raster import BrotherQLRaster
from PIL import Image, ImageDraw, ImageFont

PRINTER_MODEL      = "QL-570"
PRINTER_BACKEND    = "pyusb"
PRINTER_IDENTIFIER = "usb://0x04f9:0x2028"
LABEL_SIZE         = "62"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _ean13_image(barcode_str, target_width=600):
    """Render a scannable EAN-13 barcode as a PIL image."""
    ean = barcode.get("ean13", barcode_str, writer=ImageWriter())
    buf = BytesIO()
    ean.write(buf, options={"module_height": 15.0, "font_size": 10, "quiet_zone": 2.0})
    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    ratio = target_width / img.width
    return img.resize((target_width, int(img.height * ratio)), Image.LANCZOS)


def render_label(product):
    name        = str(product.get("name", "Unavngivet"))
    category    = str(product.get("category", ""))
    normal      = float(product.get("normal_price", 0))
    discount    = float(product.get("discount_price", 0))
    barcode_str = str(product.get("barcode", ""))
    pct_off     = round((1 - discount / normal) * 100) if normal else 0

    label = Image.new("RGB", (696, 500), "white")
    draw  = ImageDraw.Draw(label)

    f_big   = ImageFont.truetype(FONT_BOLD, 44)
    f_huge  = ImageFont.truetype(FONT_BOLD, 64)
    f_med   = ImageFont.truetype(FONT_REG,  28)
    

    # --- Header: name (left) ---
    draw.text((20, 10), name, fill="black", font=f_big)

    # --- Category (left) + stock badge (right) on the same line ---
    draw.text((20, 65), category, fill="black", font=f_med)

    

    # --- Før price with strikethrough ---
    before_txt = f"Før: {normal:.2f} kr"
    draw.text((20, 115), before_txt, fill="black", font=f_med)
    bbox = draw.textbbox((20, 115), before_txt, font=f_med)
    mid_y = (bbox[1] + bbox[3]) // 2
    draw.line((bbox[0], mid_y, bbox[2], mid_y), fill="black", width=3)

    # --- Big discount price ---
    draw.text((20, 155), f"NU {discount:.2f} kr  (-{pct_off}%)",
              fill="black", font=f_huge)

    # --- Scannable EAN-13 at the bottom ---
    if len(barcode_str) == 13 and barcode_str.isdigit():
        bc_img = _ean13_image(barcode_str)
        label.paste(bc_img, ((696 - bc_img.width) // 2, 240))
    else:
        draw.text((20, 250), barcode_str, fill="black", font=f_med)

    return label


def print_product_label(product):
    img = render_label(product)
    qlr = BrotherQLRaster(PRINTER_MODEL)
    qlr.exception_on_warning = True
    instructions = convert(
        qlr=qlr, images=[img], label=LABEL_SIZE,
        rotate="auto", threshold=70.0, dither=False, compress=False,
    )
    send(instructions=instructions,
         printer_identifier=PRINTER_IDENTIFIER,
         backend_identifier=PRINTER_BACKEND,
         blocking=True)


if __name__ == "__main__":
    print_product_label({
        "name":           "Spegepølse",
        "category":       "Pålæg",
        "normal_price":   34.95,
        "discount_price": 20.97,
        "barcode":        "2700000000014",
    })
    print("Test-etiket sendt.")