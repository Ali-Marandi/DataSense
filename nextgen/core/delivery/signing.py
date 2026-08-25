from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Protocol


class SigningKeyProvider(Protocol):
    """Boundary for local or enterprise receipt signing.

    Implementations return only a key identifier and signature bytes. The export
    service never needs to know where a key is stored or how it is protected.
    """

    @property
    def key_id(self) -> str: ...

    @property
    def algorithm(self) -> str: ...

    def sign(self, payload: bytes) -> bytes: ...

    def verify(self, payload: bytes, signature: bytes) -> bool: ...


class FileHmacSigningKeyProvider:
    """Alpha-only local signer backed by a 32-byte private file.

    Production Windows builds must replace this provider with an implementation
    backed by DPAPI/Windows Credential Manager or an organization key service.
    """

    algorithm = "HMAC-SHA256"

    def __init__(self, key_path: str | Path) -> None:
        self._key_path = Path(key_path)
        self._key_path.parent.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_create()

    @property
    def key_id(self) -> str:
        return f"local-hmac:{hashlib.sha256(self._key).hexdigest()[:16]}"

    def sign(self, payload: bytes) -> bytes:
        return hmac.new(self._key, payload, hashlib.sha256).digest()

    def verify(self, payload: bytes, signature: bytes) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)

    def _load_or_create(self) -> bytes:
        if self._key_path.exists():
            key = self._key_path.read_bytes()
            if len(key) != 32:
                raise ValueError("Local signing key must be exactly 32 bytes.")
            return key
        key = os.urandom(32)
        temporary_path = self._key_path.with_suffix(self._key_path.suffix + ".tmp")
        temporary_path.write_bytes(key)
        try:
            os.chmod(temporary_path, 0o600)
        except OSError:
            # Windows ACL hardening is a production implementation concern; this
            # best-effort mode is intentionally documented as alpha-only.
            pass
        os.replace(temporary_path, self._key_path)
        return key


class InMemoryHmacSigningKeyProvider:
    """Deterministic signer for unit tests and short-lived local previews."""

    algorithm = "HMAC-SHA256"

    def __init__(self, key: bytes, key_id: str = "test-hmac-key") -> None:
        if len(key) < 16:
            raise ValueError("HMAC test key must be at least 16 bytes.")
        self._key = key
        self._key_id = key_id

    @property
    def key_id(self) -> str:
        return self._key_id

    def sign(self, payload: bytes) -> bytes:
        return hmac.new(self._key, payload, hashlib.sha256).digest()

    def verify(self, payload: bytes, signature: bytes) -> bool:
        return hmac.compare_digest(self.sign(payload), signature)
