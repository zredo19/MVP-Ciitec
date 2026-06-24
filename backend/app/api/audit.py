"""Router de auditoría (RNF-003): consulta del log inmutable y verificación de la hash chain."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import audit as audit_mod
from ..auth.deps import CurrentUser, require_auditor
from ..db import get_db
from ..models import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def listar(
    limit: int = 200,
    user: CurrentUser = Depends(require_auditor),
    db: Session = Depends(get_db),
):
    filas = db.execute(select(AuditLog).order_by(desc(AuditLog.id)).limit(min(limit, 1000))).scalars().all()
    return {"eventos": [{
        "id": e.id,
        "actor_id": str(e.actor_id) if e.actor_id else None,
        "accion": e.accion,
        "entidad_tipo": e.entidad_tipo,
        "entidad_id": e.entidad_id,
        "detalle": e.detalle,
        "nivel_afectado": e.nivel_afectado,
        "ocurrido_en": e.ocurrido_en.isoformat() if e.ocurrido_en else None,
        "hash_actual": e.hash_actual,
    } for e in filas]}


@router.get("/verificar")
def verificar(user: CurrentUser = Depends(require_auditor), db: Session = Depends(get_db)):
    """Recomputa la cadena de hash y reporta si fue manipulada (tamper-evident)."""
    continuidad = audit_mod.verificar_cadena(db)
    fuerte = audit_mod.verificar_cadena_sql(db)
    return {"continuidad": continuidad, "integridad": fuerte,
            "valido": continuidad.get("valido", False) and fuerte.get("valido", False)}
