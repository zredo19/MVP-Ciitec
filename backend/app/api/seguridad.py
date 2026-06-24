"""
Control de acceso por nivel de clasificación y unidad (RNF-001/RNF-002) con
rastro de auditoría.

`exigir_nivel` bloquea (403) a quien no tiene habilitación suficiente para el
nivel del recurso O cuya unidad no corresponde (salvo roles transversales), y
registra el intento; los accesos permitidos a material clasificado también se
auditan si AUDIT_LOG_READS está activo (RNF-003).
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .. import audit
from ..auth import rbac
from ..auth.deps import CurrentUser
from ..config import settings


def exigir_nivel(
    db: Session,
    user: CurrentUser,
    nivel_recurso: str,
    *,
    entidad_tipo: str,
    entidad_id: str,
    unidad_recurso: str | None = None,
) -> None:
    if not rbac.nivel_ok(user.nivel, nivel_recurso):
        audit.registrar(
            db, accion="CONSULTA_CLASIFICADA", actor_id=user.id,
            entidad_tipo=entidad_tipo, entidad_id=entidad_id,
            detalle={"resultado": "DENEGADO", "motivo": "nivel", "habilitacion": user.nivel, "requerido": nivel_recurso},
            nivel_afectado=nivel_recurso,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Habilitación insuficiente para este nivel de clasificación")

    if not rbac.unidad_ok(user.roles, user.unidad, unidad_recurso):
        audit.registrar(
            db, accion="CONSULTA_CLASIFICADA", actor_id=user.id,
            entidad_tipo=entidad_tipo, entidad_id=entidad_id,
            detalle={"resultado": "DENEGADO", "motivo": "unidad", "unidad_usuario": user.unidad, "unidad_recurso": unidad_recurso},
            nivel_afectado=nivel_recurso,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Recurso fuera de la unidad del usuario")

    if settings.audit_log_reads and nivel_recurso in ("RESERVADO", "SECRETO"):
        audit.registrar(
            db, accion="CONSULTA_CLASIFICADA", actor_id=user.id,
            entidad_tipo=entidad_tipo, entidad_id=entidad_id,
            detalle={"resultado": "PERMITIDO", "habilitacion": user.nivel},
            nivel_afectado=nivel_recurso,
        )
