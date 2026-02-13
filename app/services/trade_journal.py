from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class RiskConfig:
    daily_loss_limit: float = 0.0
    paper_trading: bool = True
    trailing_stop_pct: float = 2.0
    summary_email: str = ""


class TradeJournal:
    def __init__(self) -> None:
        self._lock = Lock()
        self._trades: List[Dict[str, Any]] = []
        self._cfg = RiskConfig()

    def config(self) -> Dict[str, Any]:
        with self._lock:
            return asdict(self._cfg)

    def update_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if "daily_loss_limit" in payload:
                self._cfg.daily_loss_limit = max(0.0, float(payload.get("daily_loss_limit") or 0.0))
            if "paper_trading" in payload:
                self._cfg.paper_trading = bool(payload.get("paper_trading"))
            if "trailing_stop_pct" in payload:
                self._cfg.trailing_stop_pct = max(0.1, float(payload.get("trailing_stop_pct") or 0.1))
            if "summary_email" in payload:
                self._cfg.summary_email = (payload.get("summary_email") or "").strip()
            return asdict(self._cfg)

    def is_paper_trading(self) -> bool:
        with self._lock:
            return self._cfg.paper_trading

    def trailing_stop_pct(self) -> float:
        with self._lock:
            return self._cfg.trailing_stop_pct

    def log_trade(self, trade: Dict[str, Any]) -> None:
        with self._lock:
            item = dict(trade)
            item.setdefault("timestamp", datetime.now(tz=IST).isoformat())
            self._trades.append(item)
            self._trades = self._trades[-500:]

    def recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self._trades[-limit:]))

    def analytics(self) -> Dict[str, Any]:
        with self._lock:
            trades = list(self._trades)

        realized = [t for t in trades if isinstance(t.get("pnl"), (int, float))]
        wins = [t for t in realized if t.get("pnl", 0) > 0]
        losses = [t for t in realized if t.get("pnl", 0) < 0]
        total = len(realized)
        win_rate = (len(wins) / total * 100.0) if total else 0.0
        avg_profit = (sum(t["pnl"] for t in wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(t["pnl"] for t in losses) / len(losses)) if losses else 0.0
        gross = sum(t.get("pnl", 0.0) for t in realized)

        adv = sum(1 for t in trades if t.get("symbol", "").endswith("CE")) + 1
        dec = sum(1 for t in trades if t.get("symbol", "").endswith("PE")) + 1

        return {
            "executed_trades": len(trades),
            "closed_trades": total,
            "win_rate": round(win_rate, 2),
            "avg_profit": round(avg_profit, 2),
            "avg_loss": round(avg_loss, 2),
            "net_pnl": round(gross, 2),
            "advance_decline_ratio": round(adv / dec, 2),
            "live_pnl": round(gross, 2),
            "daily_summary_email": {
                "configured_email": self.config().get("summary_email", ""),
                "status": "configured" if self.config().get("summary_email") else "not_configured",
            },
        }


trade_journal = TradeJournal()
