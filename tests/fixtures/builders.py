"""Synthetic encrypted Aegis / KeePass fixtures for tests (generated at runtime)."""

from __future__ import annotations

import base64
import io
import json
import os
import secrets
from dataclasses import dataclass
from typing import List, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from pykeepass import create_database

# Well-known test credentials (not secrets; safe in source)
AEGIS_PASSWORD = "test-aegis-pass"
KEEPASS_PASSWORD = "test-keepass-pass"

# Fast scrypt for tests (decryptor accepts whatever n/r/p is in the slot)
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1

GITHUB_AEGIS_UUID = "11111111-1111-4111-8111-111111111111"
AWS_AEGIS_UUID = "22222222-2222-4222-8222-222222222222"
ORPHAN_AEGIS_UUID = "33333333-3333-4333-8333-333333333333"


@dataclass(frozen=True)
class VaultPair:
    """Paired synthetic vaults for upload / matching tests."""

    aegis_bytes: bytes
    aegis_password: str
    keepass_bytes: bytes
    keepass_password: str
    keyfile_bytes: Optional[bytes] = None
    github_aegis_uuid: str = GITHUB_AEGIS_UUID
    aws_aegis_uuid: str = AWS_AEGIS_UUID
    orphan_aegis_uuid: str = ORPHAN_AEGIS_UUID


def _aes_gcm_encrypt(plaintext: bytes, key: bytes, nonce: bytes) -> Tuple[bytes, bytes]:
    """Encrypt with AES-GCM; return (ciphertext_without_tag, tag)."""
    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    return ct_with_tag[:-16], ct_with_tag[-16:]


def _derive_key(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=n,
        r=r,
        p=p,
        backend=default_backend(),
    )
    return kdf.derive(password.encode("utf-8"))


def make_plaintext_aegis_vault(
    entries: Optional[List[dict]] = None,
) -> dict:
    """Return a decrypted-shaped Aegis vault dict."""
    if entries is None:
        entries = default_aegis_entries()
    return {
        "version": 1,
        "entries": entries,
    }


def default_aegis_entries() -> List[dict]:
    """Three Aegis entries: GitHub (matchable), AWS (UUID rematch), orphan."""
    return [
        {
            "type": "totp",
            "uuid": GITHUB_AEGIS_UUID,
            "name": "alice",
            "issuer": "GitHub",
            "info": {
                "secret": "JBSWY3DPEHPK3PXP",
                "algo": "SHA1",
                "digits": 6,
                "period": 30,
            },
        },
        {
            "type": "totp",
            "uuid": AWS_AEGIS_UUID,
            "name": "root",
            "issuer": "Amazon Web Services",
            "info": {
                "secret": "HXDMVJECJJWSRB3H",
                "algo": "SHA256",
                "digits": 6,
                "period": 30,
            },
        },
        {
            "type": "totp",
            "uuid": ORPHAN_AEGIS_UUID,
            "name": "nobody",
            "issuer": "UnmatchedServiceXYZ",
            "info": {
                "secret": "MFRGGZDFMZTWQ2LK",
                "algo": "SHA1",
                "digits": 6,
                "period": 30,
            },
        },
    ]


def make_encrypted_aegis_bytes(
    password: str = AEGIS_PASSWORD,
    entries: Optional[List[dict]] = None,
    *,
    n: int = SCRYPT_N,
    r: int = SCRYPT_R,
    p: int = SCRYPT_P,
) -> bytes:
    """Build encrypted Aegis backup JSON bytes compatible with AegisDecryptor."""
    plaintext = json.dumps(make_plaintext_aegis_vault(entries)).encode("utf-8")

    master_key = secrets.token_bytes(32)
    db_nonce = secrets.token_bytes(12)
    db_cipher, db_tag = _aes_gcm_encrypt(plaintext, master_key, db_nonce)

    salt = secrets.token_bytes(32)
    derived = _derive_key(password, salt, n, r, p)
    slot_nonce = secrets.token_bytes(12)
    slot_cipher, slot_tag = _aes_gcm_encrypt(master_key, derived, slot_nonce)

    vault = {
        "version": 1,
        "header": {
            "slots": [
                {
                    "type": 1,
                    "key": slot_cipher.hex(),
                    "key_params": {
                        "nonce": slot_nonce.hex(),
                        "tag": slot_tag.hex(),
                    },
                    "n": n,
                    "r": r,
                    "p": p,
                    "salt": salt.hex(),
                }
            ],
            "params": {
                "nonce": db_nonce.hex(),
                "tag": db_tag.hex(),
            },
        },
        "db": base64.b64encode(db_cipher).decode("ascii"),
    }
    return json.dumps(vault).encode("utf-8")


def make_kdbx_bytes(
    password: str = KEEPASS_PASSWORD,
    *,
    keyfile_bytes: Optional[bytes] = None,
    include_uuid_linked_aws: bool = True,
) -> bytes:
    """
    Build a tiny KeePass database with entries suited for matching tests.

    - GitHub: title/username match alice
    - Amazon AWS: optional AegisUUID marker for rematch
    - Unrelated: distractor entry
    """
    stream = io.BytesIO()
    keyfile_stream = None
    if keyfile_bytes is not None:
        keyfile_stream = io.BytesIO(keyfile_bytes)

    kp = create_database(stream, password=password, keyfile=keyfile_stream)

    kp.add_entry(
        kp.root_group,
        "GitHub",
        "alice",
        "password",
        url="https://github.com/login",
    )

    aws_notes = f"AegisUUID: {AWS_AEGIS_UUID}" if include_uuid_linked_aws else ""
    kp.add_entry(
        kp.root_group,
        "Amazon AWS",
        "root",
        "password",
        url="https://aws.amazon.com",
        notes=aws_notes,
    )

    kp.add_entry(
        kp.root_group,
        "Unrelated Bank",
        "bob",
        "password",
        url="https://example-bank.test",
    )

    out = io.BytesIO()
    kp.save(out)
    return out.getvalue()


def make_keyfile_bytes(size: int = 32) -> bytes:
    return secrets.token_bytes(size)


def make_vault_pair(
    *,
    with_keyfile: bool = False,
    include_uuid_linked_aws: bool = True,
) -> VaultPair:
    """Return a matching Aegis + KeePass pair for integration tests."""
    keyfile = make_keyfile_bytes() if with_keyfile else None
    return VaultPair(
        aegis_bytes=make_encrypted_aegis_bytes(),
        aegis_password=AEGIS_PASSWORD,
        keepass_bytes=make_kdbx_bytes(
            keyfile_bytes=keyfile,
            include_uuid_linked_aws=include_uuid_linked_aws,
        ),
        keepass_password=KEEPASS_PASSWORD,
        keyfile_bytes=keyfile,
    )


def write_temp_kdbx(path: str, password: str = KEEPASS_PASSWORD) -> None:
    """Write a kdbx file to disk (helper for optional file-based tests)."""
    data = make_kdbx_bytes(password=password)
    with open(path, "wb") as fh:
        fh.write(data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
