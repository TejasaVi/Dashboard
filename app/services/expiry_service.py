from __future__ import annotations

from datetime import datetime
from typing import List

from pnsea.nse import NSE


def get_index_expiries(symbol: str = "NIFTY") -> List[str]:
    nse = NSE()
    expiries = nse.options.expiry_dates(symbol.upper())
    return sorted({_normalize_expiry(item) for item in expiries if item}, key=_date_sort_key)


def _normalize_expiry(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _date_sort_key(value: str):
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.max
