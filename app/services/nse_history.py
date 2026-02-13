from __future__ import annotations

from typing import Optional

import pandas as pd

from app.utils.nse_client import NSEClient


_nse_client: Optional[NSEClient] = None


def _get_client() -> NSEClient:
    global _nse_client
    if _nse_client is None:
        _nse_client = NSEClient()
    return _nse_client


def fetch_nifty_ohlcv(limit: int = 600) -> pd.DataFrame:
    """Fetch NIFTY 50 chart points from NSE and normalize to OHLCV-like dataframe."""
    raw = _get_client().fetch_index_chart(index_name="NIFTY 50")
    points = raw.get("points") or []

    if not points:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    frame = pd.DataFrame(points, columns=["timestamp", "Close"])
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True).dt.tz_convert("Asia/Kolkata")
    frame = frame.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

    if limit > 0:
        frame = frame.tail(limit)

    # NSE chart endpoint is close-only. Keep schema compatible for existing indicator code.
    frame["Open"] = frame["Close"]
    frame["High"] = frame["Close"]
    frame["Low"] = frame["Close"]
    frame["Volume"] = 0

    return frame.set_index("timestamp")[["Open", "High", "Low", "Close", "Volume"]]


def resample_close(df: pd.DataFrame, interval: str) -> pd.Series:
    close = df["Close"].astype(float)
    rule = {"15m": "15min", "60m": "60min", "1h": "60min", "1d": "1D"}.get(interval, "60min")
    return close.resample(rule).last().dropna()
