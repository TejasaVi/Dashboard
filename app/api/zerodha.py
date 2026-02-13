from flask import Blueprint, jsonify, redirect, request

from app.services.zerodha import zerodha_client

zerodha_bp = Blueprint("zerodha", __name__)


@zerodha_bp.route("/zerodha/status", methods=["GET"])
def zerodha_status():
    if not zerodha_client.is_configured:
        return jsonify({
            "configured": False,
            "connected": False,
            "message": "Set ZERODHA_API_KEY and ZERODHA_API_SECRET in environment",
        }), 200

    try:
        profile = zerodha_client.profile() if zerodha_client.is_connected else None
    except Exception:
        profile = None

    return jsonify({
        "configured": True,
        "connected": zerodha_client.is_connected,
        "profile": profile,
    })


@zerodha_bp.route("/zerodha/login-url", methods=["GET"])
def zerodha_login_url():
    try:
        return jsonify({"login_url": zerodha_client.login_url()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@zerodha_bp.route("/zerodha/callback", methods=["GET"])
def zerodha_callback():
    request_token = request.args.get("request_token")
    if not request_token:
        return "No request_token received", 400

    try:
        zerodha_client.save_session(request_token)
    except Exception as exc:
        return f"Error while generating session: {exc}", 400

    return redirect("/?zerodha=connected")


@zerodha_bp.route("/zerodha/profile", methods=["GET"])
def zerodha_profile():
    try:
        return jsonify(zerodha_client.profile())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@zerodha_bp.route("/zerodha/place-order", methods=["POST"])
def place_order():
    payload = request.get_json(silent=True) or {}

    index_name = payload.get("index_name", "NIFTY")
    strike = payload.get("strike")
    option_type = payload.get("option_type")
    quantity = payload.get("quantity", 1)
    transaction_type = payload.get("transaction_type", "BUY")

    if strike is None or option_type not in {"CE", "PE"}:
        return jsonify({"error": "strike and option_type (CE/PE) are required"}), 400

    try:
        result = zerodha_client.place_option_order(
            index_name=index_name,
            strike=int(strike),
            option_type=option_type,
            quantity=int(quantity),
            transaction_type=transaction_type,
        )
        return jsonify({"success": True, "order": result})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
