"""Aegis-KeePass OTP Sync — Flask application factory."""

from __future__ import annotations

import os
import sys

from flask import Flask

from app._version import __version__
from app.system_theme import detect_system_theme, system_theme_from_environ

GITHUB_REPO_URL = "https://github.com/wsj-br/aegis-keepass"


def _resource_root() -> str | None:
    """Return PyInstaller extract dir when frozen; otherwise None."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS  # type: ignore[attr-defined]
    return None


def create_app() -> Flask:
    frozen_root = _resource_root()
    if frozen_root is not None:
        app = Flask(
            __name__,
            template_folder=os.path.join(frozen_root, 'app', 'templates'),
            static_folder=os.path.join(frozen_root, 'app', 'static'),
        )
    else:
        app = Flask(__name__)

    desktop_mode = os.environ.get('AK_DESKTOP') == '1'
    system_theme = None
    if desktop_mode:
        # Fail closed to dark when OS detection is unavailable.
        system_theme = system_theme_from_environ() or detect_system_theme() or 'dark'

    app.config.update(
        SECRET_KEY=os.environ.get('FLASK_SECRET_KEY', os.urandom(32)),
        MAX_CONTENT_LENGTH=int(os.environ.get('MAX_UPLOAD_BYTES', 50 * 1024 * 1024)),
        SESSION_COOKIE_NAME='ak_session',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict',
        SESSION_COOKIE_SECURE=False,
        SESSION_TIMEOUT_SECONDS=int(os.environ.get('SESSION_TIMEOUT_SECONDS', 1800)),
        MAX_IN_MEMORY_UPLOAD_BYTES=int(os.environ.get('MAX_IN_MEMORY_UPLOAD_BYTES', 32 * 1024 * 1024)),
        DESKTOP_MODE=desktop_mode,
        SYSTEM_THEME=system_theme,
    )

    @app.context_processor
    def inject_app_meta():
        return {
            'app_version': __version__,
            'github_repo_url': GITHUB_REPO_URL,
            'desktop_mode': app.config.get('DESKTOP_MODE', False),
            'system_theme': app.config.get('SYSTEM_THEME'),
        }

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
