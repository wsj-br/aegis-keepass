"""Unit tests for SecureBytes, WipeRegistry, and SessionStore wipe."""

from __future__ import annotations

from app.secure import SecureBytes, WipeRegistry
from app.session import SessionStore


class TestSecureBytes:
    def test_wipe_clears_buffer(self):
        buf = SecureBytes("secret-value")
        assert buf.decode() == "secret-value"
        buf.wipe()
        assert len(buf) == 0
        assert bytes(buf) == b""

    def test_context_manager_wipes(self):
        with SecureBytes("temp") as buf:
            assert buf.decode() == "temp"
        # already wiped via __exit__
        assert len(buf) == 0

    def test_registry_wipe_all(self):
        registry = WipeRegistry()
        a = SecureBytes("one", registry=registry)
        b = SecureBytes("two", registry=registry)
        registry.wipe_all()
        assert len(a) == 0
        assert len(b) == 0

    def test_double_wipe_safe(self):
        buf = SecureBytes("x")
        buf.wipe()
        buf.wipe()
        assert len(buf) == 0


class TestSessionStore:
    def test_create_get_destroy(self):
        store = SessionStore(timeout_seconds=3600)
        session = store.create()
        sid = session.session_id
        assert store.get(sid) is session

        session.aegis_password = SecureBytes("pw", registry=session.wipe_registry)
        store.destroy(sid)
        assert store.get(sid) is None

    def test_timeout_purges(self, monkeypatch):
        store = SessionStore(timeout_seconds=1)
        session = store.create()
        sid = session.session_id
        # Force last_access into the past
        session.last_access = 0
        assert store.get(sid) is None
