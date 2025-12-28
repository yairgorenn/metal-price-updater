import subprocess
import time
import re
import read_usd_eru as ur
import update_price_ingooglesheet as upg
import datetime
import os
import requests


RUNING_DIR = r"c:\COPPER_PRICE"
AUTO_HOT_KEY_APP = r"C:\Program Files\\AutoHotkey\AutoHotkey.exe"
HOT_KEY_FILE_COPPER = r"\readcopper.ahk"
HOT_KEY_FILE_ALUMINIUM = r"\readaluminium.ahk"
COPPER_FILE_NAME = r"\copper_price.txt"
ALUMINIUM_FILE_NAME = r"\aluminium_price.txt"
ERU_SYMBOL = "\u20AC"
SHEKEL_SYMBOL = "\u20AA"
COPPER_TEXT_BEFORE_PRICE ="LME Copper"
ALUMINIUM_TEXT_BEFORE_PRICE = "LME Aluminium"
PUSHBULLET_TOKEN = os.getenv("PUSHBULLET_TOKEN")

if not PUSHBULLET_TOKEN:
    raise RuntimeError("PUSHBULLET_TOKEN environment variable not set")

def get_log_path():
    now = datetime.datetime.now()
    log_dir = r"C:\COPPER_PRICE\logs"

    # יצירת תיקיית logs אם לא קיימת
    os.makedirs(log_dir, exist_ok=True)

    return fr"{log_dir}\run_{now.year}-{now.month:02d}.log"



def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(get_log_path(), "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def remove_old_file(path):
    if os.path.exists(path):
        try:
            os.remove(path)
            log(f"Old file removed: {path}")
        except Exception as e:
            log(f"FAILED to remove old file {path}: {e}")
            raise

def send_pushbullet(title, body):
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


def wait_for_file(path, timeout=20):
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
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as fh:
            lines = [line.strip() for line in fh if line.strip()]

        for i in range(len(lines) - 1):
            # תנאי 1: השורה מכילה את הטקסט המבוקש
            if lines[i] == search_text:
                next_line = lines[i + 1]

                # תנאי 2: השורה הבאה מתחילה במספר (מחיר)
                if re.match(r"^\d+(\.\d+)?", next_line):
                    price_str = next_line.split()[0]
                    return float(price_str)

        raise ValueError(f"Price not found for {search_text}")


    except Exception as e:

        log(f"Failed to extract LME price | file={file_path} | search={search_text} | error={e}")

        raise



def run_auto_hot_key(metal_file_name):
    log(f"Running AutoHotkey: {metal_file_name}")
    try:
        result = subprocess.run(
            [AUTO_HOT_KEY_APP, RUNING_DIR + metal_file_name],
            timeout=30
        )
        log(f"AutoHotkey finished, returncode={result.returncode}")
        if result.returncode != 0:
            raise RuntimeError("AutoHotkey returned non-zero code")
        return True
    except Exception as e:
        log(f"AutoHotkey FAILED: {e}")
        raise


def open_file_find_cash(file_path):
    """open the text file find the cash row return it and clos the file"""
    file_path = file_path
    try:
        fh = open(file_path)
        for row in fh:
            if row.startswith("Cash"):
                fh.close()
                return row
        raise
    except Exception as e:
        log(f"Failed to open file: {file_path}")
        log(f"Error: {e}")

        raise

def calculate_average(row):
    # find all numbers in current line
    # format XXXX.XX $
    line_number_list = re.findall('[0-9]+[.][0-9]+', row)
    if len(line_number_list) == 2:
        try:
            average =(float(line_number_list[0])+float(line_number_list[1]))/2.0
            return average
        except:
            raise


def get_average_price(auto_keyfile: str, text_file: str, search_text: str):
    full_path = RUNING_DIR + text_file

    remove_old_file(full_path)
    run_auto_hot_key(auto_keyfile)

    if not wait_for_file(full_path):
        raise RuntimeError(f"File not created: {full_path}")

    # אם extract נכשל – חריגה תעלה למעלה
    price = extract_row_price(full_path, search_text)

    # הגנה נוספת (paranoid, אבל נכון)
    if price is None:
        raise RuntimeError(f"Price is None for {search_text}")

    return price




def read_metal_prices():
    usd_eru, eru_shekel = ur.get_usd_eru()
    avr = get_average_price(HOT_KEY_FILE_COPPER,COPPER_FILE_NAME,COPPER_TEXT_BEFORE_PRICE)
    log(f"The copper price from LME Cash is {avr:.2f} $/ton")
    copper_price_eru = round(avr*usd_eru,2)
    log(f"The copper price from LME Cash is {copper_price_eru:.2f}{ERU_SYMBOL}/ton")

    avr = get_average_price(HOT_KEY_FILE_ALUMINIUM,ALUMINIUM_FILE_NAME,ALUMINIUM_TEXT_BEFORE_PRICE)
    log(f"The aluminium price from LME Cash is {avr:.2f}$/ton")
    aluminium_price_eru = round(avr*usd_eru,2)
    log(f"The aluminium price from LME Cash is {aluminium_price_eru:.2f}{ERU_SYMBOL}/ton")
    log(f'Eru price: {eru_shekel}{SHEKEL_SYMBOL}')
    log ("Up dating the price on ateka drive google sheet cable...")
    if upg.up_date_price(copper_price_eru,aluminium_price_eru,eru_shekel):
        return True
    else:
        return False
    #return round(copper_price_eru/1000,3), round(aluminium_price_eru/1000,3),eru_shekel


def main():
    log("=" * 60)
    log("START RUN")

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
