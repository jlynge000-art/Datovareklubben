# /home/pi/datovare/scanner_daemon.py
import requests
from evdev import InputDevice, categorize, ecodes, list_devices
from printer import print_product_label   # lokal - printer er på raspen

SERVER = "http://192.168.0.14:5000"   # <-- Udskift med relevant ip-adresse

KEYMAP = {f"KEY_{d}": d for d in "0123456789"}
KEYMAP.update({f"KEY_{c}": c.lower() for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"})
KEYMAP.update({"KEY_MINUS": "-", "KEY_DOT": ".", "KEY_SPACE": " "})
SHIFT_KEYS = {"KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"}

def find_scanner(name_hint="barcode"):
    for path in list_devices():
        dev = InputDevice(path)
        if name_hint.lower() in dev.name.lower():
            return dev
    return None

def handle(barcode):

    barcode = barcode.strip()

    print("Sender stregkode til API:", repr(barcode))#indsat
    
    try:
        r = requests.post(f"{SERVER}/scan",
                          json={"barcode": barcode}, timeout=10)
    except requests.RequestException as e:
        print(f"[{barcode}] kunne ikke nå serveren: {e}")
        return

    if r.status_code == 404:
        print(f"[{barcode}] ikke fundet i databasen"); return
    if not r.ok:
        print(f"[{barcode}] HTTP {r.status_code}: {r.text}"); return

    p = r.json()
    print(f"[{barcode}] {p['name']} – "
          f"{p['normal_price']} → {p['discount_price']} kr "
    )

    try:
        print_product_label(p)
        print("Etiket printet.")
    except Exception as e:
        print(f"Print fejlede: {e}")

def main():
    dev = find_scanner("WCM") #WCM er navnet for vores scanner
    if dev is None:
        print("Scanner ikke fundet. Tilgængelige enheder:")
        for p in list_devices():
            print(f"  {p}  ->  {InputDevice(p).name}")
        return

    print(f"Lytter på: {dev.name} ({dev.path})")
    dev.grab()
    buf, shift = "", False
    for ev in dev.read_loop():
        if ev.type != ecodes.EV_KEY:
            continue
        k = categorize(ev)
        if k.keycode in SHIFT_KEYS:
            shift = (k.keystate != 0); continue
        if k.keystate != k.key_down:
            continue
        if k.keycode == "KEY_ENTER":
            if buf:
                handle(buf); buf = ""
        else:
            ch = KEYMAP.get(k.keycode, "")
            buf += ch.upper() if shift and ch.isalpha() else ch

if __name__ == "__main__":
    main()