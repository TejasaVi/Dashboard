from __future__ import annotations

import importlib

import pandas as pd


_HAS_TA = importlib.util.find_spec("ta") is not None


if _HAS_TA:
    from ta.momentum import RSIIndicator
    from ta.trend import EMAIndicator, MACD, SMAIndicator


def sma(series: pd.Series, period: int) -> pd.Series:
    if _HAS_TA:
        return SMAIndicator(series, window=period).sma_indicator()
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    if _HAS_TA:
        return EMAIndicator(series, window=period).ema_indicator()
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    if _HAS_TA:
        return RSIIndicator(series, window=period).rsi()

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    if _HAS_TA:
        ind = MACD(close=series, window_fast=fast, window_slow=slow, window_sign=signal)
        line = ind.macd()
        sig = ind.macd_signal()
        hist = ind.macd_diff()
        return line, sig, hist

    ema_short = series.ewm(span=fast, adjust=False).mean()
    ema_long = series.ewm(span=slow, adjust=False).mean()
    line = ema_short - ema_long
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig
