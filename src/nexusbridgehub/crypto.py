"""Server URL encryption — not reversible without build seed + runtime material."""

from __future__ import annotations

import base64
import hashlib
import os
import platform
import uuid
from typing import Final

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_SALT_PREFIX: Final = b"nexusbridgehub:v1:"
_PBKDF2_ITERATIONS: Final = 480_000


def _machine_fingerprint() -> bytes:
    """Stable-ish runtime material; not stored as plain text in the binary."""
    parts = [
        platform.node(),
        platform.machine(),
        platform.processor() or "",
        str(uuid.getnode()),
    ]
    raw = "|".join(parts).encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).digest()


def derive_key(build_seed: bytes, *, extra: bytes | None = None) -> bytes:
    material = _SALT_PREFIX + build_seed
    if extra:
        material += b":" + extra
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_machine_fingerprint(),
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(material)


def encrypt_server_url(server_url: str, build_seed: bytes) -> str:
    """Encrypt WSS URL for embedding in a thin client bundle."""
    key = derive_key(build_seed)
    nonce = os.urandom(12)
    aes = AESGCM(key)
    ciphertext = aes.encrypt(nonce, server_url.encode("utf-8"), None)
    blob = nonce + ciphertext
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt_server_url(encrypted: str, build_seed: bytes) -> str:
    """Decrypt server URL at runtime inside the worker process."""
    raw = base64.urlsafe_b64decode(encrypted.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    key = derive_key(build_seed)
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, None).decode("utf-8")


def obfuscate_seed(seed: bytes) -> bytes:
    """Split seed into XOR-masked chunks for embedding (light obfuscation layer)."""
    mask = hashlib.sha256(b"nexusbridgehub:mask").digest()
    return bytes(b ^ mask[i % len(mask)] for i, b in enumerate(seed))


def deobfuscate_seed(obfuscated: bytes) -> bytes:
    return obfuscate_seed(obfuscated)


def generate_build_seed() -> bytes:
    return os.urandom(32)
