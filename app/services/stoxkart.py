import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests


class StoxkartClient:
    def __init__(self) -> None:
        self.client_id = os.getenv("STOXKART_CLIENT_ID", "")
        self.secret_key = os.getenv("STOXKART_SECRET_KEY", "")
        self.redirect_uri = os.getenv("STOXKART_REDIRECT_URI", "http://127.0.0.1:5000/api/stoxkart/callback")
        self.auth_base_url = os.getenv("STOXKART_AUTH_BASE_URL", "")
        self.token_url = os.getenv("STOXKART_TOKEN_URL", "")
        self.api_base_url = os.getenv("STOXKART_API_BASE_URL", "")
        self._access_token = os.getenv("STOXKART_ACCESS_TOKEN", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.secret_key and self.redirect_uri and self.auth_base_url)

    @property
    def is_connected(self) -> bool:
        return bool(self._access_token)

    def login_url(self) -> str:
        if not self.is_configured:
            raise ValueError("Stoxkart credentials are not configured")
        query = urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
            }
        )
        return f"{self.auth_base_url}?{query}"

    def save_session(self, code: Optional[str] = None, access_token: Optional[str] = None) -> str:
        if access_token:
            self._access_token = access_token
            return self._access_token

        if not code:
            raise ValueError("No code or access_token provided")

        if not self.token_url:
            raise ValueError("Set STOXKART_TOKEN_URL or pass access_token directly in callback")

        resp = requests.post(
            self.token_url,
            json={
                "client_id": self.client_id,
                "client_secret": self.secret_key,
                "redirect_uri": self.redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        token = data.get("access_token")
        if not token:
            raise ValueError(f"Unable to generate Stoxkart access token: {data}")
        self._access_token = token
        return self._access_token

    def _headers(self) -> Dict[str, str]:
        if not self._access_token:
            raise ValueError("Please connect Stoxkart first")
        return {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

    def profile(self) -> Dict[str, Any]:
        if not self.api_base_url:
            raise ValueError("Set STOXKART_API_BASE_URL")
        resp = requests.get(f"{self.api_base_url.rstrip('/')}/profile", headers=self._headers(), timeout=20)
        return resp.json() if resp.content else {}

    def place_option_order(
        self,
        symbol: Optional[str],
        quantity: int,
        transaction_type: str = "BUY",
    ) -> Dict[str, Any]:
        if not symbol:
            raise ValueError("Stoxkart order requires symbol")
        if not self.api_base_url:
            raise ValueError("Set STOXKART_API_BASE_URL")

        payload = {
            "symbol": symbol,
            "quantity": int(quantity),
            "transaction_type": transaction_type.upper(),
            "order_type": "MARKET",
            "product": "INTRADAY",
        }
        resp = requests.post(
            f"{self.api_base_url.rstrip('/')}/orders",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        data = resp.json() if resp.content else {}
        return {"response": data, "symbol": symbol, "quantity": int(quantity), "transaction_type": transaction_type.upper()}


stoxkart_client = StoxkartClient()
