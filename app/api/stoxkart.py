from flask import Blueprint, jsonify, redirect, request

from app.services.stoxkart import stoxkart_client

stoxkart_bp = Blueprint("stoxkart", __name__)


@stoxkart_bp.route("/stoxkart/status", methods=["GET"])
def stoxkart_status():
    if not stoxkart_client.is_configured:
        return jsonify({
            "configured": False,
            "connected": False,
            "message": "Provide STOXKART credentials (client_id, secret_key, auth_base_url)",
        })

    try:
        profile = stoxkart_client.profile() if stoxkart_client.is_connected else None
    except Exception:
        profile = None

    return jsonify({"configured": True, "connected": stoxkart_client.is_connected, "profile": profile})


@stoxkart_bp.route("/stoxkart/credentials", methods=["POST"])
def stoxkart_credentials():
    payload = request.get_json(silent=True) or {}
    client_id = payload.get("client_id", "")
    secret_key = payload.get("secret_key", "")
    if not client_id or not secret_key:
        return jsonify({"success": False, "error": "client_id and secret_key are required"}), 400

    stoxkart_client.update_credentials(
        client_id=client_id,
        secret_key=secret_key,
        redirect_uri=payload.get("redirect_uri"),
        auth_base_url=payload.get("auth_base_url"),
        token_url=payload.get("token_url"),
        api_base_url=payload.get("api_base_url"),
    )
    return jsonify({"success": True})


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
