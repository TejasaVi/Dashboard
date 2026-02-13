from flask import Blueprint, jsonify
import pandas as pd
import yfinance as yf

macd_bp = Blueprint("macd", __name__)

def _stochastic_macd(df, macd_col="MACD", k_period=14, d_period=3):
    low_macd = df[macd_col].rolling(window=k_period).min()
    high_macd = df[macd_col].rolling(window=k_period).max()
    denominator = (high_macd - low_macd).replace(0, pd.NA)
    df["Stoch_%K"] = 100 * ((df[macd_col] - low_macd) / denominator)
    df["Stoch_%D"] = df["Stoch_%K"].rolling(window=d_period).mean()
    return df

def _to_scalar(val):
    return val.item() if hasattr(val, "item") else val

def _analyze_and_suggest(df):
    if len(df) < 2:
        return {
            "MACD_signal": None,
            "Stochastic_signal": None,
            "Stoch_K_value": None,
            "Stoch_D_value": None,
            "Momentum": None,
            "Option_Strategy": "Not enough data to generate strategy.",
        }

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    macd = _to_scalar(latest["MACD"])
    signal = _to_scalar(latest["Signal"])
    prev_macd = _to_scalar(prev["MACD"])
    prev_signal = _to_scalar(prev["Signal"])
    stoch_k = _to_scalar(latest["Stoch_%K"])
    stoch_d = _to_scalar(latest["Stoch_%D"])
    prev_stoch_k = _to_scalar(prev["Stoch_%K"])
    prev_stoch_d = _to_scalar(prev["Stoch_%D"])

    result = {
        "MACD_signal": "No crossover",
        "Stochastic_signal": "Neutral",
        "Stoch_K_value": round(stoch_k, 1) if pd.notna(stoch_k) else None,
        "Stoch_D_value": round(stoch_d, 1) if pd.notna(stoch_d) else None,
        "Momentum": "Neutral",
        "Option_Strategy": "",
    }

    # MACD Crossover Detection
    if pd.notna(macd) and pd.notna(signal) and pd.notna(prev_macd) and pd.notna(prev_signal):
        if macd > signal and prev_macd <= prev_signal:
            result["MACD_signal"] = "Bullish crossover"
        elif macd < signal and prev_macd >= prev_signal:
            result["MACD_signal"] = "Bearish crossover"

    # Improved Stochastic Logic - Shows actual values + crossovers + relaxed thresholds
    if pd.notna(stoch_k):
        if stoch_k > 85:  # Relaxed from 80 for MACD volatility
            result["Stochastic_signal"] = "Overbought"
        elif stoch_k < 15:  # Relaxed from 20
            result["Stochastic_signal"] = "Oversold"
        elif pd.notna(stoch_d) and pd.notna(prev_stoch_k) and pd.notna(prev_stoch_d):
            # Add %K/%D crossover signals for neutral zone
            if stoch_k > stoch_d and prev_stoch_k <= prev_stoch_d:
                result["Stochastic_signal"] = "Bullish %K/%D crossover"
            elif stoch_k < stoch_d and prev_stoch_k >= prev_stoch_d:
                result["Stochastic_signal"] = "Bearish %K/%D crossover"
        else:
            result["Stochastic_signal"] = f"Neutral ({result['Stoch_K_value']})"

    # MACD Momentum
    if pd.notna(macd):
        result["Momentum"] = "Positive" if macd > 0 else "Negative"

    # Enhanced Option Strategy Logic
    option_action = []
    
    # Primary signals
    if result["MACD_signal"] == "Bullish crossover" and result["Momentum"] == "Positive":
        option_action.append("CE Buying opportunity")
    elif result["MACD_signal"] == "Bearish crossover" and result["Momentum"] == "Negative":
        option_action.append("PE Buying opportunity")
    
    # Stochastic cautions
    if result["Stochastic_signal"] == "Overbought":
        option_action.append("Caution: CE positions overbought")
    elif result["Stochastic_signal"] == "Oversold":
        option_action.append("Caution: PE positions oversold")
    elif "Bullish %K/%D crossover" in result["Stochastic_signal"]:
        option_action.append("Stochastic supports bullish bias")
    elif "Bearish %K/%D crossover" in result["Stochastic_signal"]:
        option_action.append("Stochastic supports bearish bias")
    
    if not option_action:
        option_action.append("Wait for clearer signals")

    result["Option_Strategy"] = " | ".join(option_action)
    return result

def get_nifty_option_signals(period="6mo", interval="1d"):
    ticker = "^NSEI"
    data = yf.download(ticker, period=period, interval=interval, progress=False)

    if data.empty:
        return {
            "MACD_signal": None,
            "Stochastic_signal": None,
            "Stoch_K_value": None,
            "Stoch_D_value": None,
            "Momentum": None,
            "Option_Strategy": "No data fetched for NIFTY. Check internet or try alternative ticker.",
        }

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    # Standard MACD calculation
    ema_short = data["Close"].ewm(span=12, adjust=False).mean()
    ema_long = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = ema_short - ema_long
    data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["Histogram"] = data["MACD"] - data["Signal"]

    # Apply Stochastic to MACD
    data = _stochastic_macd(data, macd_col="MACD", k_period=14, d_period=3)
    
    return _analyze_and_suggest(data)

@macd_bp.route("/macd", methods=["GET"])
def nifty_options_api():
    signals = get_nifty_option_signals()
    return jsonify(signals)
