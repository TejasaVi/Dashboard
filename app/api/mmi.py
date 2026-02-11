from flask import Blueprint, jsonify
from tickersnap.mmi import MarketMoodIndex

def mmi_action_logic(value):
    if value < 25:
        return "Aggressive buying, add long positions"
    elif value < 40:
        return "Buy on dips, positional longs allowed"
    elif value < 55:
        return "Neutral zone, wait & watch, option selling preferred"
    elif value < 70:
        return "Reduce longs, hedge positions"
    else:
        return "Book profits, avoid fresh longs, consider shorts"

def fetch_mmi():
    mmi = MarketMoodIndex()
    current = mmi.get_current_mmi()

    action = mmi_action_logic(current.value)

    return {
        "value": round(current.value, 2),
        "zone": current.zone.value,   # original zone
        "action": action              # YOUR strategy layer
    }

mmi_bp = Blueprint("mmi", __name__)

@mmi_bp.route("/mmi", methods=["GET"])
def mmi_check():
    return jsonify(fetch_mmi())
