import os
from datetime import date
from typing import Any, Dict, List, Optional

from kiteconnect import KiteConnect


class ZerodhaClient:
    """Lightweight in-memory Zerodha session manager."""

    def __init__(self) -> None:
        self.api_key = os.getenv("ZERODHA_API_KEY", "")
        self.api_secret = os.getenv("ZERODHA_API_SECRET", "")
        self._access_token = os.getenv("ZERODHA_ACCESS_TOKEN", "")
        self._kite: Optional[KiteConnect] = KiteConnect(api_key=self.api_key) if self.api_key else None
        self._nfo_instruments: List[Dict[str, Any]] = []

        if self._kite and self._access_token:
            self._kite.set_access_token(self._access_token)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self._kite)

    @property
    def is_connected(self) -> bool:
        return bool(self._access_token and self._kite)

    def login_url(self) -> str:
        if not self._kite:
            raise ValueError("ZERODHA_API_KEY is missing")
        return self._kite.login_url()

    def save_session(self, request_token: str) -> str:
        if not self.is_configured or not self._kite:
            raise ValueError("Zerodha credentials are not configured")
        session_data = self._kite.generate_session(request_token, api_secret=self.api_secret)
        self._access_token = session_data["access_token"]
        self._kite.set_access_token(self._access_token)
        return self._access_token

    def profile(self) -> Dict[str, Any]:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            raise ValueError("Zerodha access token not available")
        return self._kite.profile()

    def _get_instruments(self) -> List[Dict[str, Any]]:
        if self._nfo_instruments:
            return self._nfo_instruments
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        self._nfo_instruments = self._kite.instruments("NFO")
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

    def place_option_order(
        self,
        index_name: str,
        strike: int,
        option_type: str,
        quantity: int,
        transaction_type: str = "BUY",
        product: str = "MIS",
    ) -> Dict[str, Any]:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            raise ValueError("Please connect Zerodha first")

        contract = self._pick_option(index_name=index_name, strike=strike, option_type=option_type)

        order_id = self._kite.place_order(
            variety=self._kite.VARIETY_REGULAR,
            exchange=self._kite.EXCHANGE_NFO,
            tradingsymbol=contract["tradingsymbol"],
            transaction_type=(
                self._kite.TRANSACTION_TYPE_SELL
                if transaction_type.upper() == "SELL"
                else self._kite.TRANSACTION_TYPE_BUY
            ),
            quantity=int(quantity),
            order_type=self._kite.ORDER_TYPE_MARKET,
            product=self._kite.PRODUCT_MIS if product == "MIS" else self._kite.PRODUCT_NRML,
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
