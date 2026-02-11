from flask import Blueprint, jsonify

import requests


def get_india_vix():
    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive",
    }

    # Step 1: Warm-up request to get cookies
    session.get("https://www.nseindia.com", headers=headers, timeout=10)

    # Step 2: Fetch indices data
    url = "https://www.nseindia.com/api/allIndices"
    resp = session.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    data = resp.json()

    for item in data.get("data", []):
        if item.get("index") == "INDIA VIX":
            last = float(item["last"])
            prev = float(item.get("previousClose", last))
            change = round(last - prev, 2)

            return {
                "value": last,
                "change": change,
                "percent_change": float(item.get("percChange", 0.0)),
            }

    raise RuntimeError("INDIA VIX not found in NSE response")


vix_bp = Blueprint("vix", __name__)


def vix_sentiment(vix):
    if vix < 10:
        return "Complacent, Market too relaxed, risk of sudden spike"
    elif 10 <= vix < 12:
        return "Stable, Low volatility, bullish bias"
    elif 12 <= vix < 15:
        return "Normal, Healthy volatility"
    elif 15 <= vix < 20:
        return "Nervous, Uncertainty increasing"
    elif 20 <= vix < 30:
        return "Fear, High volatility, defensive mode"
    else:
        return "Capitulation, Extreme fear, contrarian opportunity"

def vix_action(vix):
    if vix < 10:
        return "carry position trades next day, movment will be only in the first 15min candle and rangebound throughout the day unless markets break range, scalping for 2-3 point in ATM options work well."
    elif 10 <= vix < 12:
        return "buy ATM options in the direction of market, market will move is same direction throughout the day."
    elif 12 <= vix < 15:
        return "Buy OTM options for quick scalping, dont hold for more then 2mins"
    elif 15 <= vix < 20:
        return "Avoid options trade, quick and large spikes are seen"
    elif  vix > 20:
        return "Avoid options trade in market"

@vix_bp.route("/vix", methods=["GET"])
def vix_check():
    vix = get_india_vix()
    sentiment = vix_sentiment(vix["value"])
    action = vix_action(vix["value"])

    return jsonify(
        {
            "vix": vix["value"],
            "sentiment": sentiment,
            "action": action,
        }
    )
