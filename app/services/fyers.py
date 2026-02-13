import os
from typing import Any, Dict, Optional

from fyers_apiv3 import fyersModel


class FyersClient:
    def __init__(self) -> None:
        self.client_id = os.getenv("FYERS_CLIENT_ID", "")
        self.secret_key = os.getenv("FYERS_SECRET_KEY", "")
        self.redirect_uri = os.getenv("FYERS_REDIRECT_URI", "http://127.0.0.1:5000/api/fyers/callback")
        self._access_token = os.getenv("FYERS_ACCESS_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.secret_key and self.redirect_uri)

    @property
    def is_connected(self) -> bool:
        return bool(self._access_token)

    def _session(self) -> fyersModel.SessionModel:
        return fyersModel.SessionModel(
            client_id=self.client_id,
            secret_key=self.secret_key,
            redirect_uri=self.redirect_uri,
            response_type="code",
            grant_type="authorization_code",
        )

    def login_url(self) -> str:
        if not self.is_configured:
            raise ValueError("Fyers credentials are not configured")
        return self._session().generate_authcode()

    def save_session(self, auth_code: str) -> str:
        if not self.is_configured:
            raise ValueError("Fyers credentials are not configured")
        session = self._session()
        session.set_token(auth_code)
        response = session.generate_token()
        token = response.get("access_token")
        if not token:
            raise ValueError(f"Unable to generate Fyers access token: {response}")
        self._access_token = token
        return self._access_token

    def profile(self) -> Dict[str, Any]:
        if not self.is_connected:
            raise ValueError("Fyers access token not available")
        fyers = fyersModel.FyersModel(client_id=self.client_id, token=self._access_token, log_path="")
        return fyers.get_profile()

    def place_option_order(
        self,
        symbol: Optional[str],
        quantity: int,
        transaction_type: str = "BUY",
    ) -> Dict[str, Any]:
        if not self.is_connected:
            raise ValueError("Please connect Fyers first")
        if not symbol:
            raise ValueError("Fyers order requires option symbol")

        fyers = fyersModel.FyersModel(client_id=self.client_id, token=self._access_token, log_path="")
        side = 1 if transaction_type.upper() == "BUY" else -1
        payload = {
            "symbol": symbol,
            "qty": int(quantity),
            "type": 2,
            "side": side,
            "productType": "INTRADAY",
            "limitPrice": 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "stopLoss": 0,
            "takeProfit": 0,
        }
        resp = fyers.place_order(payload)
        return {"response": resp, "symbol": symbol, "quantity": int(quantity), "transaction_type": transaction_type.upper()}


fyers_client = FyersClient()
