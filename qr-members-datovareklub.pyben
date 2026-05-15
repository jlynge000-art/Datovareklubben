"""Print QR-code member labels on the Brother QL-570 over USB."""
import logging
logging.getLogger("brother_ql.devicedependent").setLevel(logging.ERROR)

from dataclasses import dataclass

import qrcode
from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from PIL import Image, ImageDraw, ImageFont

PRINTER = "usb://0x04f9:0x2028"
LABEL = "62"
LABEL_WIDTH = 696
LABEL_HEIGHT = 560
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TITLE_TEXT = "Datovareklubben"


@dataclass
class Member:
    name: str
    member_id: str


# --- Edit the four members here -------------------------------------------
MEMBERS = [
    Member("Alice Andersen", "M001"),
    Member("Bob Berg",       "M002"),
    Member("Cara Carlsen",   "M003"),
    Member("Dan Dahl",       "M004"),
]
# --------------------------------------------------------------------------


def build_qr_image(data, size):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.LANCZOS)


def draw_centered_text(draw, text, y, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    draw.text(((LABEL_WIDTH - width) // 2, y), text, fill="black", font=font)


def build_member_label(member):
    label = Image.new("RGB", (LABEL_WIDTH, LABEL_HEIGHT), "white")
    draw = ImageDraw.Draw(label)

    title_font = ImageFont.truetype(FONT_PATH, 56)
    name_font  = ImageFont.truetype(FONT_PATH, 48)
    id_font    = ImageFont.truetype(FONT_PATH, 40)

    # Title at top, centered
    draw_centered_text(draw, TITLE_TEXT, 15, title_font)

    # Thin separator under the title
    draw.line([(40, 90), (LABEL_WIDTH - 40, 90)], fill="black", width=2)

    # QR code centered below the title
    qr_size = 320
    qr_img = build_qr_image(f"{member.member_id}|{member.name}", qr_size)
    label.paste(qr_img, ((LABEL_WIDTH - qr_size) // 2, 105))

    # Name and ID centered below the QR code
    draw_centered_text(draw, member.name, 440, name_font)
    draw_centered_text(draw, f"ID: {member.member_id}", 500, id_font)

    return label


def print_labels(members):
    images = [build_member_label(m) for m in members]
    qlr = BrotherQLRaster("QL-570")
    qlr.exception_on_warning = True
    instructions = convert(
        qlr=qlr,
        images=images,
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
    for m in members:
        print(f"Printed: {m.name} ({m.member_id})")


if __name__ == "__main__":
    print_labels(MEMBERS)
