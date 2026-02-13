from stealthkit import StealthSession
from datetime import datetime

NSE_HOME = "https://www.nseindia.com"
MARKET_STATUS_URL = "https://www.nseindia.com/api/marketStatus"
ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"


class NSEClient:
    def __init__(self):
        # Create stealth session (no args)
        self.session = StealthSession()

        # Warm-up request to get cookies
        self.session.get(NSE_HOME, timeout=10)

    def fetch_indices(self):
        market_status_payload = self.fetch_market_status()
        payload = self.fetch_all_indices()
        data = payload.get("data", [])

        indices = {}
        selected_snapshot = {}
        for item in data:
            name = item.get("index")
            last = item.get("last")

            if name in ("NIFTY 50", "NIFTY BANK", "SENSEX"):
                indices[name] = float(last)

            if name in ("NIFTY NEXT 50", "NIFTY MIDCAP 100", "INDIA VIX"):
                selected_snapshot[name] = {
                    "last": self._to_float(item.get("last")),
                    "change": self._to_float(item.get("change")),
                    "percentChange": self._to_float(item.get("percentChange") or item.get("percChange")),
                }

        market_state = market_status_payload.get("marketState", [])
        equity_state = next(
            (item for item in market_state if item.get("market") == "Capital Market"),
            None,
        )

        return {
            "NIFTY50": indices.get("NIFTY 50"),
            "BANKNIFTY": indices.get("NIFTY BANK"),
            "SENSEX": indices.get("SENSEX"),
            "market": self._normalize_market_state(equity_state),
            "marketStates": [self._normalize_market_state(item) for item in market_state],
            "indexSnapshot": selected_snapshot,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def fetch_market_status(self):
        resp = self.session.get(MARKET_STATUS_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def fetch_all_indices(self):
        resp = self.session.get(ALL_INDICES_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _normalize_market_state(item):
        if not item:
            return {
                "market": None,
                "status": None,
                "last": None,
                "tradeDate": None,
                "isOpen": False,
            }

        return {
            "market": item.get("market"),
            "status": item.get("marketStatus"),
            "last": item.get("last"),
            "tradeDate": item.get("tradeDate"),
            "isOpen": str(item.get("marketStatus", "")).upper() == "OPEN",
        }

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
