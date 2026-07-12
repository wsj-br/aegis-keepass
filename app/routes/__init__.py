"""Health check endpoint."""

from flask import Blueprint, jsonify

from aegis_keepass_lib import CRYPTO_AVAILABLE

bp = Blueprint('health', __name__)


@bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'crypto': CRYPTO_AVAILABLE})
