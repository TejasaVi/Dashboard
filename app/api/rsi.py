from flask import Blueprint, jsonify

import yfinance as yf
import pandas as pd


def tradingview_rsi(series, period=14):
    """
    TradingView-style RSI (Wilder's RSI)
    """
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def get_nifty_rsi(interval="60m", period="1mo", rsi_period=14):
    """
    Fetch NIFTY RSI for given interval
    """
    df = yf.download("^NSEI", interval=interval, period=period, progress=False)

    if df.empty:
        raise ValueError("No data fetched. Check interval/period.")

    df["RSI"] = tradingview_rsi(df["Close"], rsi_period)

    latest = df.iloc[-1]

    return {
        "interval": interval,
        "rsi_period": rsi_period,
        "rsi_value": round(latest["RSI"], 2),
        "timestamp": latest.name,
    }


rsi_bp = Blueprint("rsi", __name__)


@rsi_bp.route("/rsi", methods=["GET"])
def rsi_check():
    rsi60 = get_nifty_rsi()
    rsi60_value = rsi60["rsi_value"].iloc[0]

    rsi15 = get_nifty_rsi(interval="15m")
    rsi15_value = rsi15["rsi_value"].iloc[0]

    # Determine sentiment
    if rsi60_value < 30:
        if rsi15_value < 30:
            sentiment = "Strong Buy"
        elif rsi15_value <= 70:
            sentiment = "Buy"
        else:  # rsi15 > 70
            sentiment = "Caution Buy"
    elif rsi60_value <= 70:  # 30-70
        if rsi15_value < 30:
            sentiment = "Buy (Short-term oversold)"
        elif rsi15_value <= 70:
            sentiment = "Neutral"
        else:  # rsi15 > 70
            sentiment = "Sell (Short-term overbought)"
    else:  # rsi60 > 70
        if rsi15_value < 30:
            sentiment = "Caution Sell"
        elif rsi15_value <= 70:
            sentiment = "Sell"
        else:  # rsi15 > 70
            sentiment = "Strong Sell"

    return jsonify({"rsi1hr": rsi60_value, "rsi15min":rsi15_value , "sentiment": sentiment})
