"""
Cliente de object storage (MinIO) — RF-001.

Los binarios originales se guardan en MinIO. Cifrado en reposo (RNF-002):
si `MINIO_ENCRYPT=true` el contenido se cifra client-side con AES-256-GCM
(envelope, ver crypto.py) ANTES de subir, y se descifra al recuperar. Así el
cifrado es real y demostrable sin depender de un KMS externo.
"""
from __future__ import annotations

import io
from functools import lru_cache

from minio import Minio

from . import crypto
from .config import settings


@lru_cache(maxsize=1)
def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_user,
        secret_key=settings.minio_password,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    cli = _client()
    if not cli.bucket_exists(settings.minio_bucket):
        cli.make_bucket(settings.minio_bucket)


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Sube bytes (cifrados si MINIO_ENCRYPT) y devuelve la key del objeto."""
    payload = crypto.encrypt(data) if settings.minio_encrypt else data
    cli = _client()
    cli.put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(payload),
        length=len(payload),
        content_type=content_type,
    )
    return key


def get_bytes(key: str) -> bytes:
    """Recupera y descifra (si corresponde) los bytes de un objeto."""
    resp = _client().get_object(settings.minio_bucket, key)
    try:
        raw = resp.read()
    finally:
        resp.close()
        resp.release_conn()
    return crypto.decrypt(raw) if settings.minio_encrypt else raw
