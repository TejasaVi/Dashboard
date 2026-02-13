import pandas as pd

from app.services.nse_history import fetch_nifty_ohlcv, resample_close
from app.services.ta_compat import ema as ta_ema, sma as ta_sma


def fetch_nifty_data(period="6mo"):
    _ = period  # retained for API compatibility
    data = fetch_nifty_ohlcv(limit=600)
    if data.empty:
        return data

    close_daily = resample_close(data, "1d")
    if len(close_daily) >= 2:
        daily = pd.DataFrame(index=close_daily.index)
        daily["Close"] = close_daily
        daily["Open"] = close_daily
        daily["High"] = close_daily
        daily["Low"] = close_daily
        daily["Volume"] = 0
        return daily

    return data


def safe_get_value(series_or_value):
    if isinstance(series_or_value, pd.Series):
        return series_or_value.iloc[0] if len(series_or_value) > 0 else None
    return series_or_value


def calculate_indicators(data, ma_periods=None):
    ma_periods = ma_periods or [10, 20, 50, 100]
    close = data["Close"].astype(float)
    for period in ma_periods:
        data[f"MA_{period}"] = ta_sma(close, period)
        data[f"EMA_{period}"] = ta_ema(close, period)
    return data


def calculate_pivot_points(yesterday):
    high = safe_get_value(yesterday["High"])
    low = safe_get_value(yesterday["Low"])
    close = safe_get_value(yesterday["Close"])
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    r2 = pivot + (high - low)
    r3 = high + 2 * (pivot - low)
    s1 = (2 * pivot) - high
    s2 = pivot - (high - low)
    s3 = low - 2 * (high - pivot)
    return {
        "pivot": round(pivot, 2),
        "resistance": {"r1": round(r1, 2), "r2": round(r2, 2), "r3": round(r3, 2)},
        "support": {"s1": round(s1, 2), "s2": round(s2, 2), "s3": round(s3, 2)},
    }


def calculate_support_resistance(data, yesterday_close, ma_periods):
    yesterday = data.iloc[-2]
    ma_levels = []
    for period in ma_periods:
        ma_val = safe_get_value(yesterday[f"MA_{period}"])
        if ma_val is not None and not pd.isna(ma_val):
            ma_levels.append(("MA", period, ma_val))

    recent_data = data.tail(20)
    recent_high = safe_get_value(recent_data["High"].max())
    recent_low = safe_get_value(recent_data["Low"].min())

    supports, resistances = [], []
    for label, period, value in ma_levels:
        if value < yesterday_close:
            supports.append({"level": f"{label}_{period}", "value": round(value, 2)})
        else:
            resistances.append({"level": f"{label}_{period}", "value": round(value, 2)})

    if recent_high and recent_high > yesterday_close:
        resistances.append({"level": "Recent_High", "value": round(recent_high, 2)})
    if recent_low and recent_low < yesterday_close:
        supports.append({"level": "Recent_Low", "value": round(recent_low, 2)})

    supports.sort(key=lambda x: x["value"], reverse=True)
    resistances.sort(key=lambda x: x["value"])
    return supports[:5], resistances[:5]


def analyze_trend(close, ma_values):
    trends = []
    trends.append("Above 20-day MA (Short-term bullish)" if close > ma_values.get("MA_20", 0) else "Below 20-day MA (Short-term bearish)")
    trends.append("Above 50-day MA (Medium-term bullish)" if close > ma_values.get("MA_50", 0) else "Below 50-day MA (Medium-term bearish)")
    if ma_values.get("MA_20") and ma_values.get("MA_50"):
        trends.append("20-MA above 50-MA (Bullish alignment)" if ma_values["MA_20"] > ma_values["MA_50"] else "20-MA below 50-MA (Bearish alignment)")
    return trends


def get_nifty_analysis(period="6mo", ma_periods=None):
    ma_periods = ma_periods or [10, 20, 50, 100]
    try:
        data = fetch_nifty_data(period)
        if len(data) < 2:
            return {"error": "Insufficient data retrieved"}

        data = calculate_indicators(data, ma_periods)
        yesterday = data.iloc[-2]
        yesterday_close = safe_get_value(yesterday["Close"])
        yesterday_date = yesterday.name.date()

        ma_values = {}
        analysis_data = {
            "date": yesterday_date.isoformat(),
            "price_data": {
                "close": round(yesterday_close, 2),
                "high": round(safe_get_value(yesterday["High"]), 2),
                "low": round(safe_get_value(yesterday["Low"]), 2),
                "volume": int(safe_get_value(yesterday["Volume"])),
            },
            "moving_averages": {},
            "exponential_moving_averages": {},
            "trend_analysis": [],
            "pivot_points": {},
            "support_resistance": {"supports": [], "resistances": []},
        }

        for p in ma_periods:
            ma_val = safe_get_value(yesterday[f"MA_{p}"])
            ema_val = safe_get_value(yesterday[f"EMA_{p}"])
            ma_val = ma_val if ma_val is not None and not pd.isna(ma_val) else None
            ema_val = ema_val if ema_val is not None and not pd.isna(ema_val) else None
            ma_values[f"MA_{p}"] = ma_val

            if ma_val is not None:
                diff = ((yesterday_close - ma_val) / ma_val) * 100
                analysis_data["moving_averages"][f"MA_{p}"] = {
                    "value": round(ma_val, 2),
                    "difference_percent": round(diff, 2),
                    "position": "above" if diff > 0 else "below",
                }
            if ema_val is not None:
                diff = ((yesterday_close - ema_val) / ema_val) * 100
                analysis_data["exponential_moving_averages"][f"EMA_{p}"] = {
                    "value": round(ema_val, 2),
                    "difference_percent": round(diff, 2),
                    "position": "above" if diff > 0 else "below",
                }

        analysis_data["trend_analysis"] = analyze_trend(yesterday_close, ma_values)
        analysis_data["pivot_points"] = calculate_pivot_points(yesterday)
        supports, resistances = calculate_support_resistance(data, yesterday_close, ma_periods)
        analysis_data["support_resistance"]["supports"] = supports
        analysis_data["support_resistance"]["resistances"] = resistances
        return analysis_data
    except Exception as e:
        import traceback

        return {"error": str(e), "traceback": traceback.format_exc()}
