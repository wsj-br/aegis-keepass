"""Health check endpoint."""

from flask import Blueprint, jsonify

from aegis_keepass_lib import CRYPTO_AVAILABLE
from app._version import __version__

bp = Blueprint('health', __name__)


@bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'version': __version__, 'crypto': CRYPTO_AVAILABLE})
