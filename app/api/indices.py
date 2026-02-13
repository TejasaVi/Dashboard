from flask import Blueprint, jsonify
from app.utils.nse_client import NSEClient
from app.utils.bse_client import fetch_sensex

indices_bp = Blueprint("indices", __name__)

# Single client instance (reuse session & cookies)
nse_client = NSEClient()


@indices_bp.route("/indices", methods=["GET"])
def get_indices():
    try:
        data = nse_client.fetch_indices()
        bse_value = fetch_sensex()
        data['SENSEX'] = bse_value['value']
        return jsonify(data)

    except Exception as e:
        return jsonify({
            "error": "Failed to fetch NSE indices",
            "details": str(e)
        }), 500

