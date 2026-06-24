"""
Emisión y verificación de JWT con expiración por inactividad (RNF-001).

La sesión expira a los `SESSION_TIMEOUT_MIN` (15 min) de inactividad: cada
request válido renueva el token (sliding). El middleware de la app emite el
token renovado en la cabecera `X-Session-Token`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from ..config import settings


def crear_token(*, sub: str, uid: str, nivel: str, roles: list[str], unidad: str | None) -> str:
    ahora = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": sub,
        "uid": uid,
        "nivel": nivel,
        "roles": roles,
        "unidad": unidad,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.session_timeout_min),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decodificar_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def renovar_token(payload: dict[str, Any]) -> str:
    """Reemite el token extendiendo la expiración (sliding session)."""
    return crear_token(
        sub=payload["sub"],
        uid=payload["uid"],
        nivel=payload["nivel"],
        roles=payload.get("roles", []),
        unidad=payload.get("unidad"),
    )
