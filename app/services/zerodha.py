import os
from datetime import date
from importlib import import_module
from typing import Any, Dict, List


class ZerodhaClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("ZERODHA_API_KEY", "")
        self.api_secret = os.getenv("ZERODHA_API_SECRET", "")
        self._access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")
        self._kite = None
        self._nfo_instruments: List[Dict[str, Any]] = []
        self._load_sdk_and_client()

    def _load_sdk_and_client(self) -> None:
        if not self.api_key:
            self._kite = None
            return
        try:
            kite_cls = import_module("kiteconnect").KiteConnect
            self._kite = kite_cls(api_key=self.api_key)
            if self._access_token:
                self._kite.set_access_token(self._access_token)
        except Exception:
            self._kite = None

    def _ensure_client(self):
        if self._kite is None:
            self._load_sdk_and_client()
        if self._kite is None:
            raise ValueError("kiteconnect SDK is not installed or ZERODHA_API_KEY missing. Run: pip install kiteconnect")
        return self._kite

    def update_credentials(self, api_key: str, api_secret: str) -> None:
        self.api_key = (api_key or "").strip()
        self.api_secret = (api_secret or "").strip()
        self._access_token = ""
        self._nfo_instruments = []
        self._load_sdk_and_client()

    @property
    def sdk_available(self) -> bool:
        return self._kite is not None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self._kite)

    @property
    def is_connected(self) -> bool:
        return bool(self._access_token and self._kite)

    def login_url(self) -> str:
        return self._ensure_client().login_url()

    def save_session(self, request_token: str) -> str:
        if not (self.api_key and self.api_secret):
            raise ValueError("Zerodha credentials are not configured")
        kite = self._ensure_client()
        session_data = kite.generate_session(request_token, api_secret=self.api_secret)
        self._access_token = session_data["access_token"]
        kite.set_access_token(self._access_token)
        return self._access_token

    def profile(self) -> Dict[str, Any]:
        if not self._access_token:
            raise ValueError("Zerodha access token not available")
        return self._ensure_client().profile()

    def _get_instruments(self) -> List[Dict[str, Any]]:
        if self._nfo_instruments:
            return self._nfo_instruments
        self._nfo_instruments = self._ensure_client().instruments("NFO")
        return self._nfo_instruments

    def _pick_option(self, index_name: str, strike: int, option_type: str) -> Dict[str, Any]:
        option_type = option_type.upper()
        today = date.today()
        candidates = []
        for row in self._get_instruments():
            if row.get("name") != index_name:
                continue
            if row.get("instrument_type") != option_type:
                continue
            if int(float(row.get("strike", 0))) != int(strike):
                continue
            expiry = row.get("expiry")
            if not expiry or expiry < today:
                continue
            candidates.append(row)
        if not candidates:
            raise ValueError(f"No option contract found for {index_name} {strike} {option_type}")
        candidates.sort(key=lambda x: x["expiry"])
        return candidates[0]

    def place_option_order(self, index_name: str, strike: int, option_type: str, quantity: int, transaction_type: str = "BUY", product: str = "MIS") -> Dict[str, Any]:
        if not self._access_token:
            raise ValueError("Please connect Zerodha first")
        kite = self._ensure_client()
        contract = self._pick_option(index_name=index_name, strike=strike, option_type=option_type)
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=kite.EXCHANGE_NFO,
            tradingsymbol=contract["tradingsymbol"],
            transaction_type=(kite.TRANSACTION_TYPE_SELL if transaction_type.upper() == "SELL" else kite.TRANSACTION_TYPE_BUY),
            quantity=int(quantity),
            order_type=kite.ORDER_TYPE_MARKET,
            product=kite.PRODUCT_MIS if product == "MIS" else kite.PRODUCT_NRML,
        )
        return {
            "order_id": order_id,
            "tradingsymbol": contract["tradingsymbol"],
            "strike": int(strike),
            "option_type": option_type.upper(),
            "expiry": str(contract.get("expiry")),
            "transaction_type": transaction_type.upper(),
            "quantity": int(quantity),
        }


zerodha_client = ZerodhaClient()
