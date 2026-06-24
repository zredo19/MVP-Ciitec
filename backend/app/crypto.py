"""
Cifrado en reposo (RNF-002): envelope AES-256-GCM a nivel de aplicación.

- `encrypt`/`decrypt` operan sobre bytes (binarios de MinIO).
- `encrypt_str`/`decrypt_str` sobre texto (devuelven/leen base64).
- `EncryptedText` es un TypeDecorator de SQLAlchemy: las columnas marcadas
  con él se cifran de forma transparente al escribir y se descifran al leer.

Formato del ciphertext: base64( nonce(12B) || ct || tag(16B) ).
La clave maestra sale de `ENCRYPTION_KEY`; si no es exactamente 32 bytes en
base64, se deriva con SHA-256 para garantizar AES-256.
"""
from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from .config import settings

_NONCE_LEN = 12


@lru_cache
def _key() -> bytes:
    raw = settings.encryption_key
    try:
        decoded = base64.b64decode(raw)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass
    # Derivación determinista a 32 bytes (AES-256) si la clave no viene en formato exacto.
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt(data: bytes) -> bytes:
    nonce = os.urandom(_NONCE_LEN)
    ct = AESGCM(_key()).encrypt(nonce, data, None)
    return nonce + ct


def decrypt(blob: bytes) -> bytes:
    nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
    return AESGCM(_key()).decrypt(nonce, ct, None)


def encrypt_str(text: str) -> str:
    return base64.b64encode(encrypt(text.encode("utf-8"))).decode("ascii")


def decrypt_str(token: str) -> str:
    return decrypt(base64.b64decode(token)).decode("utf-8")


class EncryptedText(TypeDecorator):
    """Columna de texto cifrada en reposo (AES-256-GCM)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return decrypt_str(value)
        except Exception:
            # Tolerancia a datos legados/no cifrados (p. ej. seed manual).
            return value
