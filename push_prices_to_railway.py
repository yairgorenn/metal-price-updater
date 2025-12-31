import os
import requests
import datetime

RAILWAY_BASE_URL = os.getenv("RAILWAY_BASE_URL")
INGEST_TOKEN = os.getenv("INGEST_TOKEN")

if not RAILWAY_BASE_URL:
    raise RuntimeError("RAILWAY_BASE_URL not set")

if not INGEST_TOKEN:
    raise RuntimeError("INGEST_TOKEN not set")


def push_metal_price(
    metal: str,
    price_eur_per_ton: float,
    eur_to_ils: float,
    price_date: str
):
    url = f"{RAILWAY_BASE_URL}/ingest/metal-price"

    params = {
        "metal": metal,
        "price_eur_per_ton": price_eur_per_ton,
        "eur_to_ils": eur_to_ils,
        "price_date": price_date
    }

    headers = {
        "X-Token": INGEST_TOKEN
    }

    r = requests.post(url, params=params, headers=headers, timeout=15)

    if r.status_code != 200:
        raise RuntimeError(
            f"Railway ingest failed | metal={metal} | "
            f"status={r.status_code} | body={r.text}"
        )

    return True
