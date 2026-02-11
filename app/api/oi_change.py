from flask import Blueprint, jsonify
from app.utils.oi_change import get_current_expiry_oi_change_pcr

oi_change_pcr_bp = Blueprint("oi_change_pcr", __name__)

@oi_change_pcr_bp.route("/oi-change", methods=["GET"])
def oi_change_pcr_check():
    return jsonify(get_current_expiry_oi_change_pcr())
