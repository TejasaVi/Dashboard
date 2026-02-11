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

def vix_analysis(vix):
    """
    Returns market sentiment and action guidance based on VIX value.

    Output:
    {
        "vix": float,
        "sentiment": str,
        "action": str
    }
    """

    # Define ranges and corresponding sentiment/action
    vix_levels = [
        (0, 10, "Complacent: Market too relaxed, low perceived risk",
                  "Market calm and rangebound; avoid aggressive option selling."),
        (10, 12, "Stable: Low volatility, calm market environment",
                  "Mild trending possible; caution with heavy OTM option buying."),
        (12, 15, "Normal: Healthy volatility, balanced market conditions",
                  "Moderate swings likely; OTM options may move but avoid holding long."),
        (15, 20, "Nervous: Rising uncertainty, market participants cautious",
                  "High volatility; avoid selling options or overexposing positions."),
        (20, 30, "Fear: High volatility, defensive stance dominant",
                  "Significant swings; limit directional exposure, stay defensive."),
        (30, float('inf'), "Capitulation: Extreme fear, market highly stressed",
                           "Extreme volatility; avoid aggressive positions, focus on risk containment.")
    ]

    # Find the correct range
    for lower, upper, sentiment, action in vix_levels:
        if lower <= vix < upper:
            return {"vix": vix, "sentiment": sentiment, "action": action}

    # Fallback (should never hit)
    return {"vix": vix, "sentiment": "Unknown", "action": "No guidance available"}


@vix_bp.route("/vix", methods=["GET"])
def vix_check():
    vix = get_india_vix()
    analysis = vix_analysis(vix["value"])
    

    return jsonify(analysis)