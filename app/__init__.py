from flask import Flask, render_template

from app.config import Config
from app.api.vix import vix_bp
from app.api.mmi import mmi_bp
from app.api.pcr import pcr_bp
from app.api.rsi import rsi_bp
from app.api.indices import indices_bp
from app.api.market_bias import marketbias_bp
from app.api.oi_change import oi_change_pcr_bp
from app.api.nifty_mas import nifty_avgs_bp
from app.api.macd import macd_bp
from app.api.zerodha import zerodha_bp, zerodha_public_bp
from app.api.fyers import fyers_bp
from app.api.brokers import brokers_bp
from app.api.stoxkart import stoxkart_bp
from app.api.market_extras import market_extras_bp
from app.logging_setup import configure_file_logging, patch_requests_logging

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    configure_file_logging(app)
    patch_requests_logging()

    @app.route("/")
    def dashboard():
        return render_template("index.html")

    # Register blueprints
    app.register_blueprint(vix_bp, url_prefix="/api")
    app.register_blueprint(pcr_bp, url_prefix="/api")
    app.register_blueprint(rsi_bp, url_prefix="/api")
    app.register_blueprint(mmi_bp, url_prefix="/api")
    app.register_blueprint(marketbias_bp, url_prefix="/api")
    app.register_blueprint(indices_bp, url_prefix="/api")
    app.register_blueprint(oi_change_pcr_bp, url_prefix="/api")
    app.register_blueprint(nifty_avgs_bp, url_prefix="/api")
    app.register_blueprint(macd_bp, url_prefix="/api")
    app.register_blueprint(zerodha_bp, url_prefix="/api")
    app.register_blueprint(zerodha_public_bp)
    app.register_blueprint(fyers_bp, url_prefix="/api")
    app.register_blueprint(brokers_bp, url_prefix="/api")
    app.register_blueprint(stoxkart_bp, url_prefix="/api")
    app.register_blueprint(market_extras_bp, url_prefix="/api")
    return app
