from flask import Blueprint, jsonify, redirect, request

from app.services.fyers import fyers_client

fyers_bp = Blueprint("fyers", __name__)


@fyers_bp.route("/fyers/status", methods=["GET"])
def fyers_status():
    if not fyers_client.is_configured:
        return jsonify({
            "configured": False,
            "connected": False,
            "message": "Set FYERS_CLIENT_ID, FYERS_SECRET_KEY, FYERS_REDIRECT_URI",
        })

    try:
        profile = fyers_client.profile() if fyers_client.is_connected else None
    except Exception:
        profile = None

    return jsonify({"configured": True, "connected": fyers_client.is_connected, "profile": profile})


@fyers_bp.route("/fyers/login-url", methods=["GET"])
def fyers_login_url():
    try:
        return jsonify({"login_url": fyers_client.login_url()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@fyers_bp.route("/fyers/callback", methods=["GET"])
def fyers_callback():
    auth_code = request.args.get("auth_code")
    if not auth_code:
        return "No auth_code received", 400

    try:
        fyers_client.save_session(auth_code)
    except Exception as exc:
        return f"Error while generating session: {exc}", 400

    return redirect("/?fyers=connected")


@fyers_bp.route("/fyers/profile", methods=["GET"])
def fyers_profile():
    try:
        return jsonify(fyers_client.profile())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
