"""Aegis-KeePass OTP Sync — Flask application factory."""

from __future__ import annotations

import os

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', os.urandom(32)),
        MAX_CONTENT_LENGTH=int(os.environ.get('MAX_UPLOAD_BYTES', 50 * 1024 * 1024)),
        SESSION_COOKIE_NAME='ak_session',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_SECURE=False,
        SESSION_TIMEOUT_SECONDS=int(os.environ.get('SESSION_TIMEOUT_SECONDS', 1800)),
        MAX_IN_MEMORY_UPLOAD_BYTES=int(os.environ.get('MAX_IN_MEMORY_UPLOAD_BYTES', 32 * 1024 * 1024)),
    )

    from app.routes.health import bp as health_bp
    from app.routes.upload import bp as upload_bp
    from app.routes.review import bp as review_bp
    from app.session import SessionStore

    app.extensions['session_store'] = SessionStore(
        timeout_seconds=app.config['SESSION_TIMEOUT_SECONDS']
    )

    app.register_blueprint(health_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(review_bp)

    @app.after_request
    def add_cache_headers(response):
        if response.content_type and (
            'text/html' in response.content_type
            or 'application/json' in response.content_type
        ):
            response.headers['Cache-Control'] = 'no-store'
        return response

    return app
