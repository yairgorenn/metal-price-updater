"""
Metal Price Updater
-------------------
Reads official LME Copper & Aluminium prices via browser automation,
converts USD→EUR using Bank of Israel rates,
and updates Ateka Google Sheet.

Designed for unattended daily execution on Windows VM (Azure).

Author: Yair Goren
"""

import subprocess
import time
import re
import read_usd_eru as ur
import update_price_ingooglesheet as upg
import datetime
import os,sys
import requests
import json
from push_prices_to_railway import push_metal_price
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOT_KEY_FILE_COPPER = os.path.join(BASE_DIR, "readcopper.ahk")
HOT_KEY_FILE_ALUMINIUM = os.path.join(BASE_DIR, "readaluminium.ahk")

COPPER_FILE_NAME = os.path.join(BASE_DIR, "copper_price.txt")
ALUMINIUM_FILE_NAME = os.path.join(BASE_DIR, "aluminium_price.txt")

LAST_PRICE_FILE = os.path.join(BASE_DIR, "last_prices.json")

AUTO_HOT_KEY_APP = os.getenv("AUTOHOTKEY_PATH")
if not AUTO_HOT_KEY_APP:
    raise RuntimeError("AUTOHOTKEY_PATH not set")

ERU_SYMBOL = "\u20AC"
SHEKEL_SYMBOL = "\u20AA"
COPPER_TEXT_BEFORE_PRICE ="LME Copper"
ALUMINIUM_TEXT_BEFORE_PRICE = "LME Aluminium"
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")

if not PUSHBULLET_TOKEN:
    raise RuntimeError("PUSHBULLET_TOKEN environment variable not set")

SOFT_LIMIT = 0.07    # 7%
HARD_LIMIT = 0.20    # 20%

COPPER_RANGE = (3000, 19000)
ALUMINIUM_RANGE = (1000, 8000)

def get_log_path():
    """Create dir for log"""
    now = datetime.datetime.now()
    log_dir = os.path.join(BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return fr"{log_dir}\run_{now.year}-{now.month:02d}.log"


def log(msg):
    """log to file"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(get_log_path(), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def load_last_prices():
    if not os.path.exists(LAST_PRICE_FILE):
        log("No last_prices.json found – first run")
        return None
    try:
        with open(LAST_PRICE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"FAILED to read last_prices.json: {e}")
        return None

def save_last_prices(copper_eur, aluminium_eur):
    data = {
        "date": datetime.date.today().isoformat(),
        "copper_eur": copper_eur,
        "aluminium_eur": aluminium_eur
    }
    with open(LAST_PRICE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log("last_prices.json updated successfully")


def validate_price(new, old, metal_name, valid_range):
    if not (valid_range[0] <= new <= valid_range[1]):
        raise RuntimeError(
            f"{metal_name} price {new} out of absolute range {valid_range}"
        )

    if old is None:
        return "OK"

    change = abs(new - old) / old

    if change > HARD_LIMIT:
        raise RuntimeError(
            f"{metal_name} price jump {change*100:.1f}% exceeds HARD limit"
        )

    if change > SOFT_LIMIT:
        send_pushbullet(
            title=f"⚠ {metal_name} price unusual change",
            body=f"Change: {change*100:.1f}% (price accepted)"
        )
        return "SOFT"

    return "OK"

def remove_old_file(path):
    """remove the old text file"""
    if os.path.exists(path):
        try:
            os.remove(path)
            log(f"Old file removed: {path}")
        except Exception as e:
            log(f"FAILED to remove old file {path}: {e}")
            raise


def send_pushbullet(title, body):
    """ send alarm pb to yair goren"""
    token = os.getenv("PUSHBULLET_TOKEN")
    if not token:
        log("Pushbullet token missing")
        return
    try:
        url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": token,
            "Content-Type": "application/json"
        }
        data = {
            "type": "note",
            "title": title,
            "body": body
        }
        r = requests.post(url, json=data, headers=headers, timeout=10)
        if r.status_code != 200:
            log(f"Pushbullet FAILED: {r.status_code} {r.text}")
    except Exception as e:
        log(f"Pushbullet EXCEPTION: {e}")


def wait_for_file(path, timeout=120):
    """wait until auto hot key create and close the text file with the data"""
    log(f"Waiting for file: {path}")
    start = time.time()
    while time.time() - start < timeout:
        try:
            if os.path.exists(path):
                size = os.path.getsize(path)
                if size > 100:
                    log(f"File ready: size={size}")
                    return True
        except Exception as e:
            log(f"wait_for_file error: {e}")
        time.sleep(0.5)
    log("wait_for_file TIMEOUT")
    return False


def extract_row_price(file_path, search_text: str):
    """ get the metal price from the text file this could be changed
    according to the LME format"""
    """
    Assumes LME page structure:
    <Metal Name>
    <Price Line starting with number>
    """

    try:
        with open(file_path, encoding="utf-8", errors="ignore") as fh:
            lines = [line.strip() for line in fh if line.strip()]

        for i in range(len(lines) - 1):
            if lines[i] == search_text:
                next_line = lines[i + 1]
                if re.match(r"^\d+(\.\d+)?", next_line):
                    price_str = next_line.split()[0]
                    return float(price_str)
        raise ValueError(f"Price not found for {search_text}")

    except Exception as e:
        log(f"Failed to extract LME price | file={file_path} | search={search_text} | error={e}")
        raise


def run_auto_hot_key(metal_file_name):
    """ run auto hot key file. the file open the site in firefox select all copy the text
    and save it as text file"""
    log(f"Running AutoHotkey: {metal_file_name}")
    try:
        result = subprocess.run(
       [AUTO_HOT_KEY_APP, os.path.join(BASE_DIR, metal_file_name)],
        timeout=180
        )
        log(f"AutoHotkey finished, returncode={result.returncode}")
        if result.returncode != 0:
            raise RuntimeError("AutoHotkey returned non-zero code")
        time.sleep(2)
        return True
    except Exception as e:
        log(f"AutoHotkey FAILED: {e}")
        raise


def get_price(auto_keyfile: str, text_file: str, search_text: str):
    """find the price proces"""
    full_path =  os.path.join(BASE_DIR, text_file)
    remove_old_file(full_path)
    run_auto_hot_key(auto_keyfile)

    if not wait_for_file(full_path):
        raise RuntimeError(f"File not created: {full_path}")

    price = extract_row_price(full_path, search_text)
    # הגנה נוספת (paranoid, אבל נכון)
    if price is None:
        raise RuntimeError(f"Price is None for {search_text}")
    return price


def read_metal_prices():
    # ---------- 1. Load last known prices (for sanity validation only)
    last = load_last_prices() if isinstance(load_last_prices(), dict) else {}

    # ---------- 2. Fetch FX rates
    usd_to_eur, eur_to_ils = ur.get_usd_eru()

    if not (0.5 < usd_to_eur < 1.5):
        raise ValueError(f"usd_to_eur לא סביר: {usd_to_eur}")

    if not (3.0 < eur_to_ils < 6.0):
        raise ValueError(f"eur_to_ils לא סביר: {eur_to_ils}")

    log(f"FX rates: USD→EUR={usd_to_eur}, EUR→ILS={eur_to_ils}")

    # ---------- 3. Fetch LME prices (USD / ton)
    copper_usd = get_price(
        HOT_KEY_FILE_COPPER,
        COPPER_FILE_NAME,
        COPPER_TEXT_BEFORE_PRICE
    )

    log(f"LME Copper: {copper_usd:.2f} USD/ton")

    time.sleep(15)

    aluminium_usd = get_price(
        HOT_KEY_FILE_ALUMINIUM,
        ALUMINIUM_FILE_NAME,
        ALUMINIUM_TEXT_BEFORE_PRICE
    )

    log(f"LME Aluminium: {aluminium_usd:.2f} USD/ton")

    # ---------- 4. Convert to EUR / ton (NO ROUNDING)
    copper_eur = copper_usd * usd_to_eur
    aluminium_eur = aluminium_usd * usd_to_eur

    # ---------- 5. Sanity validation vs last values
    validate_price(
        copper_eur,
        last.get("copper_eur"),
        "Copper",
        COPPER_RANGE
    )

    validate_price(
        aluminium_eur,
        last.get("aluminium_eur"),
        "Aluminium",
        ALUMINIUM_RANGE
    )

    # ---------- 6. Persist to Railway (source of truth)
    today_iso = date.today().isoformat()

    push_metal_price("CU", copper_eur, eur_to_ils, today_iso)
    push_metal_price("AL", aluminium_eur, eur_to_ils, today_iso)
    log("Railway ingest completed successfully")

    # ---------- 7. Update Google Sheet (presentation layer)
    if not upg.up_date_price(
        round(copper_eur, 2),
        round(aluminium_eur, 2),
        eur_to_ils
    ):
        raise RuntimeError("Google Sheet update failed")

    # ---------- 8. Persist last known good values (local safety net)
    save_last_prices(copper_eur, aluminium_eur)

    log("Metal prices updated successfully")

    return True


def main():
    log("=" * 60)
    log("START RUN")
    log(f"Python version: {sys.version}")
    log(f"Working dir: {os.getcwd()}")
    log(f"Using copper search text: {COPPER_TEXT_BEFORE_PRICE}")
    log(f"Using aluminium search text: {ALUMINIUM_TEXT_BEFORE_PRICE}")

    try:
        success = read_metal_prices()

        if not success:
            raise RuntimeError("Update returned False")

        log("UPDATE SUCCESS")

    except Exception as e:
        error_msg = f"UPDATE FAILED: {e}"
        log(error_msg)

        # 🔴 תמיד שולח Pushbullet
        send_pushbullet(
            title="❌ Copper Price Update FAILED",
            body=error_msg
        )

        raise  # שומר exit code != 0

    finally:
        log("END RUN")
        log("=" * 60)


if __name__ == "__main__":
    main()
