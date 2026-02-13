from stealthkit import StealthSession
from datetime import datetime

NSE_HOME = "https://www.nseindia.com"
ALL_INDICES_URL = "https://www.nseindia.com/api/allIndices"
MARKET_STATUS_URL = "https://www.nseindia.com/api/marketStatus"
CHART_DATA_URL = "https://www.nseindia.com/api/chart-databyindex"


class NSEClient:
    def __init__(self):
        # Create stealth session (no args)
        self.session = StealthSession()

        # Warm-up request to get cookies
        self.session.get(NSE_HOME, timeout=10)


    def fetch_index_chart(self, index_name: str = "NIFTY 50"):
        resp = self.session.get(
            CHART_DATA_URL,
            params={"index": index_name, "indices": "true"},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        graph_points = payload.get("grapthData") or payload.get("graphData") or []
        return {"index": index_name, "points": graph_points, "raw": payload}

    def fetch_indices(self):
        all_indices_resp = self.session.get(ALL_INDICES_URL, timeout=10)
        all_indices_resp.raise_for_status()

        payload = all_indices_resp.json()
        data = payload.get("data", [])

        market_status = {}
        try:
            market_status_resp = self.session.get(MARKET_STATUS_URL, timeout=10)
            market_status_resp.raise_for_status()
            market_status = market_status_resp.json()
        except Exception:
            market_status = {}

        indices = {}
        for item in data:
            name = item.get("index")
            last = item.get("last")

            if name in ("NIFTY 50", "NIFTY BANK", "SENSEX"):
                indices[name] = float(last)

        market_states = market_status.get("marketState") or []

        return {
            "NIFTY50": indices.get("NIFTY 50"),
            "BANKNIFTY": indices.get("NIFTY BANK"),
            "SENSEX": indices.get("SENSEX"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "all_indices": data,
            "market_status": {
                "raw": market_status,
                "states": market_states,
                "is_open": any((state.get("marketStatus") or "").lower() == "open" for state in market_states),
            },
        }
