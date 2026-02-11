import yfinance as yf


def fetch_sensex():
    sensex = yf.Ticker("^BSESN")
    price = sensex.fast_info["last_price"]
    if price is None:
        raise RuntimeError("Yahoo Finance returned no Sensex price")

    return {
        "index": "SENSEX",
        "value": float(price),
    }
