from flask import Blueprint, jsonify, request

from app.services.broker_engine import OrderRequest, broker_switcher, order_execution_engine, strategy_router
from app.services.fyers import fyers_client
from app.services.stoxkart import stoxkart_client
from app.services.zerodha import zerodha_client

brokers_bp = Blueprint("brokers", __name__)


@brokers_bp.route("/brokers/status", methods=["GET"])
def brokers_status():
    return jsonify({
        "active_broker": broker_switcher.active_broker,
        "brokers": order_execution_engine.broker_status(),
    })


@brokers_bp.route("/brokers/active", methods=["GET"])
def active_broker():
    return jsonify({"active_broker": broker_switcher.active_broker})


@brokers_bp.route("/brokers/switch", methods=["POST"])
def switch_broker():
    payload = request.get_json(silent=True) or {}
    broker = payload.get("broker")
    if not broker:
        return jsonify({"success": False, "error": "broker is required"}), 400

    try:
        active = broker_switcher.set_active(broker, list(order_execution_engine.brokers.keys()))
        return jsonify({"success": True, "active_broker": active})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@brokers_bp.route("/brokers/place-order", methods=["POST"])
def place_order_multi():
    payload = request.get_json(silent=True) or {}
    selected = payload.get("brokers") or []
    failover_enabled = bool(payload.get("failover_enabled", False))

    order = OrderRequest(
        index_name=payload.get("index_name", "NIFTY"),
        strike=payload.get("strike"),
        option_type=payload.get("option_type"),
        quantity=int(payload.get("quantity", 1)),
        transaction_type=payload.get("transaction_type", "BUY"),
        fyers_symbol=payload.get("fyers_symbol"),
        stoxkart_symbol=payload.get("stoxkart_symbol"),
        metadata=payload.get("metadata") or {},
    )

    result = order_execution_engine.execute_with_failover(
        order=order,
        selected_brokers=selected,
        failover_enabled=failover_enabled,
    )

    code = 200 if result.get("success") else 400
    return jsonify(result), code


@brokers_bp.route("/brokers/execute-strategy", methods=["POST"])
def execute_strategy():
    payload = request.get_json(silent=True) or {}
    strategy = payload.get("strategy", "single")
    selected = payload.get("brokers") or []
    failover_enabled = bool(payload.get("failover_enabled", False))

    try:
        routed_orders = strategy_router.route(strategy, payload)
        result = order_execution_engine.execute_strategy(
            orders=routed_orders,
            selected_brokers=selected,
            failover_enabled=failover_enabled,
        )
        code = 200 if result.get("success") else 400
        return jsonify(result), code
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@brokers_bp.route("/brokers/configure", methods=["POST"])
def configure_broker():
    payload = request.get_json(silent=True) or {}
    broker = (payload.get("broker") or "").lower().strip()

    if broker == "zerodha":
        api_key = payload.get("api_key", "")
        api_secret = payload.get("api_secret", "")
        access_token = payload.get("access_token", "")
        if not api_key or not api_secret:
            return jsonify({"success": False, "error": "api_key and api_secret are required for Zerodha"}), 400
        zerodha_client.configure(api_key=api_key, api_secret=api_secret, access_token=access_token)
    elif broker == "fyers":
        api_key = payload.get("api_key", "")
        api_secret = payload.get("api_secret", "")
        redirect_uri = payload.get("redirect_uri")
        access_token = payload.get("access_token", "")
        if not api_key or not api_secret:
            return jsonify({"success": False, "error": "api_key and api_secret are required for Fyers"}), 400
        fyers_client.configure(
            client_id=api_key,
            secret_key=api_secret,
            redirect_uri=redirect_uri,
            access_token=access_token,
        )
    elif broker == "stoxkart":
        api_key = payload.get("api_key", "")
        api_secret = payload.get("api_secret", "")
        redirect_uri = payload.get("redirect_uri")
        auth_base_url = payload.get("auth_base_url")
        token_url = payload.get("token_url")
        api_base_url = payload.get("api_base_url")
        access_token = payload.get("access_token", "")
        if not api_key or not api_secret:
            return jsonify({"success": False, "error": "api_key and api_secret are required for Stoxkart"}), 400
        stoxkart_client.configure(
            client_id=api_key,
            secret_key=api_secret,
            redirect_uri=redirect_uri,
            auth_base_url=auth_base_url,
            token_url=token_url,
            api_base_url=api_base_url,
            access_token=access_token,
        )
    else:
        return jsonify({"success": False, "error": "Unsupported broker"}), 400

    return jsonify({
        "success": True,
        "broker": broker,
        "configured": order_execution_engine.broker_status().get(broker, {}),
    })
