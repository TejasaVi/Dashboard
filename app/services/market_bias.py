import json
from datetime import datetime, time


def clamp(val, low, high):
    return max(low, min(val, high))


def is_market_hours():
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)


def classify_vix_regime(vix):
    if vix is None:
        return "Unknown"

    if vix < 13:
        return "Low Volatility"
    elif vix < 18:
        return "Normal Volatility"
    elif vix < 23:
        return "High Volatility"
    else:
        return "Extreme Volatility"


def option_signal_engine(
    mmi,
    rsi15,
    rsi60,
    pcr,
    oi_change_pcr=None,
    vix=None,
    spot=None,
    expiry_type="WEEKLY",
    prev_bias=None,
    confirm_count=0,
    confirm_needed=2,
    freeze_after_hours=True
):

    # --------------------------------------------------
    # Market Freeze
    # --------------------------------------------------
    if freeze_after_hours and not is_market_hours():
        return {
            "score": None,
            "raw_score": None,
            "bias": "Market Closed",
            "primary_action": "No Action",
            "strategy_list": [],
            "strikes": {"warnings": ["🛑 Market closed: Signals frozen"]},
            "vix": vix
        }

    raw_score = 50.0
    warnings = []
    structural_notes = []

    # --------------------------------------------------
    # MMI
    # --------------------------------------------------
    if isinstance(mmi, str):
        if "Extreme Fear" in mmi:
            raw_score += 15
            structural_notes.append("Contrarian upside pressure forming")
        elif "Fear" in mmi:
            raw_score += 8
        elif "Extreme Greed" in mmi:
            raw_score -= 15
            structural_notes.append("Excess optimism — downside risk elevated")
        elif "Greed" in mmi:
            raw_score -= 8

    # --------------------------------------------------
    # RSI Trend Strength
    # --------------------------------------------------
    trend_strength = "Neutral"

    if isinstance(rsi15, (int, float)) and isinstance(rsi60, (int, float)):
        avg_rsi = (rsi15 + rsi60) / 2
        delta_rsi = rsi15 - rsi60

        if avg_rsi > 60:
            raw_score -= clamp((avg_rsi - 60) * 0.6, 0, 12)
            trend_strength = "Strong Uptrend"
        elif avg_rsi < 40:
            raw_score += clamp((40 - avg_rsi) * 0.6, 0, 12)
            trend_strength = "Strong Downtrend"

        if abs(delta_rsi) > 8:
            structural_notes.append("Momentum acceleration detected")

    # --------------------------------------------------
    # PCR
    # --------------------------------------------------
    if isinstance(pcr, (int, float)):
        raw_score += clamp((pcr - 1) * 18, -12, 12)

    # --------------------------------------------------
    # OI Change PCR (Most Important Structural Input)
    # --------------------------------------------------
    if isinstance(oi_change_pcr, (int, float)):

        if oi_change_pcr > 1.4:
            raw_score += 12
            structural_notes.append("Aggressive PUT writing (Strong bullish build-up)")
        elif oi_change_pcr > 1.2:
            raw_score += 6
            structural_notes.append("Moderate bullish build-up")
        elif oi_change_pcr < 0.6:
            raw_score -= 12
            structural_notes.append("Aggressive CALL writing (Strong bearish build-up)")
        elif oi_change_pcr < 0.8:
            raw_score -= 6
            structural_notes.append("Moderate bearish build-up")

    # --------------------------------------------------
    # VIX Regime + Impact
    # --------------------------------------------------
    vix_regime = classify_vix_regime(vix)

    if isinstance(vix, (int, float)):
        if vix < 13:
            raw_score += 5
            warnings.append("Low volatility regime — expansion trades preferred")
        elif vix > 20:
            raw_score -= 8
            warnings.append("High volatility regime — use defined risk spreads")

    raw_score = clamp(raw_score, 0, 100)
    score = round(raw_score, 1)

    # --------------------------------------------------
    # Breakout Probability Estimation
    # --------------------------------------------------
    breakout_probability = "Low"

    if abs(score - 50) > 20 and trend_strength != "Neutral":
        breakout_probability = "High"
    elif abs(score - 50) > 12:
        breakout_probability = "Moderate"

    # --------------------------------------------------
    # Bias Bands
    # --------------------------------------------------
    if score >= 62:
        new_bias = "Bullish"
        primary_action = "Buy Calls / Bullish Spread"
    elif score <= 38:
        new_bias = "Bearish"
        primary_action = "Buy Puts / Bearish Spread"
    else:
        new_bias = "Neutral"
        primary_action = "Wait / Non-Directional"

    # --------------------------------------------------
    # Bias Confirmation
    # --------------------------------------------------
    if prev_bias and new_bias != prev_bias:
        if confirm_count < confirm_needed:
            new_bias = prev_bias
            confirm_count += 1
            warnings.append("Shift forming — awaiting confirmation")
        else:
            confirm_count = 0
            warnings.append("Confirmed structural shift")

    # --------------------------------------------------
    # Strategy List
    # --------------------------------------------------
    if new_bias == "Bullish":
        strategy_list = [
            "Bull Call Spread",
            "Bull Put Spread",
            "Call Ratio Spread",
            "Calendar Spread",
            "Iron Condor"
        ]
    elif new_bias == "Bearish":
        strategy_list = [
            "Bear Put Spread",
            "Bear Call Spread",
            "Put Ratio Spread",
            "Calendar Spread",
            "Iron Condor"
        ]
    else:
        strategy_list = [
            "Long Straddle",
            "Long Strangle",
            "Iron Condor",
            "Butterfly Spread",
            "Calendar Spread"
        ]

    # --------------------------------------------------
    # Strike Logic
    # --------------------------------------------------
    if isinstance(vix, (int, float)):
        if vix < 12:
            base = 50 if expiry_type == "WEEKLY" else 100
        elif vix < 16:
            base = 100 if expiry_type == "WEEKLY" else 150
        elif vix < 20:
            base = 150 if expiry_type == "WEEKLY" else 250
        else:
            base = 250 if expiry_type == "WEEKLY" else 400
    else:
        base = 100

    atm = round(spot / 50) * 50 if spot else None

    strikes = {
        "ce_strike": atm + base if new_bias == "Bullish" and atm else atm,
        "pe_strike": atm - base if new_bias == "Bearish" and atm else atm,
        "spread_ce": {"buy": atm, "sell": atm + base} if atm else {},
        "spread_pe": {"buy": atm - base, "sell": atm} if atm else {},
        "iron_condor": {
            "sell_ce": atm + base,
            "buy_ce": atm + 2 * base,
            "sell_pe": atm - base,
            "buy_pe": atm - 2 * base
        } if atm else {},
        "calendar": {"ce_atm": atm, "pe_atm": atm} if atm else {},
        "warnings": warnings + structural_notes
    }

    # --------------------------------------------------
    # Final Response
    # --------------------------------------------------
    return {
        "score": score,
        "raw_score": round(raw_score, 1),
        "bias": new_bias,
        "primary_action": primary_action,
        "strategy_list": strategy_list,
        "strikes": strikes,
        "vix": vix,
        "vix_regime": vix_regime,
        "trend_strength": trend_strength,
        "breakout_probability": breakout_probability,
        "confirm_count": confirm_count
    }
