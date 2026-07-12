"""Session cookie helpers."""

from __future__ import annotations

from functools import wraps
from typing import Callable, Optional

from flask import current_app, g, jsonify, make_response, request

from app.session import SessionData, SessionStore


def get_session_store() -> SessionStore:
    return current_app.extensions['session_store']


def get_current_session() -> Optional[SessionData]:
    return getattr(g, 'session_data', None)


def set_session_cookie(response, session_id: str):
    response.set_cookie(
        current_app.config['SESSION_COOKIE_NAME'],
        session_id,
        httponly=True,
        samesite='Strict',
        secure=current_app.config['SESSION_COOKIE_SECURE'],
        max_age=current_app.config['SESSION_TIMEOUT_SECONDS'],
    )
    return response


def clear_session_cookie(response):
    response.delete_cookie(current_app.config['SESSION_COOKIE_NAME'])
    return response


def require_session(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        session_id = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'])
        session = get_session_store().get(session_id)
        if session is None:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Session expired or not found'}), 401
            from flask import redirect, url_for
            return redirect(url_for('upload.index'))
        g.session_data = session
        return view(*args, **kwargs)
    return wrapper


def session_required_api(view: Callable):
    @wraps(view)
    def wrapper(*args, **kwargs):
        session_id = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'])
        session = get_session_store().get(session_id)
        if session is None:
            return jsonify({'error': 'Session expired or not found'}), 401
        g.session_data = session
        return view(*args, **kwargs)
    return wrapper
