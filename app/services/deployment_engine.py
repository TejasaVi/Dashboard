from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, time, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.services.zerodha import zerodha_client

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class DeploymentRequest:
    index_name: str
    strike: int
    option_type: str
    expiry_date: Optional[str]
    lots: int
    transaction_type: str = "BUY"


@dataclass
class DeploymentPlan:
    plan_id: str
    request: DeploymentRequest
    created_at: datetime
    status: str
    mode: Dict[str, str]
    max_lots_from_margin: int
    effective_max_lots: int
    initial_price: float
    bought_lots: int = 0
    pending_lots: int = 0
    average_buy_price: float = 0.0
    first_buy_price: Optional[float] = None
    first_buy_at: Optional[datetime] = None
    price_check_5m: Optional[float] = None
    price_check_10m: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    events: List[str] = field(default_factory=list)


class DeploymentEngine:
    """Stateful staged deployment engine for Zerodha."""

    def __init__(self) -> None:
        self._plans: Dict[str, DeploymentPlan] = {}
        self._lock = Lock()

    def _ist_now(self) -> datetime:
        return datetime.now(tz=IST)

    def _is_weekday(self, now: datetime) -> bool:
        return now.weekday() < 5

    def _market_is_regular_hours(self, now: datetime) -> bool:
        t = now.time()
        return time(9, 15) <= t <= time(15, 30)

    def _is_deployment_window(self, now: datetime) -> bool:
        t = now.time()
        return time(9, 40) <= t <= time(14, 50)

    def _order_mode(self, now: datetime) -> Dict[str, str]:
        if self._is_weekday(now) and not self._market_is_regular_hours(now):
            return {"variety": "AMO", "product": "NRML"}
        return {"variety": "REGULAR", "product": "NRML"}

    def _serialize_plan(self, plan: DeploymentPlan) -> Dict[str, Any]:
        data = asdict(plan)
        data["created_at"] = plan.created_at.isoformat()
        data["first_buy_at"] = plan.first_buy_at.isoformat() if plan.first_buy_at else None
        data["request"]["transaction_type"] = plan.request.transaction_type.upper()
        return data

    def create_plan(self, request: DeploymentRequest, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        metadata = metadata or {}
        now = self._ist_now()

        if not self._is_weekday(now):
            raise ValueError("Deployment is only supported Monday to Friday")

        if not self._is_deployment_window(now):
            raise ValueError("Deployments allowed only between 9:40 AM and 2:50 PM IST")

        zerodha_client.cancel_pending_nfo_orders()

        margin_available = zerodha_client.get_available_margin()
        contract = zerodha_client.find_option_contract(
            index_name=request.index_name,
            strike=request.strike,
            option_type=request.option_type,
            expiry_date=request.expiry_date,
        )
        current_price = zerodha_client.get_option_ltp(contract)
        lot_size = int(contract.get("lot_size") or 1)

        if current_price <= 0:
            raise ValueError("Invalid option LTP for deployment")

        max_by_margin = int(margin_available // (current_price * lot_size))
        max_lots = max(0, min(max_by_margin, int(request.lots)))
        if max_lots <= 0:
            raise ValueError("Insufficient margin for even 1 lot")

        plan = DeploymentPlan(
            plan_id=str(uuid4()),
            request=request,
            created_at=now,
            status="PENDING_START",
            mode=self._order_mode(now),
            max_lots_from_margin=max_by_margin,
            effective_max_lots=max_lots,
            initial_price=current_price,
            bought_lots=0,
            pending_lots=max_lots,
            metadata=metadata,
            events=["Plan created; waiting for engine tick to place first lot"],
        )

        with self._lock:
            self._plans[plan.plan_id] = plan

        return {"success": True, "plan": self._serialize_plan(plan)}

    def get_plan(self, plan_id: str) -> Dict[str, Any]:
        with self._lock:
            plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError("Deployment plan not found")
        return {"success": True, "plan": self._serialize_plan(plan)}

    def list_plans(self, active_only: bool = False) -> Dict[str, Any]:
        with self._lock:
            plans = list(self._plans.values())
        if active_only:
            plans = [p for p in plans if p.status in {"PENDING_START", "WAIT_5M", "WAIT_10M", "ACTIVE"}]
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return {"success": True, "plans": [self._serialize_plan(p) for p in plans]}

    def _place_lots(self, plan: DeploymentPlan, lots: int, price_hint: float, tx_type: Optional[str] = None) -> None:
        if lots <= 0:
            return
        order = zerodha_client.place_option_order(
            index_name=plan.request.index_name,
            strike=plan.request.strike,
            option_type=plan.request.option_type,
            quantity=lots,
            transaction_type=(tx_type or plan.request.transaction_type),
            expiry_date=plan.request.expiry_date,
            variety=plan.mode["variety"],
            product=plan.mode["product"],
        )
        plan.orders.append(order)
        if (tx_type or plan.request.transaction_type).upper() == "BUY":
            total_cost = (plan.average_buy_price * plan.bought_lots) + (price_hint * lots)
            plan.bought_lots += lots
            plan.pending_lots = max(0, plan.effective_max_lots - plan.bought_lots)
            plan.average_buy_price = total_cost / max(1, plan.bought_lots)

    def _process_single_plan(self, plan: DeploymentPlan, now: datetime) -> None:
        if plan.status in {"EXITED", "CLOSED", "EXPIRED", "ERROR"}:
            return

        if now.time() >= time(14, 59) and plan.bought_lots > 0:
            self._place_lots(
                plan,
                lots=plan.bought_lots,
                price_hint=plan.average_buy_price or plan.initial_price,
                tx_type="SELL" if plan.request.transaction_type.upper() == "BUY" else "BUY",
            )
            plan.events.append("Forced square-off before 3:00 PM IST")
            plan.status = "CLOSED"
            return

        if plan.status == "PENDING_START":
            if not self._is_deployment_window(now):
                if now.time() > time(14, 50):
                    plan.status = "EXPIRED"
                    plan.events.append("Plan expired without first deployment")
                return

            first_price = zerodha_client.get_option_ltp(
                zerodha_client.find_option_contract(
                    index_name=plan.request.index_name,
                    strike=plan.request.strike,
                    option_type=plan.request.option_type,
                    expiry_date=plan.request.expiry_date,
                )
            )
            self._place_lots(plan, lots=1, price_hint=first_price)
            plan.first_buy_price = first_price
            plan.first_buy_at = now
            plan.status = "WAIT_5M"
            plan.events.append("First lot deployed; waiting for 5-minute checkpoint")
            return

        if not plan.first_buy_at:
            return

        five_min_due = plan.first_buy_at + timedelta(minutes=5)
        ten_min_due = plan.first_buy_at + timedelta(minutes=10)

        current_price = zerodha_client.get_option_ltp(
            zerodha_client.find_option_contract(
                index_name=plan.request.index_name,
                strike=plan.request.strike,
                option_type=plan.request.option_type,
                expiry_date=plan.request.expiry_date,
            )
        )

        if plan.status == "WAIT_5M" and now >= five_min_due:
            plan.price_check_5m = current_price
            baseline = plan.first_buy_price or plan.initial_price
            if current_price > baseline and plan.pending_lots > 0:
                lots = plan.pending_lots
                self._place_lots(plan, lots=lots, price_hint=current_price)
                plan.events.append(f"5m: price up; deployed remaining {lots} lots")
            elif current_price < baseline and plan.pending_lots > 0:
                self._place_lots(plan, lots=1, price_hint=current_price)
                plan.events.append("5m: price down; deployed 1 additional lot")
            else:
                plan.events.append("5m: price unchanged; waiting for 10-minute checkpoint")
            plan.status = "WAIT_10M"
            return

        if plan.status in {"WAIT_10M", "ACTIVE"} and now >= ten_min_due:
            plan.price_check_10m = current_price
            if plan.bought_lots > 0 and current_price < plan.average_buy_price:
                self._place_lots(
                    plan,
                    lots=plan.bought_lots,
                    price_hint=current_price,
                    tx_type="SELL" if plan.request.transaction_type.upper() == "BUY" else "BUY",
                )
                plan.events.append("10m: price below average buy; exited position")
                plan.status = "EXITED"
            else:
                plan.events.append("10m: position retained")
                plan.status = "ACTIVE"

    def process(self, plan_id: Optional[str] = None) -> Dict[str, Any]:
        now = self._ist_now()
        if not self._is_weekday(now):
            return {"success": True, "processed": [], "message": "Non-trading day"}

        with self._lock:
            plans = [self._plans[plan_id]] if plan_id and plan_id in self._plans else list(self._plans.values())

        if plan_id and not plans:
            raise ValueError("Deployment plan not found")

        processed: List[Dict[str, Any]] = []
        for plan in plans:
            try:
                self._process_single_plan(plan, now)
            except Exception as exc:  # keep engine resilient across plans
                plan.status = "ERROR"
                plan.events.append(f"Engine error: {exc}")
            processed.append(self._serialize_plan(plan))

        return {"success": True, "processed": processed}

    def square_off_active_buys(self) -> Dict[str, Any]:
        now = self._ist_now()
        if not self._is_weekday(now):
            return {"success": True, "message": "No weekday positions to square off", "orders": []}
        if now.time() >= time(15, 0):
            return {"success": False, "error": "Square off must be completed before 3:00 PM IST", "orders": []}

        mode = self._order_mode(now)
        return zerodha_client.square_off_active_buys(variety=mode["variety"], product=mode["product"])


deployment_engine = DeploymentEngine()
