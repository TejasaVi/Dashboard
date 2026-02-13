from flask import Blueprint, jsonify

from app.services.nse_history import fetch_nifty_ohlcv, resample_close
from app.services.ta_compat import rsi as ta_rsi


rsi_bp = Blueprint("rsi", __name__)


def get_nifty_rsi(interval="60m", period="1mo", rsi_period=14):
    _ = period  # kept for API compatibility
    df = fetch_nifty_ohlcv(limit=600)
    if df.empty:
        raise ValueError("No data fetched from NSE chart endpoint.")

    close = resample_close(df, interval)
    if close.empty:
        raise ValueError("Insufficient resampled data for RSI.")

    rsi_series = ta_rsi(close, period=rsi_period)
    latest_rsi = float(rsi_series.dropna().iloc[-1]) if not rsi_series.dropna().empty else None
    latest_ts = close.index[-1]

    return {
        "interval": interval,
        "rsi_period": rsi_period,
        "rsi_value": round(latest_rsi, 2) if latest_rsi is not None else None,
        "timestamp": latest_ts,
    }


@rsi_bp.route("/rsi", methods=["GET"])
def rsi_check():
    rsi60_value = get_nifty_rsi()["rsi_value"]
    rsi15_value = get_nifty_rsi(interval="15m")["rsi_value"]

    if rsi60_value is None or rsi15_value is None:
        return jsonify({"rsi1hr": rsi60_value, "rsi15min": rsi15_value, "sentiment": "Insufficient data"})

    if rsi60_value < 30:
        if rsi15_value < 30:
            sentiment = "Strong Buy"
        elif rsi15_value <= 70:
            sentiment = "Buy"
        else:
            sentiment = "Caution Buy"
    elif rsi60_value <= 70:
        if rsi15_value < 30:
            sentiment = "Buy (Short-term oversold)"
        elif rsi15_value <= 70:
            sentiment = "Neutral"
        else:
            sentiment = "Sell (Short-term overbought)"
    else:
        if rsi15_value < 30:
            sentiment = "Caution Sell"
        elif rsi15_value <= 70:
            sentiment = "Sell"
        else:
            sentiment = "Strong Sell"

    return jsonify({"rsi1hr": rsi60_value, "rsi15min": rsi15_value, "sentiment": sentiment})
