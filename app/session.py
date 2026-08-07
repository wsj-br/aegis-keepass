"""Per-session in-memory state with secure wipe lifecycle."""

from __future__ import annotations

import copy
import gc
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aegis_keepass_lib import AegisEntry, EntryMatcher, KeePassEntry, KeePassKdbx, MatchResult
from app.secure import EncryptedSpillStore, SecureBytes, WipeRegistry


@dataclass
class SessionData:
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_access: float = field(default_factory=time.time)
    aegis_entries: List[AegisEntry] = field(default_factory=list)
    keepass_entries: List[KeePassEntry] = field(default_factory=list)
    keepass_db: Optional[Any] = None
    keepass_master_password: Optional[SecureBytes] = None
    keepass_keyfile_bytes: Optional[SecureBytes] = None
    aegis_password: Optional[SecureBytes] = None
    pending_aegis: Optional[SecureBytes] = None
    pending_keepass: Optional[SecureBytes] = None
    pending_keyfile: Optional[SecureBytes] = None
    pending_download: Optional[SecureBytes] = None
    save_summary: Dict = field(default_factory=dict)
    match_assignments: Dict = field(default_factory=dict)
    initial_assignments: Dict = field(default_factory=dict)
    wipe_registry: WipeRegistry = field(default_factory=WipeRegistry)
    spill_store: Optional[EncryptedSpillStore] = None
    _wiped: bool = False

    def touch(self) -> None:
        self.last_access = time.time()

    def init_match_assignments(self, matches: List[MatchResult]) -> None:
        assignments = {}
        for entry in self.aegis_entries:
            assignments[entry.uuid] = {
                'keepass_uuid': None,
                'confidence': 0.0,
                'reason': '',
                'source': 'auto',
            }
        for match in matches:
            assignments[match.aegis_entry.uuid] = {
                'keepass_uuid': match.keepass_entry.uuid,
                'confidence': match.confidence,
                'reason': match.match_reason,
                'source': 'auto',
            }
        self.match_assignments = assignments
        self.initial_assignments = copy.deepcopy(assignments)

    def wipe(self) -> None:
        if self._wiped:
            return
        self._wiped = True

        for entry in self.aegis_entries:
            entry.wipe_secret()
        self.wipe_registry.wipe_all()

        if self.keepass_master_password is not None:
            self.keepass_master_password.wipe()
        if self.keepass_keyfile_bytes is not None:
            self.keepass_keyfile_bytes.wipe()

        for attr in (
            'aegis_password',
            'pending_aegis',
            'pending_keepass',
            'pending_keyfile',
            'pending_download',
        ):
            buf = getattr(self, attr)
            if buf is not None:
                buf.wipe()
            setattr(self, attr, None)

        if self.spill_store is not None:
            self.spill_store.wipe()

        self.aegis_entries = []
        self.keepass_entries = []
        self.keepass_db = None
        self.keepass_master_password = None
        self.keepass_keyfile_bytes = None
        self.match_assignments = {}
        self.initial_assignments = {}
        self.save_summary = {}
        gc.collect()


class SessionStore:
    """Thread-safe store for active browser sessions."""

    def __init__(self, timeout_seconds: int = 1800) -> None:
        self._timeout = timeout_seconds
        self._sessions: Dict[str, SessionData] = {}
        self._lock = threading.Lock()

    def create(self) -> SessionData:
        session_id = secrets.token_urlsafe(32)
        session = SessionData(session_id=session_id)
        with self._lock:
            self._purge_expired_locked()
            self._sessions[session_id] = session
        return session

    def get(self, session_id: Optional[str]) -> Optional[SessionData]:
        if not session_id:
            return None
        with self._lock:
            self._purge_expired_locked()
            session = self._sessions.get(session_id)
            if session is None or session._wiped:
                return None
            session.touch()
            return session

    def destroy(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is not None:
            session.wipe()

    def find_with_pending_download(self) -> Optional[SessionData]:
        """Return the first active session that has a built download ready.

        Used by the desktop shell (single-user) to save via a native dialog.
        """
        with self._lock:
            self._purge_expired_locked()
            for session in self._sessions.values():
                if session._wiped:
                    continue
                if session.pending_download is not None:
                    session.touch()
                    return session
        return None

    def _purge_expired_locked(self) -> None:
        now = time.time()
        expired = [
            sid for sid, session in self._sessions.items()
            if now - session.last_access > self._timeout
        ]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session is not None:
                session.wipe()

    @staticmethod
    def run_matcher(session: SessionData) -> None:
        matcher = EntryMatcher()
        matchable = KeePassKdbx.matchable_entries(session.keepass_entries)
        matches, _unmatched = matcher.find_matches(session.aegis_entries, matchable)
        session.init_match_assignments(matches)
