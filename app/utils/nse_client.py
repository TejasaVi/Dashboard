from stealthkit import StealthSession
from datetime import datetime

NSE_HOME = "https://www.nseindia.com"
ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"


class NSEClient:
    def __init__(self):
        # Create stealth session (no args)
        self.session = StealthSession()

        # Warm-up request to get cookies
        self.session.get(NSE_HOME, timeout=10)

    def fetch_indices(self):
        resp = self.session.get(ALL_INDICES_URL, timeout=10)
        resp.raise_for_status()

        payload = resp.json()
        data = payload.get("data", [])

        indices = {}
        for item in data:
            name = item.get("index")
            last = item.get("last")

            if name in ("NIFTY 50", "NIFTY BANK", "SENSEX"):
                indices[name] = float(last)

        return {
            "NIFTY50": indices.get("NIFTY 50"),
            "BANKNIFTY": indices.get("NIFTY BANK"),
            "SENSEX": indices.get("SENSEX"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

