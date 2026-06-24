"""
Dependencias de autenticación/autorización para FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import rbac
from .tokens import decodificar_token

_bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    id: str
    username: str
    nivel: str
    unidad: str | None
    roles: list[str] = field(default_factory=list)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")
    payload = decodificar_token(cred.credentials)
    if payload is None:
        # token inválido o expirado (inactividad > 15 min)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión inválida o expirada")
    return CurrentUser(
        id=payload["uid"],
        username=payload["sub"],
        nivel=payload.get("nivel", "PUBLICO"),
        unidad=payload.get("unidad"),
        roles=payload.get("roles", []),
    )


def require_roles(*roles: str):
    """Dependencia que exige al usuario al menos uno de los roles dados."""
    requeridos = set(roles)

    def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not rbac.tiene_rol(user.roles, requeridos):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol insuficiente")
        return user

    return _dep


def require_auditor(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not rbac.tiene_rol(user.roles, rbac.ROLES_AUDITORIA):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso restringido a auditoría")
    return user
