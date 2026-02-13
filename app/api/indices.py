from statistics import mean
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



@indices_bp.route("/advance-decline", methods=["GET"])
def advance_decline_ratio():
    try:
        data = nse_client.fetch_indices().get("all_indices") or []
        advances = 0
        declines = 0
        for item in data:
            change = item.get("percentChange")
            try:
                c = float(change)
            except (TypeError, ValueError):
                continue
            if c > 0:
                advances += 1
            elif c < 0:
                declines += 1

        ratio = round((advances / declines), 2) if declines else float(advances)
        return jsonify({"advances": advances, "declines": declines, "ratio": ratio})
    except Exception as e:
        return jsonify({"error": "Failed to fetch advance/decline", "details": str(e)}), 500


@indices_bp.route("/sector-rotation", methods=["GET"])
def sector_rotation_heatmap():
    try:
        data = nse_client.fetch_indices().get("all_indices") or []
        sectors = []
        for item in data:
            name = item.get("index") or ""
            if "NIFTY" not in name or name in {"NIFTY 50", "NIFTY BANK"}:
                continue
            try:
                pct = float(item.get("percentChange") or 0)
            except (TypeError, ValueError):
                pct = 0
            mood = "neutral"
            if pct > 0.5:
                mood = "bullish"
            elif pct < -0.5:
                mood = "bearish"
            sectors.append({"sector": name, "change": round(pct, 2), "mood": mood})

        avg_change = round(mean([s["change"] for s in sectors]), 2) if sectors else 0
        return jsonify({"sectors": sectors[:18], "average_change": avg_change})
    except Exception as e:
        return jsonify({"error": "Failed to fetch sector rotation", "details": str(e)}), 500
