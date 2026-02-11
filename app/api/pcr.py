from flask import Blueprint, jsonify
from pnsea import NSE

pcr_bp = Blueprint("pcr", __name__)

PCR_INTERPRETATION = {
    "extreme_bearish": {
        "pcr_range": (0.0, 0.5),
        "sentiment": "Extremely Bearish (OverSold)",
        "action": "Avoid longs, look for PUT buying or CALL writing"
    },
    "bearish": {
        "pcr_range": (0.5, 0.7),
        "sentiment": "Bearish",
        "action": "Sell CALL spreads or wait for reversal"
    },
    "neutral": {
        "pcr_range": (0.7, 1.0),
        "sentiment": "Neutral",
        "action": "Market is rangebound, wait for breakout"
    },
    "bullish": {
        "pcr_range": (1.0, 1.3),
        "sentiment": "Bullish",
        "action": "Buy CALLs on dips or sell PUTs"
    },
    "extreme_bullish": {
        "pcr_range": (1.3, float("inf")),
        "sentiment": "Extremely Bullish (OverBought)",
        "action": "Aggressive CALL buying or PUT writing"
    }
}


def get_pcr_sentiment(pcr_value):
    for zone, info in PCR_INTERPRETATION.items():
        low, high = info["pcr_range"]
        if low <= pcr_value < high:
            return {
                "zone": zone,
                "sentiment": info["sentiment"],
                "action": info["action"]
            }

    return {
        "zone": "unknown",
        "sentiment": "Unknown",
        "action": "No action"
    }


def get_current_expiry_pcr():
    try:
        nse = NSE()

        option_chain = nse.options.option_chain("NIFTY")
        df = option_chain[0]  # nearest expiry

        ce_oi = df["CE_openInterest"].sum()
        pe_oi = df["PE_openInterest"].sum()

        if ce_oi == 0:
            raise ValueError("CE Open Interest is zero")

        pcr = round(pe_oi / ce_oi, 2)
        sentiment = get_pcr_sentiment(pcr)

        return {
            "pcr": pcr,
            "zone": sentiment["zone"],
            "sentiment": sentiment["sentiment"],
            "action": sentiment["action"]
        }

    except Exception as e:
        return {
            "error": "PCR calculation failed",
            "details": str(e)
        }


@pcr_bp.route("/pcr", methods=["GET"])
def pcr_check():
    return jsonify(get_current_expiry_pcr())
