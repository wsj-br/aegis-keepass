"""Secure memory handling: mutable buffers with overwrite-on-wipe."""

from __future__ import annotations

import ctypes
import gc
import os
import secrets
import shutil
import subprocess
import tempfile
import weakref
from typing import Optional, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class WipeRegistry:
    """Tracks live SecureBytes instances for session-wide wipe."""

    def __init__(self) -> None:
        self._items: weakref.WeakSet = weakref.WeakSet()

    def register(self, item: SecureBytes) -> None:
        self._items.add(item)

    def wipe_all(self) -> None:
        for item in list(self._items):
            item.wipe()


def secure_wipe(buf: bytearray) -> None:
    """Overwrite mutable buffer with random data, then zeros, before release."""
    n = len(buf)
    if n == 0:
        return
    buf[:] = secrets.token_bytes(n)
    ctypes.memset((ctypes.c_char * n).from_buffer(buf), 0, n)
    buf.clear()


class SecureBytes:
    """Mutable byte buffer that overwrites contents on wipe."""

    __slots__ = ('_buf', '_registry', '_wiped', '__weakref__')

    def __init__(
        self,
        data: Union[bytes, bytearray, str, None] = None,
        *,
        registry: Optional[WipeRegistry] = None,
        encoding: str = 'utf-8',
    ) -> None:
        self._wiped = False
        self._registry = registry
        if data is None:
            self._buf = bytearray()
        elif isinstance(data, str):
            self._buf = bytearray(data.encode(encoding))
        elif isinstance(data, bytearray):
            self._buf = data
        else:
            self._buf = bytearray(data)
        if registry is not None:
            registry.register(self)

    def __len__(self) -> int:
        return len(self._buf)

    def __bytes__(self) -> bytes:
        return bytes(self._buf)

    def view(self) -> memoryview:
        return memoryview(self._buf)

    def extend(self, data: bytes) -> None:
        self._buf.extend(data)

    def decode(self, encoding: str = 'utf-8') -> str:
        return self._buf.decode(encoding)

    def wipe(self) -> None:
        if self._wiped:
            return
        secure_wipe(self._buf)
        self._wiped = True

    def __enter__(self) -> SecureBytes:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.wipe()

    def __del__(self) -> None:
        try:
            self.wipe()
        except Exception:
            pass


def shred_file(path: str, passes: int = 3) -> None:
    """Securely overwrite and delete a file."""
    if not os.path.isfile(path):
        return
    try:
        size = os.path.getsize(path)
        with open(path, 'r+b') as fh:
            for _ in range(passes):
                fh.seek(0)
                fh.write(secrets.token_bytes(size))
                fh.flush()
                os.fsync(fh.fileno())
            fh.seek(0)
            fh.write(b'\x00' * size)
            fh.flush()
            os.fsync(fh.fileno())
        os.remove(path)
    except OSError:
        try:
            subprocess.run(
                ['shred', '-u', '-z', path],
                check=False,
                capture_output=True,
            )
        except (OSError, FileNotFoundError):
            try:
                os.remove(path)
            except OSError:
                pass


class EncryptedSpillStore:
    """Optional encrypted on-disk spill for large uploads."""

    def __init__(self, session_key: bytearray, temp_dir: str) -> None:
        self._key = session_key
        self._temp_dir = temp_dir
        self._files: list[str] = []

    @classmethod
    def create(cls) -> EncryptedSpillStore:
        key = bytearray(secrets.token_bytes(32))
        temp_dir = tempfile.mkdtemp(prefix='ak_', dir='/tmp')
        return cls(key, temp_dir)

    def store(self, name: str, data: bytes) -> str:
        aes = AESGCM(bytes(self._key))
        nonce = secrets.token_bytes(12)
        ciphertext = aes.encrypt(nonce, data, None)
        path = os.path.join(self._temp_dir, f'{name}.enc')
        with open(path, 'wb') as fh:
            fh.write(nonce)
            fh.write(ciphertext)
        os.chmod(path, 0o600)
        self._files.append(path)
        return path

    def load(self, path: str) -> SecureBytes:
        with open(path, 'rb') as fh:
            raw = fh.read()
        nonce = raw[:12]
        ciphertext = raw[12:]
        aes = AESGCM(bytes(self._key))
        plaintext = aes.decrypt(nonce, ciphertext, None)
        return SecureBytes(plaintext)

    def wipe(self) -> None:
        for path in self._files:
            shred_file(path)
        self._files.clear()
        if os.path.isdir(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
            except OSError:
                pass
        secure_wipe(self._key)
        gc.collect()
