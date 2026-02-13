from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List


@dataclass
class TradingSettings:
    paper_trading: bool = False
    daily_loss_limit: float = 0.0
    summary_email: str = ""


@dataclass
class TradeRecord:
    timestamp: str
    broker: str
    symbol: str
    transaction_type: str
    quantity: int
    status: str
    pnl: float
    mode: str
    details: Dict[str, Any] = field(default_factory=dict)


class TradingState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.settings = TradingSettings()
        self._trades: List[TradeRecord] = []

    def update_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if "paper_trading" in payload:
                self.settings.paper_trading = bool(payload.get("paper_trading"))
            if "daily_loss_limit" in payload:
                self.settings.daily_loss_limit = max(0.0, float(payload.get("daily_loss_limit") or 0.0))
            if "summary_email" in payload:
                self.settings.summary_email = str(payload.get("summary_email") or "").strip()
            return self.as_dict()

    def as_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "paper_trading": self.settings.paper_trading,
                "daily_loss_limit": self.settings.daily_loss_limit,
                "summary_email": self.settings.summary_email,
            }

    def add_trade(self, trade: Dict[str, Any]) -> None:
        record = TradeRecord(
            timestamp=datetime.utcnow().isoformat(),
            broker=str(trade.get("broker") or "unknown"),
            symbol=str(trade.get("symbol") or "NIFTY"),
            transaction_type=str(trade.get("transaction_type") or "BUY"),
            quantity=int(trade.get("quantity") or 0),
            status=str(trade.get("status") or "unknown"),
            pnl=float(trade.get("pnl") or 0.0),
            mode="paper" if self.settings.paper_trading else "live",
            details=trade,
        )
        with self._lock:
            self._trades.insert(0, record)
            self._trades = self._trades[:200]

    def recent_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.__dict__ for r in self._trades[:limit]]

    def analytics(self) -> Dict[str, Any]:
        with self._lock:
            trades = list(self._trades)
        closed = [t for t in trades if t.status.lower() in {"success", "filled", "paper-filled"}]
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl < 0]
        total_pnl = sum(t.pnl for t in closed)
        return {
            "total_trades": len(closed),
            "win_rate": (len(wins) / len(closed) * 100) if closed else 0.0,
            "avg_profit": (sum(t.pnl for t in wins) / len(wins)) if wins else 0.0,
            "avg_loss": (sum(t.pnl for t in losses) / len(losses)) if losses else 0.0,
            "today_pnl": total_pnl,
            "daily_loss_breached": self.settings.daily_loss_limit > 0 and abs(min(total_pnl, 0)) >= self.settings.daily_loss_limit,
        }


trading_state = TradingState()
