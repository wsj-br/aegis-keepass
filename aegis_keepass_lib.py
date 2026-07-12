#!/usr/bin/env python3
"""
Shared library for Aegis-KeePass OTP Sync.

Parsers, entry matching, and applying imported OTP data to KeePass databases.
"""

import base64
import io
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

from rapidfuzz import fuzz

from app.secure import SecureBytes, WipeRegistry, secure_wipe

try:
    from pykeepass import PyKeePass
    from pykeepass.exceptions import CredentialsError
    PYKEEPASS_AVAILABLE = True
except ImportError:
    PyKeePass = None  # type: ignore[misc, assignment]
    CredentialsError = Exception  # type: ignore[misc, assignment]
    PYKEEPASS_AVAILABLE = False

# Optional cryptography library for Aegis decryption
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    AESGCM = None
    Scrypt = None


class AegisDecryptor:
    """Decrypts Aegis Authenticator encrypted backup files."""

    @staticmethod
    def is_encrypted_vault(data: dict) -> bool:
        """Check if parsed JSON is an encrypted Aegis backup."""
        return isinstance(data, dict) and 'header' in data and 'db' in data

    @staticmethod
    def is_encrypted(filepath: str) -> bool:
        """Check if a file is an encrypted Aegis backup."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AegisDecryptor.is_encrypted_vault(data)
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError):
            return False

    @staticmethod
    def is_encrypted_bytes(data: bytes) -> bool:
        """Check if raw bytes are an encrypted Aegis backup."""
        try:
            vault = json.loads(data.decode('utf-8'))
            return AegisDecryptor.is_encrypted_vault(vault)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False

    @staticmethod
    def _dict_drill(obj: dict, *keys: str) -> Any:
        """Safely traverse nested dict like Ruby's drill."""
        node = obj
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        return node

    @staticmethod
    def _hex_to_bytes(hex_str: str) -> bytes:
        """Convert hex string to bytes."""
        return bytes.fromhex(hex_str)

    @staticmethod
    def _derive_key(password: Union[str, bytes, bytearray, SecureBytes], salt: bytes, n: int, r: int, p: int, length: int = 32) -> bytes:
        """Derive key using scrypt KDF."""
        if Scrypt is None:
            raise RuntimeError("cryptography library required for decryption. Run: pip install cryptography")
        if isinstance(password, SecureBytes):
            password_bytes = bytes(password)
        elif isinstance(password, str):
            password_bytes = password.encode('utf-8')
        else:
            password_bytes = bytes(password)
        kdf = Scrypt(
            salt=salt,
            length=length,
            n=n,
            r=r,
            p=p,
            backend=default_backend()
        )
        return kdf.derive(password_bytes)

    @staticmethod
    def _aes_gcm_decrypt(ciphertext: bytes, key: bytes, iv: bytes, auth_tag: bytes) -> bytes:
        """Decrypt using AES-256-GCM."""
        if AESGCM is None:
            raise RuntimeError("cryptography library required for decryption. Run: pip install cryptography")
        aesgcm = AESGCM(key)
        # AES-GCM expects ciphertext + tag combined
        ciphertext_with_tag = ciphertext + auth_tag
        return aesgcm.decrypt(iv, ciphertext_with_tag, None)

    @staticmethod
    def _decrypt_vault(data: dict, password: Union[str, bytes, bytearray, SecureBytes]) -> dict:
        """Decrypt parsed vault JSON with the given password."""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError(
                "cryptography library required for Aegis decryption. "
                "Install with: pip install cryptography"
            )

        if not isinstance(data, dict):
            raise ValueError("Invalid vault file: top-level is not an object")

        slots = AegisDecryptor._dict_drill(data, 'header', 'slots')
        if not isinstance(slots, list):
            raise ValueError("Invalid vault file: no valid password slots found")

        password_slots = []
        for slot in slots:
            if not isinstance(slot, dict):
                continue
            if slot.get('type') != 1:
                continue
            if not isinstance(slot.get('key'), str):
                continue
            if not isinstance(AegisDecryptor._dict_drill(slot, 'key_params', 'nonce'), str):
                continue
            if not isinstance(AegisDecryptor._dict_drill(slot, 'key_params', 'tag'), str):
                continue
            if not isinstance(slot.get('n'), int):
                continue
            if not isinstance(slot.get('r'), int):
                continue
            if not isinstance(slot.get('p'), int):
                continue
            if not isinstance(slot.get('salt'), str):
                continue
            password_slots.append(slot)

        if not password_slots:
            raise ValueError("Invalid vault file: no valid password slots found")

        db = data.get('db')
        if not isinstance(db, str):
            raise ValueError("Invalid vault file: no db found")
        cipher_text = base64.b64decode(db)

        iv_hex = AegisDecryptor._dict_drill(data, 'header', 'params', 'nonce')
        if not isinstance(iv_hex, str):
            raise ValueError("Invalid vault file: no initialization vector found")
        iv = AegisDecryptor._hex_to_bytes(iv_hex)

        auth_tag_hex = AegisDecryptor._dict_drill(data, 'header', 'params', 'tag')
        if not isinstance(auth_tag_hex, str):
            raise ValueError("Invalid vault file: no authentication tag found")
        auth_tag = AegisDecryptor._hex_to_bytes(auth_tag_hex)

        master_key = None
        meta_key_buf = bytearray(32)

        for slot in password_slots:
            try:
                salt = AegisDecryptor._hex_to_bytes(slot['salt'])
                n = slot['n']
                r = slot['r']
                p = slot['p']

                derived = AegisDecryptor._derive_key(password, salt, n, r, p, 32)
                meta_key_buf[:] = derived

                slot_key = AegisDecryptor._hex_to_bytes(slot['key'])
                slot_nonce = AegisDecryptor._hex_to_bytes(slot['key_params']['nonce'])
                slot_tag = AegisDecryptor._hex_to_bytes(slot['key_params']['tag'])

                master_key = AegisDecryptor._aes_gcm_decrypt(
                    slot_key, bytes(meta_key_buf), slot_nonce, slot_tag
                )
                break

            except Exception:
                continue

        secure_wipe(meta_key_buf)

        if master_key is None:
            raise RuntimeError("Failed to decrypt master key. Wrong password?")

        master_key_buf = bytearray(master_key)
        try:
            plaintext = AegisDecryptor._aes_gcm_decrypt(
                cipher_text, bytes(master_key_buf), iv, auth_tag
            )
            return json.loads(plaintext.decode('utf-8'))
        except Exception as e:
            raise RuntimeError(f"Failed to decrypt vault. Vault may be corrupted: {e}") from e
        finally:
            secure_wipe(master_key_buf)

    @staticmethod
    def decrypt_data(data: bytes, password: Union[bytes, bytearray, SecureBytes]) -> dict:
        """Decrypt encrypted Aegis backup bytes."""
        vault = json.loads(data.decode('utf-8'))
        if not AegisDecryptor.is_encrypted_vault(vault):
            raise ValueError("Not an encrypted Aegis backup")
        return AegisDecryptor._decrypt_vault(vault, password)

    @staticmethod
    def decrypt_file(filepath: str, password: str) -> dict:
        """Decrypt an Aegis backup file and return the decrypted JSON data."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return AegisDecryptor._decrypt_vault(data, password)


@dataclass
class AegisEntry:
    """Represents a TOTP entry from Aegis."""
    uuid: str
    name: str
    issuer: str
    secret: SecureBytes
    algo: str
    digits: int
    period: int
    entry_type: str = "totp"

    def secret_text(self) -> str:
        """Decode TOTP secret for KeePass output (transient str)."""
        return self.secret.decode('utf-8')

    def wipe_secret(self) -> None:
        self.secret.wipe()

    @property
    def full_identifier(self) -> str:
        """Combined issuer and name for matching."""
        return f"{self.issuer} {self.name}".strip()

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        if self.name and self.issuer:
            return f"{self.issuer}: {self.name}"
        return self.issuer or self.name or "Unknown"


@dataclass
class KeePassEntry:
    """Represents an entry from a KeePass database."""
    uuid: str
    title: str
    username: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    group_path: Optional[str] = None
    in_recycle_bin: bool = False
    in_history: bool = False
    strings: Dict[str, str] = field(default_factory=dict)
    py_entry: Optional[Any] = field(default=None, repr=False)

    @property
    def is_matchable(self) -> bool:
        """Whether this entry may be used for Aegis matching/selection."""
        return not self.in_recycle_bin and not self.in_history

    @property
    def location_display(self) -> str:
        """Full path: group hierarchy plus entry title."""
        if self.group_path:
            return f"{self.group_path} / {self.title}"
        return self.title
    
    def has_otp(self) -> bool:
        """Check if entry already has OTP configuration."""
        return "TimeOtp-Secret-Base32" in self.strings
    
    def get_aegis_uuid(self) -> Optional[str]:
        """Extract Aegis UUID from notes if present."""
        if not self.notes:
            return None
        match = re.search(r'AegisUUID:\s*([a-f0-9-]+)', self.notes, re.IGNORECASE)
        return match.group(1) if match else None


@dataclass
class MatchResult:
    """Represents a match between Aegis and KeePass entries."""
    aegis_entry: AegisEntry
    keepass_entry: KeePassEntry
    confidence: float
    match_reason: str


class AegisParser:
    """Parser for Aegis JSON files (both encrypted and decrypted)."""

    # Mapping from Aegis algorithm names to KeePass HMAC algorithm names
    ALGO_MAP = {
        'SHA1': 'HMAC-SHA-1',
        'SHA256': 'HMAC-SHA-256',
        'SHA512': 'HMAC-SHA-512'
    }

    @staticmethod
    def _entries_from_vault(data: dict, registry: Optional[WipeRegistry] = None) -> List[AegisEntry]:
        entries = []
        for entry_data in data.get('entries', []):
            info = entry_data.get('info', {})
            aegis_algo = info.get('algo', 'SHA1')
            keepass_algo = AegisParser.ALGO_MAP.get(aegis_algo, 'HMAC-SHA-1')

            entries.append(AegisEntry(
                uuid=entry_data.get('uuid', ''),
                name=entry_data.get('name', ''),
                issuer=entry_data.get('issuer', ''),
                secret=SecureBytes(info.get('secret', ''), registry=registry),
                algo=keepass_algo,
                digits=info.get('digits', 6),
                period=info.get('period', 30),
                entry_type=entry_data.get('type', 'totp'),
            ))
        return entries

    @staticmethod
    def parse_bytes(
        data: bytes,
        password: Union[bytes, bytearray, SecureBytes],
        *,
        registry: Optional[WipeRegistry] = None,
    ) -> List[AegisEntry]:
        """Parse encrypted Aegis backup bytes."""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError(
                "The 'cryptography' library is required to decrypt Aegis backups."
            )
        if not AegisDecryptor.is_encrypted_bytes(data):
            raise ValueError("Only encrypted Aegis backup files are supported.")
        vault_data = AegisDecryptor.decrypt_data(data, password)
        return AegisParser._entries_from_vault(vault_data, registry=registry)

    @staticmethod
    def parse(filepath: str, password: str) -> List[AegisEntry]:
        """Parse encrypted Aegis JSON file from disk."""
        if not AegisDecryptor.is_encrypted(filepath):
            raise ValueError("Only encrypted Aegis backup files are supported.")
        if not CRYPTO_AVAILABLE:
            raise RuntimeError(
                "The 'cryptography' library is required to decrypt Aegis backups."
            )
        vault_data = AegisDecryptor.decrypt_file(filepath, password)
        return AegisParser._entries_from_vault(vault_data)


class KeePassKdbx:
    """Open and parse KeePass .kdbx databases via pykeepass."""

    KDBX_SIG1 = b'\x03\xd9\xa2\x9a'
    KDBX_SIG2 = b'\x67\xfb\x4b\xb5'

    OTP_FIELD_KEYS = (
        'TimeOtp-Secret-Base32',
        'TimeOtp-Period',
        'TimeOtp-Digits',
        'TimeOtp-Algorithm',
    )

    @classmethod
    def is_kdbx_bytes(cls, data: bytes) -> bool:
        """Return True if bytes look like a KeePass KDBX file."""
        return (
            len(data) >= 8
            and data[:4] == cls.KDBX_SIG1
            and data[4:8] == cls.KDBX_SIG2
        )

    @staticmethod
    def _password_text(
        password: Union[str, bytes, bytearray, SecureBytes],
    ) -> str:
        if isinstance(password, SecureBytes):
            return password.decode('utf-8')
        if isinstance(password, str):
            return password
        return bytes(password).decode('utf-8')

    @staticmethod
    def _read_sub_element_text(element: Any, tag: str) -> Optional[str]:
        child = element.find(tag)
        if child is not None and child.text:
            return child.text
        return None

    @staticmethod
    def _read_group_uuid(group_element: Any) -> Optional[uuid.UUID]:
        uuid_elem = group_element.find('UUID')
        if uuid_elem is None or not uuid_elem.text:
            return None
        return uuid.UUID(bytes=base64.b64decode(uuid_elem.text))

    @classmethod
    def _recycle_bin_uuid(cls, kp: PyKeePass) -> Optional[uuid.UUID]:
        elem = kp._xpath('/KeePassFile/Meta/RecycleBinUUID', first=True)
        if elem is None or not elem.text:
            return None
        return uuid.UUID(bytes=base64.b64decode(elem.text))

    @staticmethod
    def _entry_string_fields(element: Any) -> Dict[str, str]:
        strings: Dict[str, str] = {}
        for string_elem in element.findall('String'):
            key_elem = string_elem.find('Key')
            value_elem = string_elem.find('Value')
            if key_elem is None or value_elem is None:
                continue
            key = key_elem.text
            if not key:
                continue
            strings[key] = value_elem.text or ''
        return strings

    @classmethod
    def _ancestor_group_names(cls, entry_element: Any) -> List[str]:
        names: List[str] = []
        for group_element in entry_element.iterancestors('Group'):
            parent = group_element.getparent()
            if parent is not None and parent.tag == 'Root':
                continue
            name = cls._read_sub_element_text(group_element, 'Name')
            if name:
                names.append(name)
        names.reverse()
        return names

    @classmethod
    def _entry_in_recycle_bin(
        cls,
        recycle_bin_uuid: Optional[uuid.UUID],
        entry_element: Any,
    ) -> bool:
        if recycle_bin_uuid is None:
            return False
        for group_element in entry_element.iterancestors('Group'):
            group_uuid = cls._read_group_uuid(group_element)
            if group_uuid == recycle_bin_uuid:
                return True
        return False

    @classmethod
    def _group_path_for_entry(cls, entry_element: Any) -> Optional[str]:
        names = cls._ancestor_group_names(entry_element)
        if not names:
            return None
        return ' / '.join(names)

    @classmethod
    def _otp_strings(cls, fields: Dict[str, str]) -> Dict[str, str]:
        return {
            key: fields[key]
            for key in cls.OTP_FIELD_KEYS
            if fields.get(key)
        }

    @classmethod
    def open_bytes(
        cls,
        data: bytes,
        password: Union[str, bytes, bytearray, SecureBytes],
        keyfile_bytes: Optional[bytes] = None,
    ) -> PyKeePass:
        """Decrypt and load a KDBX database from bytes."""
        if not PYKEEPASS_AVAILABLE:
            raise RuntimeError(
                "The 'pykeepass' library is required to read KeePass databases. "
                "Install with: pip install pykeepass"
            )
        if not cls.is_kdbx_bytes(data):
            raise ValueError("Only KeePass .kdbx database files are supported.")

        kdbx_stream = io.BytesIO(data)
        kdbx_stream.seek(0)
        keyfile = None
        if keyfile_bytes:
            keyfile = io.BytesIO(keyfile_bytes)
            keyfile.seek(0)

        try:
            return PyKeePass(
                kdbx_stream,
                password=cls._password_text(password),
                keyfile=keyfile,
            )
        except CredentialsError as exc:
            raise ValueError(
                "Invalid KeePass master password or keyfile."
            ) from exc

    @classmethod
    def entries_from_db(cls, kp: PyKeePass) -> Tuple[List[KeePassEntry], int]:
        """Build KeePassEntry list from an open pykeepass database."""
        entries: List[KeePassEntry] = []
        recycle_bin_count = 0
        recycle_bin_uuid = cls._recycle_bin_uuid(kp)

        for py_entry in kp.entries:
            element = py_entry._element
            fields = cls._entry_string_fields(element)
            title = fields.get('Title', '')
            if not title:
                continue

            in_recycle_bin = cls._entry_in_recycle_bin(recycle_bin_uuid, element)
            if in_recycle_bin:
                recycle_bin_count += 1

            entries.append(KeePassEntry(
                uuid=str(py_entry.uuid),
                title=title,
                username=fields.get('UserName') or None,
                url=fields.get('URL') or None,
                notes=fields.get('Notes') or None,
                group_path=cls._group_path_for_entry(element),
                in_recycle_bin=in_recycle_bin,
                in_history=False,
                strings=cls._otp_strings(fields),
                py_entry=py_entry,
            ))

        return entries, recycle_bin_count

    @staticmethod
    def matchable_entries(entries: List[KeePassEntry]) -> List[KeePassEntry]:
        """Return live, non-recycle-bin entries eligible for Aegis matching."""
        return [e for e in entries if e.is_matchable]


class EntryMatcher:
    """Fuzzy matching engine for Aegis and KeePass entries."""
    
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ''
        # Convert to lowercase, remove special chars, normalize whitespace
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        if not a or not b:
            return 0.0
        return fuzz.ratio(self.normalize(a), self.normalize(b)) / 100.0

    @staticmethod
    def extract_base_domain(text: str) -> Optional[str]:
        """Extract domain/brand name from URL or host string."""
        if not text or '@' in text:
            return None
        if '://' in text:
            match = re.search(r'://([^/]+)', text)
            if match:
                text = match.group(1)
        text = text.split(':')[0].lower().strip()
        parts = text.split('.')
        if len(parts) > 1:
            subdomains = {'www', 'hub', 'account', 'login', 'signin', 'app', 'mail', 'imap', 'pop3', 'na2', 'client', 'cliente', 'minhaconta'}
            tlds = {'com', 'net', 'org', 'ai', 'io', 'br', 'uk', 'co', 'us', 'ca'}
            filtered_parts = [p for p in parts if p not in subdomains and p not in tlds]
            if filtered_parts:
                return filtered_parts[0]
        return None

    @staticmethod
    def clean_username(username: str, issuer: str) -> str:
        """Remove issuer name prefixes from the username if present."""
        if not username:
            return ''
        username = username.strip()
        if not issuer:
            return username
        issuer_clean = re.sub(r'\s+', ' ', issuer).lower().strip()
        username_lower = username.lower()
        prefixes_to_try = [
            issuer_clean + ':',
            issuer_clean + ' -',
            issuer_clean + ' ',
        ]
        for prefix in prefixes_to_try:
            if username_lower.startswith(prefix):
                cleaned = username[len(prefix):].strip()
                cleaned = re.sub(r'^[:\-\s]+', '', cleaned).strip()
                return cleaned
        return username

    @staticmethod
    def extract_numbers(text: str) -> set:
        """Extract sequence of numbers of length >= 8."""
        if not text:
            return set()
        return set(re.findall(r'\d{8,}', text))

    def share_distinct_word(self, str1: str, str2: str) -> bool:
        """Check if two strings share a distinct word (excluding common/ignored ones)."""
        if not str1 or not str2:
            return False
        words1 = set(self.normalize(str1).split())
        words2 = set(self.normalize(str2).split())
        ignored = {'com', 'net', 'org', 'web', 'services', 'app', 'login', 'account', 'auth', 'server', 'cloud', 'online', 'digital', 'micro', 'g5', 'pi', 'server', 'hosting', 'host', 'corp', 'co', 'uk', 'br', 'us', 'ca', 'portal', 'client', 'cliente', 'minhaconta', 'hub'}
        words1 = {w for w in words1 if w not in ignored and len(w) >= 3}
        words2 = {w for w in words2 if w not in ignored and len(w) >= 3}
        common = words1 & words2
        return len(common) > 0

    def _find_best_for_aegis(
        self,
        aegis_entry: AegisEntry,
        keepass_entries: List[KeePassEntry],
        *,
        use_uuid_match: bool = True,
        exclude_with_aegis_uuid: bool = False,
        excluded_keepass_uuids: Optional[set] = None,
    ) -> Optional[MatchResult]:
        """Find the best KeePass match for a single Aegis entry."""
        best_match = None
        best_confidence = 0.0
        best_reason = ""
        excluded = excluded_keepass_uuids or set()

        aegis_id = aegis_entry.full_identifier
        aegis_issuer = aegis_entry.issuer
        aegis_name = aegis_entry.name
        aegis_name_clean = self.clean_username(aegis_name, aegis_issuer)

        aegis_domain = self.extract_base_domain(aegis_issuer) or self.extract_base_domain(aegis_name)
        aegis_numbers = self.extract_numbers(aegis_issuer) | self.extract_numbers(aegis_name)

        for kp_entry in keepass_entries:
            if kp_entry.uuid in excluded:
                continue

            if exclude_with_aegis_uuid and kp_entry.get_aegis_uuid():
                continue

            kp_title = kp_entry.title or ''

            if use_uuid_match:
                existing_uuid = kp_entry.get_aegis_uuid()
                if existing_uuid and existing_uuid.lower() == aegis_entry.uuid.lower():
                    return MatchResult(
                        aegis_entry=aegis_entry,
                        keepass_entry=kp_entry,
                        confidence=10.0,
                        match_reason=f"UUID match ({aegis_entry.uuid})",
                    )

            scores = []
            reasons = []

            sim = self.similarity(aegis_id, kp_title)
            if sim > 0.5:
                scores.append(sim)
                reasons.append(f"full_id vs title ({sim:.2f})")

            sim = self.similarity(aegis_issuer, kp_title)
            if sim > 0.6:
                scores.append(sim)
                reasons.append(f"issuer vs title ({sim:.2f})")

            sim = self.similarity(aegis_name_clean, kp_title)
            if sim > 0.6:
                scores.append(sim)
                reasons.append(f"name vs title ({sim:.2f})")

            norm_issuer = self.normalize(aegis_issuer)
            norm_title = self.normalize(kp_title)
            if norm_issuer and norm_issuer in norm_title:
                scores.append(0.8)
                reasons.append("issuer in title")

            norm_name = self.normalize(aegis_name_clean)
            if norm_name and norm_name in norm_title:
                scores.append(0.7)
                reasons.append("name in title")

            kp_domain_title = self.extract_base_domain(kp_title)
            kp_domain_url = self.extract_base_domain(kp_entry.url)
            if aegis_domain:
                if aegis_domain == kp_domain_title or aegis_domain == kp_domain_url:
                    scores.append(0.9)
                    reasons.append(f"domain match ({aegis_domain})")

            if self.share_distinct_word(aegis_issuer, kp_title):
                scores.append(0.8)
                reasons.append("shared distinct word in title")
            elif self.share_distinct_word(aegis_issuer, kp_entry.url):
                scores.append(0.7)
                reasons.append("shared distinct word in url")

            kp_numbers = self.extract_numbers(kp_title) | self.extract_numbers(kp_entry.username) | self.extract_numbers(kp_entry.notes)
            common_nums = aegis_numbers & kp_numbers
            if common_nums:
                scores.append(0.95)
                reasons.append(f"numeric match ({list(common_nums)[0]})")

            has_service_match = any(r.startswith(("issuer", "domain", "numeric", "shared")) for r in reasons)
            if not has_service_match:
                scores = []
                reasons = []

            kp_username = kp_entry.username or ''
            kp_username_clean = self.clean_username(kp_username, aegis_issuer)

            if scores and kp_username_clean and aegis_name_clean:
                norm_aegis_name = self.normalize(aegis_name_clean)
                norm_kp_username = self.normalize(kp_username_clean)

                if norm_aegis_name == norm_kp_username:
                    scores.append(0.3)
                    reasons.append("username exact match")
                elif norm_aegis_name in norm_kp_username:
                    scores.append(0.2)
                    reasons.append("name in username")
                elif norm_kp_username in norm_aegis_name:
                    scores.append(0.2)
                    reasons.append("username in name")

            if scores:
                confidence = max(scores)

                if kp_username_clean and aegis_name_clean:
                    norm_aegis_name = self.normalize(aegis_name_clean)
                    norm_kp_username = self.normalize(kp_username_clean)
                    if norm_aegis_name == norm_kp_username:
                        confidence += 0.2
                        reasons.append("username bonus")
                    elif norm_aegis_name in norm_kp_username or norm_kp_username in norm_aegis_name:
                        confidence += 0.1
                        reasons.append("username partial bonus")

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = kp_entry
                    best_reason = "; ".join(reasons)

        if not best_match:
            return None

        return MatchResult(
            aegis_entry=aegis_entry,
            keepass_entry=best_match,
            confidence=best_confidence,
            match_reason=best_reason,
        )

    def suggest_match(
        self,
        aegis_entry: AegisEntry,
        keepass_entries: List[KeePassEntry],
        excluded_keepass_uuids: Optional[set] = None,
    ) -> Optional[MatchResult]:
        """Fuzzy-match one Aegis entry, ignoring existing AegisUUID markers in KeePass notes."""
        return self._find_best_for_aegis(
            aegis_entry,
            keepass_entries,
            use_uuid_match=False,
            exclude_with_aegis_uuid=False,
            excluded_keepass_uuids=excluded_keepass_uuids,
        )

    def find_matches(self, aegis_entries: List[AegisEntry], 
                     keepass_entries: List[KeePassEntry]) -> Tuple[List[MatchResult], List[AegisEntry]]:
        """
        Match Aegis entries to KeePass entries.
        Expects current entries only (KeePassKdbx.matchable_entries).
        Returns: (matches, unmatched_aegis_entries)
        """
        matches = []
        unmatched = []
        
        for aegis_entry in aegis_entries:
            result = self._find_best_for_aegis(aegis_entry, keepass_entries)
            if result:
                matches.append(result)
            else:
                unmatched.append(aegis_entry)
        
        # Resolve conflicts: one KeePass entry matched by multiple Aegis entries
        matches = self._resolve_conflicts(matches)
        
        # Update unmatched list after conflict resolution
        matched_uuids = {m.aegis_entry.uuid for m in matches}
        unmatched = [e for e in aegis_entries if e.uuid not in matched_uuids]
        
        return matches, unmatched
    
    def _resolve_conflicts(self, matches: List[MatchResult]) -> List[MatchResult]:
        """
        Resolve cases where multiple Aegis entries matched to the same KeePass entry.
        Prefers matches where Aegis name matches KeePass username.
        """
        from collections import defaultdict
        
        # Group matches by KeePass UUID
        kp_to_matches: Dict[str, List[MatchResult]] = defaultdict(list)
        for match in matches:
            kp_to_matches[match.keepass_entry.uuid].append(match)
        
        resolved = []
        for kp_uuid, match_list in kp_to_matches.items():
            if len(match_list) == 1:
                resolved.append(match_list[0])
                continue
            
            # Multiple Aegis entries matched to same KeePass entry
            # Score each match: prefer username matches
            scored = []
            for match in match_list:
                score = match.confidence
                aegis_name = match.aegis_entry.name or ''
                kp_username = match.keepass_entry.username or ''
                
                # Strong boost if username matches exactly
                if aegis_name and kp_username:
                    norm_name = self.normalize(aegis_name)
                    norm_user = self.normalize(kp_username)
                    if norm_name == norm_user:
                        score += 1.0  # Strong boost for exact username match
                    elif norm_name in norm_user or norm_user in norm_name:
                        score += 0.5
                
                scored.append((score, match))
            
            # Sort by score descending, pick the best
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, best_match = scored[0]
            
            # Only accept if the best match has a significant advantage
            # or if the username matches
            resolved.append(best_match)
            
            # Log rejected matches
            for score, match in scored[1:]:
                print(f"  Rejected match: {match.aegis_entry.display_name} -> {match.keepass_entry.title}")
                print(f"    (Better match: {best_match.aegis_entry.display_name}, scores: {score:.2f} vs {best_score:.2f})")
        
        return resolved


class KeePassUpdater:
    """Updates a KeePass database with OTP data from Aegis entries."""

    AEGIS_UUID_MARKER_PATTERN = re.compile(
        r'AegisUUID:\s*[a-f0-9-]+\s*',
        re.IGNORECASE,
    )

    OTP_FIELDS = {
        'TimeOtp-Secret-Base32': 'secret',
        'TimeOtp-Period': 'period',
        'TimeOtp-Digits': 'digits',
        'TimeOtp-Algorithm': 'algo',
    }

    def __init__(self, kp: PyKeePass):
        self.kp = kp

    @classmethod
    def _strip_all_aegis_markers(cls, notes: str) -> str:
        """Remove every AegisUUID marker line from notes text."""
        cleaned = cls.AEGIS_UUID_MARKER_PATTERN.sub('', notes or '')
        return re.sub(r'\n{3,}', '\n\n', cleaned).strip()

    def update_entry(self, match: MatchResult, dry_run: bool = True) -> Dict:
        """Update a KeePass entry with OTP data from Aegis."""
        kp_entry = match.keepass_entry
        aegis_entry = match.aegis_entry
        py_entry = kp_entry.py_entry

        changes = {
            'title': kp_entry.title,
            'aegis_uuid': aegis_entry.uuid,
            'fields_added': [],
            'fields_updated': [],
            'notes_updated': False,
        }

        if dry_run or py_entry is None:
            return changes

        for kp_key, aegis_attr in self.OTP_FIELDS.items():
            if aegis_attr == 'secret':
                value = aegis_entry.secret_text()
            else:
                value = str(getattr(aegis_entry, aegis_attr))

            existing = py_entry.get_custom_property(kp_key)
            protect = 'Secret' in kp_key
            if existing is not None and existing != '':
                if str(value).upper() != (existing or '').upper():
                    py_entry.set_custom_property(kp_key, str(value), protect=protect)
                    changes['fields_updated'].append(kp_key)
                    kp_entry.strings[kp_key] = str(value)
            else:
                py_entry.set_custom_property(kp_key, str(value), protect=protect)
                changes['fields_added'].append(kp_key)
                kp_entry.strings[kp_key] = str(value)

        marker = f"AegisUUID: {aegis_entry.uuid}"
        current_notes = py_entry.notes or ''
        cleaned_notes = self._strip_all_aegis_markers(current_notes)
        if cleaned_notes:
            new_notes = f"{cleaned_notes}\n\n{marker}"
        else:
            new_notes = marker
        if new_notes != current_notes:
            py_entry.notes = new_notes
            kp_entry.notes = new_notes
            changes['notes_updated'] = True

        return changes

    def remove_aegis_link(self, kp_entry: KeePassEntry, aegis_uuid: str) -> Dict:
        """Remove AegisUUID marker and TimeOtp-* fields from a KeePass entry."""
        py_entry = kp_entry.py_entry
        changes = {
            'title': kp_entry.title,
            'aegis_uuid': aegis_uuid,
            'marker_removed': False,
            'fields_removed': [],
        }

        if py_entry is None:
            return changes

        props = py_entry.custom_properties
        for kp_key in self.OTP_FIELDS:
            if kp_key in props:
                py_entry.delete_custom_property(kp_key)
                changes['fields_removed'].append(kp_key)
                kp_entry.strings.pop(kp_key, None)

        current_notes = py_entry.notes or ''
        pattern = re.compile(
            rf'AegisUUID:\s*{re.escape(aegis_uuid)}\s*',
            re.IGNORECASE,
        )
        new_notes = pattern.sub('', current_notes)
        new_notes = re.sub(r'\n{3,}', '\n\n', new_notes).strip()
        if new_notes != current_notes:
            py_entry.notes = new_notes if new_notes else ''
            kp_entry.notes = new_notes if new_notes else None
            changes['marker_removed'] = True

        return changes

    def apply_match(self, match: MatchResult) -> Dict:
        """Apply OTP data and AegisUUID marker for a match."""
        return self.update_entry(match, dry_run=False)

    def save_bytes(self) -> bytes:
        """Serialize modified database to encrypted KDBX bytes."""
        buffer = io.BytesIO()
        self.kp.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

    def save(self, filepath: str) -> None:
        """Save the modified database to a file."""
        self.kp.save(filepath)
        try:
            os.chmod(filepath, 0o600)
        except OSError:
            pass

