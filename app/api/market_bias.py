from flask import Blueprint, jsonify

from app.api.vix import get_india_vix
from app.api.mmi import fetch_mmi
from app.api.pcr import get_current_expiry_pcr
from app.api.rsi import get_nifty_rsi
from app.services.market_bias import option_signal_engine
from app.utils.nse_client import NSEClient
from app.utils.oi_change import get_current_expiry_oi_change_pcr


def define_market_bias():
    # ---- Fetch inputs ----
    vix = get_india_vix()
    vix = vix["value"]
    mmi_zone = fetch_mmi()
    mmi_zone = mmi_zone["zone"]
    pcr = get_current_expiry_pcr()
    pcr = pcr["pcr"]

    rsi60_data = get_nifty_rsi(interval="60m")
    rsi15_data = get_nifty_rsi(interval="15m")

    rsi60 = float(rsi60_data["rsi_value"])
    rsi15 = float(rsi15_data["rsi_value"])
    
    nse_client = NSEClient()
    data = nse_client.fetch_indices()
    # ---- Bias Engine ----
    nifty_spot = data['NIFTY50']
    oi_change = get_current_expiry_oi_change_pcr()
    oi_change_pcr = oi_change['oi_change_pcr']
    signal = option_signal_engine(
        spot=nifty_spot,
        mmi=mmi_zone,
        rsi15=rsi15,
        rsi60=rsi60,
        pcr=pcr,
        oi_change_pcr=oi_change_pcr,
        vix=vix,
        expiry_type="WEEKLY",
    )
    return jsonify(signal)


marketbias_bp = Blueprint("market_bias", __name__)


@marketbias_bp.route("/marketbias", methods=["GET"])
def bias_check():
    return define_market_bias()
