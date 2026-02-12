from flask import Blueprint, jsonify

from app.services.moving_avgs import get_nifty_analysis



nifty_avgs_bp = Blueprint("nifty_avgs", __name__)


@nifty_avgs_bp.route("/niftyavgs", methods=["GET"])
def nifty_analysis_api():
    """API endpoint for Nifty 50 analysis"""
    analysis = get_nifty_analysis()
    return jsonify(analysis)
