import json
import os
from datetime import date, datetime, time
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from kiteconnect import KiteConnect


def _parse_expiry_date(expiry_date: str) -> date:
    value = (expiry_date or "").strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("expiry_date must be in YYYY-MM-DD, DD-Mon-YYYY, or DD-MM-YYYY format")


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
            self._persist_access_token()
        elif self._kite:
            self._load_persisted_access_token()

    def _session_file_path(self) -> Path:
        configured = os.getenv("ZERODHA_SESSION_FILE", "").strip()
        if configured:
            return Path(configured)
        return Path(gettempdir()) / "zerodha_session.json"

    def _persist_access_token(self) -> None:
        if not self.api_key:
            return
        data = {"api_key": self.api_key, "access_token": self._access_token}
        self._session_file_path().write_text(json.dumps(data))

    def _load_persisted_access_token(self) -> None:
        if self._access_token or not self._kite or not self.api_key:
            return

        path = self._session_file_path()
        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())
        except Exception:
            return

        if data.get("api_key") != self.api_key:
            return

        token = (data.get("access_token") or "").strip()
        if not token:
            return

        self._access_token = token
        self._kite.set_access_token(self._access_token)

    def configure(self, api_key: str, api_secret: str, access_token: Optional[str] = None) -> None:
        prev_api_key = self.api_key
        prev_api_secret = self.api_secret
        self.api_key = (api_key or "").strip()
        self.api_secret = (api_secret or "").strip()

        if access_token is not None:
            self._access_token = access_token.strip()
        elif self.api_key != prev_api_key or self.api_secret != prev_api_secret:
            self._access_token = ""

        self._kite = KiteConnect(api_key=self.api_key) if self.api_key else None
        self._nfo_instruments = []
        if self._kite and self._access_token:
            self._kite.set_access_token(self._access_token)
            self._persist_access_token()
        elif self._kite:
            self._load_persisted_access_token()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self._kite)

    @property
    def is_connected(self) -> bool:
        self._load_persisted_access_token()
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
        self._persist_access_token()
        return self._access_token

    def disconnect(self) -> None:
        if self._kite and self._access_token:
            self._kite.set_access_token(self._access_token)
            try:
                self._kite.invalidate_access_token()
            except Exception:
                # Ignore revoke failures (e.g. already expired token) and clear local state anyway.
                pass

        self._access_token = ""
        if self._kite:
            self._kite.set_access_token("")
        self._persist_access_token()

    def profile(self) -> Dict[str, Any]:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            self._load_persisted_access_token()
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

    def _pick_option(
        self,
        index_name: str,
        strike: int,
        option_type: str,
        expiry_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        option_type = option_type.upper()
        today = date.today()
        target_expiry = None
        if expiry_date:
            target_expiry = _parse_expiry_date(expiry_date)
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
            if target_expiry and expiry != target_expiry:
                continue
            candidates.append(row)

        if not candidates:
            raise ValueError(f"No option contract found for {index_name} {strike} {option_type}")

        candidates.sort(key=lambda x: x["expiry"])
        return candidates[0]

    def find_option_contract(
        self,
        index_name: str,
        strike: int,
        option_type: str,
        expiry_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._pick_option(index_name=index_name, strike=strike, option_type=option_type, expiry_date=expiry_date)

    def get_option_ltp(self, contract: Dict[str, Any]) -> float:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        token = f"{self._kite.EXCHANGE_NFO}:{contract['tradingsymbol']}"
        ltp_data = self._kite.ltp([token])
        return float(ltp_data.get(token, {}).get("last_price") or 0)

    def get_available_margin(self) -> float:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            self._load_persisted_access_token()
        if not self._access_token:
            raise ValueError("Please connect Zerodha first")
        margins = self._kite.margins()
        equity = margins.get("equity", {})
        available = equity.get("available", {}) if isinstance(equity, dict) else {}
        cash = available.get("cash")
        live_balance = available.get("live_balance")
        return float(cash if cash is not None else (live_balance or 0))

    def _resolve_order_mode(self, variety: str, product: str) -> tuple[str, str]:
        if variety.upper() == "AMO":
            # Keep AMO payload aligned with previous working setup: always NRML for automation.
            return "AMO", "NRML"
        if variety.upper() != "AUTO":
            return variety.upper(), product.upper()
        now = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
        current = now.time()
        is_weekday = now.weekday() < 5
        if is_weekday and not (time(9, 15) <= current <= time(15, 30)):
            return "AMO", "NRML"
        return "REGULAR", "NRML"

    def _resolve_market_protection(self) -> int:
        configured = (os.getenv("ZERODHA_MARKET_PROTECTION", "3") or "3").strip()
        try:
            value = int(configured)
        except ValueError as exc:
            raise ValueError("ZERODHA_MARKET_PROTECTION must be an integer between 0 and 100") from exc
        if not (0 <= value <= 100):
            raise ValueError("ZERODHA_MARKET_PROTECTION must be between 0 and 100")
        return value

    def place_option_order(
        self,
        index_name: str,
        strike: int,
        option_type: str,
        quantity: int,
        transaction_type: str = "BUY",
        product: str = "NRML",
        variety: str = "AUTO",
        expiry_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            self._load_persisted_access_token()
        if not self._access_token:
            raise ValueError("Please connect Zerodha first")

        contract = self._pick_option(
            index_name=index_name,
            strike=strike,
            option_type=option_type,
            expiry_date=expiry_date,
        )

        lot_size = int(contract.get("lot_size") or 1)
        effective_variety, effective_product = self._resolve_order_mode(variety=variety, product=product)
        order_variety = self._kite.VARIETY_AMO if effective_variety == "AMO" else self._kite.VARIETY_REGULAR
        order_product = self._kite.PRODUCT_NRML if effective_product == "NRML" else self._kite.PRODUCT_MIS
        order_kwargs: Dict[str, Any] = {}
        if effective_variety == "AMO":
            order_kwargs["market_protection"] = self._resolve_market_protection()

        order_id = self._kite.place_order(
            variety=order_variety,
            exchange=self._kite.EXCHANGE_NFO,
            tradingsymbol=contract["tradingsymbol"],
            transaction_type=(
                self._kite.TRANSACTION_TYPE_SELL
                if transaction_type.upper() == "SELL"
                else self._kite.TRANSACTION_TYPE_BUY
            ),
            quantity=int(quantity) * lot_size,
            order_type=self._kite.ORDER_TYPE_MARKET,
            product=order_product,
            validity=self._kite.VALIDITY_DAY,
            **order_kwargs,
        )

        return {
            "order_id": order_id,
            "tradingsymbol": contract["tradingsymbol"],
            "strike": int(strike),
            "option_type": option_type.upper(),
            "expiry": str(contract.get("expiry")),
            "transaction_type": transaction_type.upper(),
            "quantity": int(quantity),
            "lot_size": lot_size,
            "variety": effective_variety,
            "product": effective_product,
        }

    def cancel_pending_nfo_orders(self) -> Dict[str, Any]:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            self._load_persisted_access_token()
        if not self._access_token:
            raise ValueError("Please connect Zerodha first")

        orders = self._kite.orders()
        cancelled = []
        for order in orders:
            status = (order.get("status") or "").upper()
            exchange = order.get("exchange")
            order_id = order.get("order_id")
            variety = (order.get("variety") or "regular").lower()
            if exchange != self._kite.EXCHANGE_NFO or not order_id:
                continue
            if status not in {"OPEN", "TRIGGER PENDING", "VALIDATION PENDING", "PUT ORDER REQ RECEIVED", "MODIFY VALIDATION PENDING", "MODIFY PENDING"}:
                continue
            self._kite.cancel_order(variety=variety, order_id=order_id)
            cancelled.append(order_id)

        return {"success": True, "cancelled_order_ids": cancelled}

    def square_off_active_buys(self, variety: str = "REGULAR", product: str = "NRML") -> Dict[str, Any]:
        if not self._kite:
            raise ValueError("Zerodha is not configured")
        if not self._access_token:
            self._load_persisted_access_token()
        if not self._access_token:
            raise ValueError("Please connect Zerodha first")

        positions = self._kite.positions().get("net", [])
        orders = []
        normalized_product = "NRML" if variety.upper() == "AMO" else product.upper()
        order_kwargs: Dict[str, Any] = {}
        if variety.upper() == "AMO":
            order_kwargs["market_protection"] = self._resolve_market_protection()
        for pos in positions:
            qty = int(pos.get("quantity") or 0)
            if qty <= 0:
                continue
            exchange = pos.get("exchange")
            symbol = pos.get("tradingsymbol")
            if exchange != self._kite.EXCHANGE_NFO or not symbol:
                continue
            order_id = self._kite.place_order(
                variety=self._kite.VARIETY_AMO if variety.upper() == "AMO" else self._kite.VARIETY_REGULAR,
                exchange=self._kite.EXCHANGE_NFO,
                tradingsymbol=symbol,
                transaction_type=self._kite.TRANSACTION_TYPE_SELL,
                quantity=qty,
                order_type=self._kite.ORDER_TYPE_MARKET,
                product=self._kite.PRODUCT_NRML if normalized_product == "NRML" else self._kite.PRODUCT_MIS,
                validity=self._kite.VALIDITY_DAY,
                **order_kwargs,
            )
            orders.append({"order_id": order_id, "tradingsymbol": symbol, "quantity": qty})

        return {"success": True, "orders": orders}


zerodha_client = ZerodhaClient()
