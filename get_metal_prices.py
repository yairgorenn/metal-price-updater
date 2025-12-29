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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOT_KEY_FILE_COPPER = os.path.join(BASE_DIR, "readcopper.ahk")
HOT_KEY_FILE_ALUMINIUM = os.path.join(BASE_DIR, "readaluminium.ahk")

COPPER_FILE_NAME = os.path.join(BASE_DIR, "copper_price.txt")
ALUMINIUM_FILE_NAME = os.path.join(BASE_DIR, "aluminium_price.txt")

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


def get_log_path():
    """Create dir for log"""
    now = datetime.datetime.now()
    log_dir = os.path.join(BASE_DIR, "\logs")
    os.makedirs(log_dir, exist_ok=True)
    return fr"{log_dir}\run_{now.year}-{now.month:02d}.log"


def log(msg):
    """log to file"""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(get_log_path(), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


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


def wait_for_file(path, timeout=40):
    """wait until auto hot key create and close the text file with the data"""
    log(f"Waiting for file: {path}")
    start = time.time()
    while time.time() - start < timeout:
        try:
            if os.path.exists(path):
                size = os.path.getsize(path)
                if size > 0:
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
            timeout=30
        )
        log(f"AutoHotkey finished, returncode={result.returncode}")
        if result.returncode != 0:
            raise RuntimeError("AutoHotkey returned non-zero code")
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
    # read from israel central bank
    usd_eru, eru_shekel = ur.get_usd_eru()

    #get copper
    copper_price = get_price(HOT_KEY_FILE_COPPER,COPPER_FILE_NAME,COPPER_TEXT_BEFORE_PRICE)
    log(f"The copper price from LME Cash is {copper_price:.2f} $/ton")
    copper_price_eru = round(copper_price*usd_eru,2)
    log(f"The copper price from LME Cash is {copper_price_eru:.2f} {ERU_SYMBOL}/ton")

    #get aluminium
    aluminium_price = get_price(HOT_KEY_FILE_ALUMINIUM,ALUMINIUM_FILE_NAME,ALUMINIUM_TEXT_BEFORE_PRICE)
    log(f"The aluminium price from LME Cash is {aluminium_price:.2f} $/ton")
    aluminium_price_eru = round(aluminium_price*usd_eru,2)
    log(f"The aluminium price from LME Cash is {aluminium_price_eru:.2f} {ERU_SYMBOL}/ton")
    log(f'Eru price: {eru_shekel}{SHEKEL_SYMBOL}')
    log ("Up dating the price on ateka drive google sheet cable...")
    try:
        if upg.up_date_price(copper_price_eru,aluminium_price_eru,eru_shekel):
            return True
        else:
            return False
    except Exception as e:
        raise RuntimeError(f"Google Sheet update failed: {e}")


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
