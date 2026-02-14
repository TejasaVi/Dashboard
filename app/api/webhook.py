from collections import deque
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

webhook_bp = Blueprint("webhook", __name__)

_RECENT_SIGNALS = deque(maxlen=25)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@webhook_bp.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    current_app.logger.info("Webhook received: %s", data)

    action = str(data.get("action", "")).upper()
    symbol = data.get("symbol")
    price = data.get("price")

    if action not in {"BUY", "SELL"}:
        return jsonify({"status": "error", "error": "action must be BUY or SELL"}), 400

    signal = {
        "timestamp": _utc_now_iso(),
        "action": action,
        "symbol": symbol,
        "price": price,
        "execution": f"{action} signal accepted",  # Broker execution can be wired here.
    }
    _RECENT_SIGNALS.appendleft(signal)

    return jsonify({"status": "success", "signal": signal})


@webhook_bp.route("/api/webhook/events", methods=["GET"])
def webhook_events():
    return jsonify({"status": "success", "events": list(_RECENT_SIGNALS)})
