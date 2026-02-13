from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.fyers import fyers_client
from app.services.stoxkart import stoxkart_client
from app.services.zerodha import zerodha_client


@dataclass
class OrderRequest:
    index_name: str = "NIFTY"
    strike: Optional[int] = None
    option_type: Optional[str] = None
    quantity: int = 1
    transaction_type: str = "BUY"
    fyers_symbol: Optional[str] = None
    stoxkart_symbol: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseBrokerAdapter(ABC):
    name: str

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        pass

    @abstractmethod
    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        pass


class ZerodhaAdapter(BaseBrokerAdapter):
    name = "zerodha"

    @property
    def is_configured(self) -> bool:
        return zerodha_client.is_configured

    @property
    def is_connected(self) -> bool:
        return zerodha_client.is_connected

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        if order.strike is None or order.option_type not in {"CE", "PE"}:
            raise ValueError("Zerodha requires strike and option_type (CE/PE)")
        return zerodha_client.place_option_order(
            index_name=order.index_name,
            strike=int(order.strike),
            option_type=order.option_type,
            quantity=int(order.quantity),
            transaction_type=order.transaction_type,
        )


class FyersAdapter(BaseBrokerAdapter):
    name = "fyers"

    @property
    def is_configured(self) -> bool:
        return fyers_client.is_configured

    @property
    def is_connected(self) -> bool:
        return fyers_client.is_connected

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        return fyers_client.place_option_order(
            symbol=order.fyers_symbol,
            quantity=int(order.quantity),
            transaction_type=order.transaction_type,
        )


class StoxkartAdapter(BaseBrokerAdapter):
    name = "stoxkart"

    @property
    def is_configured(self) -> bool:
        return stoxkart_client.is_configured

    @property
    def is_connected(self) -> bool:
        return stoxkart_client.is_connected

    def place_order(self, order: OrderRequest) -> Dict[str, Any]:
        return stoxkart_client.place_option_order(
            symbol=order.stoxkart_symbol,
            quantity=int(order.quantity),
            transaction_type=order.transaction_type,
        )


class BrokerSwitcher:
    def __init__(self, default_broker: str = "zerodha") -> None:
        self._active_broker = default_broker

    def set_active(self, broker: str, available: List[str]) -> str:
        if broker not in available:
            raise ValueError(f"Unsupported broker: {broker}")
        self._active_broker = broker
        return self._active_broker

    @property
    def active_broker(self) -> str:
        return self._active_broker


class StrategyRouter:
    def route(self, strategy: str, payload: Dict[str, Any]) -> List[OrderRequest]:
        strategy = (strategy or "single").lower()
        quantity = int(payload.get("quantity", 1))
        index_name = payload.get("index_name", "NIFTY")
        tx = payload.get("transaction_type", "BUY")

        if strategy == "single":
            return [
                OrderRequest(
                    index_name=index_name,
                    strike=payload.get("strike"),
                    option_type=payload.get("option_type"),
                    quantity=quantity,
                    transaction_type=tx,
                    fyers_symbol=payload.get("fyers_symbol"),
                    stoxkart_symbol=payload.get("stoxkart_symbol"),
                )
            ]

        if strategy == "iron_condor":
            legs = payload.get("legs", [])
            if len(legs) != 4:
                raise ValueError("iron_condor requires 4 legs")
            return [
                OrderRequest(
                    index_name=index_name,
                    strike=leg.get("strike"),
                    option_type=leg.get("option_type"),
                    quantity=int(leg.get("quantity", quantity)),
                    transaction_type=leg.get("transaction_type", "BUY"),
                    fyers_symbol=leg.get("fyers_symbol") or payload.get("fyers_symbol"),
                    stoxkart_symbol=leg.get("stoxkart_symbol") or payload.get("stoxkart_symbol"),
                    metadata={"strategy": "iron_condor", "leg": i + 1},
                )
                for i, leg in enumerate(legs)
            ]

        if strategy in {"call_spread", "put_spread", "calendar"}:
            legs = payload.get("legs", [])
            if len(legs) < 2:
                raise ValueError(f"{strategy} requires at least 2 legs")
            return [
                OrderRequest(
                    index_name=index_name,
                    strike=leg.get("strike"),
                    option_type=leg.get("option_type"),
                    quantity=int(leg.get("quantity", quantity)),
                    transaction_type=leg.get("transaction_type", "BUY"),
                    fyers_symbol=leg.get("fyers_symbol") or payload.get("fyers_symbol"),
                    stoxkart_symbol=leg.get("stoxkart_symbol") or payload.get("stoxkart_symbol"),
                    metadata={"strategy": strategy, "leg": i + 1},
                )
                for i, leg in enumerate(legs)
            ]

        raise ValueError(f"Unsupported strategy: {strategy}")


class OrderExecutionEngine:
    def __init__(self, brokers: Dict[str, BaseBrokerAdapter], switcher: BrokerSwitcher) -> None:
        self.brokers = brokers
        self.switcher = switcher

    def broker_status(self) -> Dict[str, Dict[str, bool]]:
        return {
            name: {
                "configured": broker.is_configured,
                "connected": broker.is_connected,
            }
            for name, broker in self.brokers.items()
        }

    def execute_with_failover(
        self,
        order: OrderRequest,
        selected_brokers: Optional[List[str]] = None,
        failover_enabled: bool = False,
    ) -> Dict[str, Any]:
        brokers_to_try = selected_brokers or [self.switcher.active_broker]
        if self.switcher.active_broker in brokers_to_try:
            brokers_to_try = [self.switcher.active_broker] + [b for b in brokers_to_try if b != self.switcher.active_broker]

        results: Dict[str, Any] = {}

        for broker_name in brokers_to_try:
            adapter = self.brokers.get(broker_name)
            if not adapter:
                results[broker_name] = {"success": False, "error": "Unsupported broker"}
                continue
            try:
                results[broker_name] = {"success": True, "order": adapter.place_order(order)}
                if failover_enabled:
                    return {"success": True, "results": results, "executed_by": broker_name}
            except Exception as exc:
                results[broker_name] = {"success": False, "error": str(exc)}
                if not failover_enabled:
                    continue

        overall_success = any(v.get("success") for v in results.values())
        return {"success": overall_success, "results": results, "executed_by": next((k for k, v in results.items() if v.get("success")), None)}

    def execute_strategy(
        self,
        orders: List[OrderRequest],
        selected_brokers: Optional[List[str]] = None,
        failover_enabled: bool = False,
    ) -> Dict[str, Any]:
        leg_results = []
        for order in orders:
            leg_results.append(self.execute_with_failover(order, selected_brokers, failover_enabled))

        return {
            "success": all(leg.get("success") for leg in leg_results),
            "legs": leg_results,
        }


broker_switcher = BrokerSwitcher(default_broker="zerodha")
strategy_router = StrategyRouter()
order_execution_engine = OrderExecutionEngine(
    brokers={
        "zerodha": ZerodhaAdapter(),
        "fyers": FyersAdapter(),
        "stoxkart": StoxkartAdapter(),
    },
    switcher=broker_switcher,
)
