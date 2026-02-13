from flask import Blueprint, jsonify

market_extras_bp = Blueprint('market_extras', __name__)


@market_extras_bp.route('/advance-decline', methods=['GET'])
def advance_decline():
    advanced = 28
    declined = 22
    ratio = round(advanced / max(declined, 1), 2)
    sentiment = 'Bullish breadth' if ratio > 1 else 'Weak breadth'
    return jsonify({
        'advanced': advanced,
        'declined': declined,
        'ratio': ratio,
        'sentiment': sentiment,
    })


@market_extras_bp.route('/sector-rotation', methods=['GET'])
def sector_rotation():
    sectors = [
        {'name': 'Banking', 'change': 1.2},
        {'name': 'IT', 'change': -0.6},
        {'name': 'Auto', 'change': 0.9},
        {'name': 'Pharma', 'change': 0.3},
        {'name': 'FMCG', 'change': -0.2},
        {'name': 'Energy', 'change': 1.6},
    ]
    mood = 'Risk-on rotation' if any(s['change'] > 1 for s in sectors) else 'Balanced rotation'
    return jsonify({'sectors': sectors, 'mood': mood})
