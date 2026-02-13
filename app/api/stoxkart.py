from flask import Blueprint, jsonify, redirect, request

from app.services.stoxkart import stoxkart_client

stoxkart_bp = Blueprint("stoxkart", __name__)


@stoxkart_bp.route("/stoxkart/status", methods=["GET"])
def stoxkart_status():
    if not stoxkart_client.is_configured:
        return jsonify({
            "configured": False,
            "connected": False,
            "message": "Set STOXKART_CLIENT_ID, STOXKART_SECRET_KEY, STOXKART_REDIRECT_URI, STOXKART_AUTH_BASE_URL",
        })

    try:
        profile = stoxkart_client.profile() if stoxkart_client.is_connected else None
    except Exception:
        profile = None

    return jsonify({"configured": True, "connected": stoxkart_client.is_connected, "profile": profile})


@stoxkart_bp.route("/stoxkart/login-url", methods=["GET"])
def stoxkart_login_url():
    try:
        return jsonify({"login_url": stoxkart_client.login_url()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@stoxkart_bp.route("/stoxkart/callback", methods=["GET"])
def stoxkart_callback():
    code = request.args.get("code")
    access_token = request.args.get("access_token")
    if not code and not access_token:
        return "No code/access_token received", 400

    try:
        stoxkart_client.save_session(code=code, access_token=access_token)
    except Exception as exc:
        return f"Error while generating session: {exc}", 400

    return redirect("/?stoxkart=connected")


@stoxkart_bp.route("/stoxkart/profile", methods=["GET"])
def stoxkart_profile():
    try:
        return jsonify(stoxkart_client.profile())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400
