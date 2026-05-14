"""Print a label using the Brother QL-570 over USB."""
import logging
logging.getLogger("brother_ql.devicedependent").setLevel(logging.ERROR)

from brother_ql.raster import BrotherQLRaster
from brother_ql.conversion import convert
from brother_ql.backends.helpers import send
from PIL import Image, ImageDraw, ImageFont

PRINTER = "usb://0x04f9:0x2028"
LABEL = "62"


def print_label(text: str):
    """Print a single-line text label."""
    img = Image.new("RGB", (696, 200), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60
    )
    draw.text((20, 60), text, fill="black", font=font)

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


if __name__ == "__main__":
    print_label("Hello world!")
