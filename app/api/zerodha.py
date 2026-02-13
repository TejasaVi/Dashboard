from flask import Blueprint, jsonify, redirect, request

from app.services.zerodha import zerodha_client

zerodha_bp = Blueprint("zerodha", __name__)


@zerodha_bp.route("/zerodha/status", methods=["GET"])
def zerodha_status():
    if not zerodha_client.is_configured:
        msg = "Set ZERODHA_API_KEY and ZERODHA_API_SECRET in environment"
        if not zerodha_client.sdk_available:
            msg = "kiteconnect SDK missing. Install with: pip install kiteconnect"
        return jsonify({"configured": False, "connected": False, "message": msg}), 200

    try:
        profile = zerodha_client.profile() if zerodha_client.is_connected else None
    except Exception:
        profile = None

    return jsonify({"configured": True, "connected": zerodha_client.is_connected, "profile": profile})


@zerodha_bp.route("/zerodha/credentials", methods=["POST"])
def zerodha_credentials():
    payload = request.get_json(silent=True) or {}
    api_key = payload.get("api_key", "")
    api_secret = payload.get("api_secret", "")
    if not api_key or not api_secret:
        return jsonify({"success": False, "error": "api_key and api_secret are required"}), 400
    zerodha_client.update_credentials(api_key=api_key, api_secret=api_secret)
    return jsonify({"success": True})


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
