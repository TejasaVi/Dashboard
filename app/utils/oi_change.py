from pnsea import NSE
OI_CHANGE_PCR_INTERPRETATION = {
    "extreme_bearish": {
        "pcr_range": (0.0, 0.5),
        "sentiment": "Strong Bearish Build-up",
        "action": "Short rallies, Buy PUTs"
    },
    "bearish": {
        "pcr_range": (0.5, 0.7),
        "sentiment": "Bearish Build-up",
        "action": "Sell CALLs or CALL spreads"
    },
    "neutral": {
        "pcr_range": (0.7, 1),
        "sentiment": "Neutral / No Clear Build-up",
        "action": "Avoid trades, wait for confirmation"
    },
    "bullish": {
        "pcr_range": (1, 1.3),
        "sentiment": "Bullish Build-up",
        "action": "Buy CALLs or sell PUTs"
    },
    "extreme_bullish": {
        "pcr_range": (1.3, float("inf")),
        "sentiment": "Strong Bullish Build-up",
        "action": "Aggressive CALL buying / PUT writing"
    }
}

def get_oi_change_pcr_sentiment(pcr_value):
    for zone, info in OI_CHANGE_PCR_INTERPRETATION.items():
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


def get_current_expiry_oi_change_pcr():
    try:
        nse = NSE()
        df = nse.options.option_chain("NIFTY")[0]  # nearest expiry

        ce_oi_change = df["CE_changeinOpenInterest"].sum()
        pe_oi_change = df["PE_changeinOpenInterest"].sum()

        if ce_oi_change <= 0:
            raise ValueError("Invalid CE OI Change")

        oi_change_pcr = round(pe_oi_change / ce_oi_change, 2)
        sentiment = get_oi_change_pcr_sentiment(oi_change_pcr)

        return {
            "oi_change_pcr": oi_change_pcr,
            "zone": sentiment["zone"],
            "sentiment": sentiment["sentiment"],
            "action": sentiment["action"]
        }

    except Exception as e:
        return {
            "error": "OI Change PCR calculation failed",
            "details": str(e)
        }

