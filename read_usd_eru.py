import urllib.request, urllib.parse, urllib.error
import ssl
import json

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def get_json(url_json):
    try:
        js = urllib.request.urlopen(url_json, context=ctx).read()
        #print("Retrieving",url_json)
        #print("Retrieved", len(js),"characters")
        return js
    except:
        return None


def get_usd_eru():
    json_url = "https://boi.org.il/PublicApi/GetExchangeRates"

    raw = get_json(json_url)
    if raw is None:
        raise RuntimeError("Failed to retrieve BOI exchange rates (no response)")

    try:
        data = json.loads(raw)
    except Exception as e:
        raise RuntimeError(f"Failed to parse BOI JSON: {e}")

    if 'exchangeRates' not in data:
        raise RuntimeError("BOI response missing 'exchangeRates' field")

    usd_rate = None
    eur_rate = None

    for rate in data['exchangeRates']:
        if rate.get('key') == 'USD':
            usd_rate = float(rate.get('currentExchangeRate'))
        elif rate.get('key') == 'EUR':
            eur_rate = float(rate.get('currentExchangeRate'))

    if usd_rate is None:
        raise RuntimeError("USD rate not found in BOI response")

    if eur_rate is None:
        raise RuntimeError("EUR rate not found in BOI response")

    # sanity checks – קריטי
    if not (0.5 < usd_rate < 10):
        raise RuntimeError(f"USD rate out of expected range: {usd_rate}")

    if not (0.5 < eur_rate < 10):
        raise RuntimeError(f"EUR rate out of expected range: {eur_rate}")

    usd_to_eur = usd_rate / eur_rate

    if not (0.5 < usd_to_eur < 2):
        raise RuntimeError(f"USD/EUR rate out of expected range: {usd_to_eur}")

    return usd_to_eur, eur_rate
