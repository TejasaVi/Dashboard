import json

def clamp(val, low, high):
    return max(low, min(val, high))


def option_signal_engine(
    mmi,
    rsi15,
    rsi60,
    pcr,
    oi_change_pcr,
    vix,
    spot,
    expiry_type="WEEKLY",
    prev_score=None,
    smooth_factor=0.7
):
    """
    Enhanced option signal engine with OI Change PCR
    """

    # ----------------------------
    # Step 1: Base score
    # ----------------------------
    raw_score = 50.0

    # ----------------------------
    # MMI (sentiment)
    # ----------------------------
    if "Extreme Fear" in mmi:
        raw_score += 15
    elif "Fear" in mmi:
        raw_score += 8
    elif "Greed" in mmi:
        raw_score -= 8
    elif "Extreme Greed" in mmi:
        raw_score -= 15

    # ----------------------------
    # RSI (momentum scaling)
    # ----------------------------
    if isinstance(rsi15, (int, float)) and isinstance(rsi60, (int, float)):
        avg_rsi = (rsi15 + rsi60) / 2

        if avg_rsi < 40:
            raw_score += clamp((40 - avg_rsi) * 0.5, 0, 12)
        elif avg_rsi > 60:
            raw_score -= clamp((avg_rsi - 60) * 0.5, 0, 12)

    # ----------------------------
    # Static PCR (positioning)
    # ----------------------------
    if isinstance(pcr, (int, float)):
        if pcr < 1:
            raw_score -= clamp((1 - pcr) * 20, 0, 12)
        else:
            raw_score += clamp((pcr - 1) * 20, 0, 12)

    # ----------------------------
    # ✅ OI Change PCR (flow-based weight)
    # ----------------------------
    if isinstance(oi_change_pcr, (int, float)):

        # Strong bullish build-up
        if oi_change_pcr > 1.3:
            raw_score += clamp((oi_change_pcr - 1.3) * 25, 0, 15)

        # Mild bullish build-up
        elif 1.1 < oi_change_pcr <= 1.3:
            raw_score += clamp((oi_change_pcr - 1.1) * 20, 0, 8)

        # Strong bearish build-up
        elif oi_change_pcr < 0.8:
            raw_score -= clamp((0.8 - oi_change_pcr) * 25, 0, 15)

        # Mild bearish build-up
        elif 0.8 <= oi_change_pcr < 0.95:
            raw_score -= clamp((0.95 - oi_change_pcr) * 20, 0, 8)

    # ----------------------------
    # VIX (volatility regime)
    # ----------------------------
    if isinstance(vix, (int, float)):
        if vix < 14:
            raw_score += clamp((14 - vix) * 1.5, 0, 8)
        elif vix > 18:
            raw_score -= clamp((vix - 18) * 1.5, 0, 10)

    # ----------------------------
    # Clamp raw score
    # ----------------------------
    raw_score = clamp(raw_score, 0, 100)

    # ----------------------------
    # Step 2: Smooth score (EMA)
    # ----------------------------
    if prev_score is not None:
        score = (smooth_factor * prev_score) + ((1 - smooth_factor) * raw_score)
    else:
        score = raw_score

    score = round(score, 1)

    # ----------------------------
    # Step 3: Bias bands
    # ----------------------------
    if score >= 62:
        bias = "Bullish"
        primary_action = "Buy Calls / Bullish Spread"
        strategy_list = [
            "Bull Call Spread", "Bull Put Spread",
            "Long Straddle", "Long Strangle",
            "Iron Condor", "Butterfly Spread", "Calendar Spread"
        ]
    elif score <= 38:
        bias = "Bearish"
        primary_action = "Buy Puts / Bearish Spread"
        strategy_list = [
            "Bear Put Spread", "Bear Call Spread",
            "Long Straddle", "Long Strangle",
            "Iron Condor", "Butterfly Spread", "Calendar Spread"
        ]
    else:
        bias = "Neutral"
        primary_action = "Wait / Non-Directional"
        strategy_list = [
            "Long Straddle", "Long Strangle",
            "Iron Condor", "Butterfly Spread", "Calendar Spread"
        ]

    # ----------------------------
    # Step 4: Strike logic
    # ----------------------------
    if vix < 12:
        base = 50 if expiry_type == "WEEKLY" else 100
    elif vix < 16:
        base = 100 if expiry_type == "WEEKLY" else 150
    elif vix < 20:
        base = 150 if expiry_type == "WEEKLY" else 250
    else:
        base = 250 if expiry_type == "WEEKLY" else 400

    atm = round(spot / 50) * 50

    strikes = {
        "ce_strike": atm + base if bias == "Bullish" else atm,
        "pe_strike": atm - base if bias == "Bearish" else atm,
        "spread_ce": {"buy": atm, "sell": atm + base},
        "spread_pe": {"buy": atm - base, "sell": atm},
        "iron_condor": {
            "sell_ce": atm + base,
            "buy_ce": atm + 2 * base,
            "sell_pe": atm - base,
            "buy_pe": atm - 2 * base
        },
        "butterfly": {
            "buy_lower": atm - base,
            "sell": atm,
            "buy_upper": atm + base
        },
        "calendar": {
            "ce_atm": atm,
            "pe_atm": atm
        },
        "warnings": []
    }

    if vix < 12:
        strikes["warnings"].append("⚠️ Low VIX: Premium expansion trades preferred")
    if vix > 20:
        strikes["warnings"].append("⚠️ High VIX: Risk defined strategies only")
    if expiry_type == "WEEKLY":
        strikes["warnings"].append("⏰ Weekly expiry: Theta accelerates")

    return {
        "score": score,
        "raw_score": round(raw_score, 1),
        "bias": bias,
        "primary_action": primary_action,
        "strategy_list": strategy_list,
        "strikes": strikes,
        "vix": vix,
        "oi_change_pcr": oi_change_pcr  # debugging visibility
    }
