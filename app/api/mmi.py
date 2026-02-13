from flask import Blueprint, jsonify
from tickersnap.mmi import MarketMoodIndex

mmi_bp = Blueprint("mmi", __name__)

def mmi_investment_logic(value):
    if value < 25:
        return {
            "regime": "Extreme Fear",
            "investment_view": "Strong accumulation zone",
            "equity_exposure": "Increase aggressively",
            "risk_level": "Low",
            "action": "Deploy cash, accumulate quality stocks / ETFs"
        }

    elif value < 40:
        return {
            "regime": "Fear",
            "investment_view": "Accumulation zone",
            "equity_exposure": "Increase gradually",
            "risk_level": "Moderate",
            "action": "Buy on dips, accelerate SIP if long-term investor"
        }

    elif value < 55:
        return {
            "regime": "Neutral",
            "investment_view": "Fair valuation zone",
            "equity_exposure": "Maintain allocation",
            "risk_level": "Balanced",
            "action": "Continue systematic investing"
        }

    elif value < 70:
        return {
            "regime": "Greed",
            "investment_view": "Caution zone",
            "equity_exposure": "Trim leveraged exposure",
            "risk_level": "Elevated",
            "action": "Rebalance portfolio, tighten stop losses"
        }

    else:
        return {
            "regime": "Extreme Greed",
            "investment_view": "Distribution zone",
            "equity_exposure": "Reduce equity allocation",
            "risk_level": "High",
            "action": "Book profits, raise cash, hedge portfolio"
        }


def fetch_mmi():
    mmi = MarketMoodIndex()
    current = mmi.get_current_mmi()

    investment_layer = mmi_investment_logic(current.value)

    return {
        "value": round(current.value, 2),
        "zone": current.zone.value,
        "portfolio_guidance": investment_layer
    }


@mmi_bp.route("/mmi", methods=["GET"])
def mmi_check():
    return jsonify(fetch_mmi())
