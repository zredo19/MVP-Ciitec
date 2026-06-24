"""
Router de briefings: generación (RF-004), versionado (RF-007), point-in-time
(RF-009), diffs, aprobación, inconsistencias (RF-005), trazabilidad (RF-006) y
exportación (RF-008).
"""
from __future__ import annotations

import difflib
import io
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from .. import audit, storage
from ..auth import rbac
from ..auth.deps import CurrentUser, get_current_user, require_roles
from ..db import get_db
from ..models import (
    Briefing,
    BriefingVersion,
    Exportacion,
    Fuente,
    Inconsistencia,
    VersionBulletHecho,
)
from ..pipeline import exportacion
from ..schemas.api import CrearBriefingIn, ExportarIn
from ..worker import lanzar_generacion
from .seguridad import exigir_nivel

router = APIRouter(prefix="/briefings", tags=["briefings"])


def _version_activa(db: Session, briefing_id, at: datetime | None = None) -> BriefingVersion | None:
    q = select(BriefingVersion).where(BriefingVersion.briefing_id == briefing_id)
    if at is not None:
        q = q.where(BriefingVersion.creado_en <= at)
    return db.execute(q.order_by(desc(BriefingVersion.creado_en)).limit(1)).scalar_one_or_none()


# ---------------- Generación ----------------
@router.post("")
def crear(body: CrearBriefingIn, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.fuente_ids:
        # Solo se aceptan fuentes a las que el usuario tiene acceso por unidad (RNF-001).
        sel = db.execute(select(Fuente).where(Fuente.id.in_(body.fuente_ids))).scalars().all()
        for f in sel:
            if not rbac.unidad_ok(user.roles, user.unidad, f.unidad):
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Fuente fuera de la unidad del usuario")
        fuente_ids = [str(f.id) for f in sel]
    else:
        q = select(Fuente.id).where(Fuente.estado != "ERROR")
        # Sin lista explícita: solo las fuentes de la propia unidad (salvo rol transversal).
        if not rbac.es_transversal(user.roles):
            q = q.where((Fuente.unidad == user.unidad) | (Fuente.unidad.is_(None)))
        fuente_ids = [str(fid) for fid in db.execute(q).scalars()]
    if not fuente_ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No hay fuentes para procesar")

    briefing = Briefing(
        titulo=body.titulo,
        nivel_clasificacion=body.nivel_clasificacion,
        unidad=user.unidad,  # el briefing queda asociado a la unidad de su autor (RNF-001)
        periodo_desde=body.periodo_desde,
        periodo_hasta=body.periodo_hasta,
        creado_por=uuid.UUID(user.id),
    )
    db.add(briefing)
    db.commit()
    db.refresh(briefing)

    task_id = str(uuid.uuid4())
    lanzar_generacion(
        briefing_id=str(briefing.id), fuente_ids=fuente_ids,
        parametros={"titulo": body.titulo}, task_id=task_id, generado_por=user.id,
    )
    return {"briefing_id": str(briefing.id), "task_id": task_id, "fuentes": len(fuente_ids)}


@router.get("")
def listar(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Briefing).order_by(desc(Briefing.creado_en))
    # Segmentación por unidad (RNF-001): salvo roles transversales, solo la propia unidad.
    if not rbac.es_transversal(user.roles):
        q = q.where((Briefing.unidad == user.unidad) | (Briefing.unidad.is_(None)))
    filas = db.execute(q).scalars().all()
    out = []
    for b in filas:
        v = _version_activa(db, b.id)
        out.append({
            "id": str(b.id), "titulo": b.titulo, "estado": b.estado,
            "nivel_clasificacion": b.nivel_clasificacion,
            "creado_en": b.creado_en.isoformat() if b.creado_en else None,
            "version_activa": v.numero_version if v else None,
        })
    return {"briefings": out}


@router.get("/{briefing_id}")
def detalle(briefing_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Briefing, uuid.UUID(briefing_id))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)
    v = _version_activa(db, b.id)
    return {
        "id": str(b.id), "titulo": b.titulo, "estado": b.estado,
        "nivel_clasificacion": b.nivel_clasificacion,
        "version": v.numero_version if v else None,
        "contenido": v.contenido if v else None,
        "creado_en": b.creado_en.isoformat() if b.creado_en else None,
    }


# ---------------- Versiones (RF-007) y point-in-time (RF-009) ----------------
@router.get("/{briefing_id}/versiones")
def versiones(
    briefing_id: str,
    at: datetime | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = db.get(Briefing, uuid.UUID(briefing_id))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)

    if at is not None:
        # Reconstrucción a una hora pasada (RF-009)
        v = _version_activa(db, b.id, at=at)
        if v is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No existe versión activa en ese instante")
        audit.registrar(db, accion="RECONSTRUCCION", actor_id=user.id, entidad_tipo="briefing",
                        entidad_id=str(b.id), detalle={"at": at.isoformat(), "version": v.numero_version})
        return {"at": at.isoformat(), "version": v.numero_version, "contenido": v.contenido,
                "creado_en": v.creado_en.isoformat()}

    filas = db.execute(
        select(BriefingVersion).where(BriefingVersion.briefing_id == b.id).order_by(BriefingVersion.numero_version)
    ).scalars().all()
    return {"versiones": [{
        "id": str(v.id), "numero_version": v.numero_version,
        "comentario_cambio": v.comentario_cambio,
        "aprobado_por": str(v.aprobado_por) if v.aprobado_por else None,
        "aprobado_en": v.aprobado_en.isoformat() if v.aprobado_en else None,
        "creado_en": v.creado_en.isoformat() if v.creado_en else None,
    } for v in filas]}


@router.get("/{briefing_id}/versiones/{numero}")
def version_n(briefing_id: str, numero: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Briefing, uuid.UUID(briefing_id))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)
    v = db.execute(select(BriefingVersion).where(
        BriefingVersion.briefing_id == b.id, BriefingVersion.numero_version == numero)).scalar_one_or_none()
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada")
    return {"numero_version": v.numero_version, "contenido": v.contenido,
            "creado_en": v.creado_en.isoformat() if v.creado_en else None}


@router.get("/{briefing_id}/diff/{a}/{b}")
def diff(briefing_id: str, a: int, b: int, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    br = db.get(Briefing, uuid.UUID(briefing_id))
    if br is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, br.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(br.id), unidad_recurso=br.unidad)

    def _contenido(n: int):
        v = db.execute(select(BriefingVersion).where(
            BriefingVersion.briefing_id == br.id, BriefingVersion.numero_version == n)).scalar_one_or_none()
        if v is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Versión {n} no existe")
        return json.dumps(v.contenido, ensure_ascii=False, indent=2).splitlines()

    izq, der = _contenido(a), _contenido(b)
    delta = list(difflib.unified_diff(izq, der, fromfile=f"v{a}", tofile=f"v{b}", lineterm=""))
    return {"desde": a, "hasta": b, "diff": delta}


# ---------------- Aprobación (RF-007) ----------------
@router.post("/versiones/{version_id}/aprobar")
def aprobar(
    version_id: str,
    user: CurrentUser = Depends(require_roles(*rbac.ROLES_APROBACION)),
    db: Session = Depends(get_db),
):
    v = db.get(BriefingVersion, uuid.UUID(version_id))
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versión no encontrada")
    b = db.get(Briefing, v.briefing_id)
    # Aprobar exige acceso por nivel y unidad al briefing (RNF-001).
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)
    v.aprobado_por = uuid.UUID(user.id)
    v.aprobado_en = datetime.now(timezone.utc)
    b.estado = "APROBADO"
    db.commit()
    audit.registrar(db, accion="APROBACION", actor_id=user.id, entidad_tipo="version",
                    entidad_id=str(v.id), detalle={"version": v.numero_version})
    return {"ok": True, "version": v.numero_version, "estado": b.estado}


# ---------------- Inconsistencias (RF-005) ----------------
@router.get("/{briefing_id}/inconsistencias")
def inconsistencias(briefing_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Briefing, uuid.UUID(briefing_id))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)
    filas = db.execute(select(Inconsistencia).where(Inconsistencia.briefing_id == uuid.UUID(briefing_id))).scalars().all()
    return {"inconsistencias": [{
        "id": str(i.id), "tipo": i.tipo, "severidad": i.severidad,
        "descripcion": i.descripcion, "hechos_involucrados": i.hechos_involucrados,
        "resuelto": i.resuelto,
    } for i in filas]}


# ---------------- Trazabilidad (RF-006) ----------------
@router.get("/{briefing_id}/trazabilidad")
def trazabilidad(briefing_id: str, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Briefing, uuid.UUID(briefing_id))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)
    v = _version_activa(db, b.id)
    if v is None:
        return {"trazas": []}
    filas = db.execute(select(VersionBulletHecho).where(VersionBulletHecho.version_id == v.id)).scalars().all()
    return {"version": v.numero_version, "trazas": [
        {"bullet_key": t.bullet_key, "hecho_id": str(t.hecho_id)} for t in filas
    ]}


# ---------------- Exportación (RF-008) ----------------
@router.post("/{briefing_id}/exportar")
def exportar(
    briefing_id: str,
    body: ExportarIn,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    b = db.get(Briefing, uuid.UUID(briefing_id))
    if b is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Briefing no encontrado")
    exigir_nivel(db, user, b.nivel_clasificacion, entidad_tipo="briefing", entidad_id=str(b.id), unidad_recurso=b.unidad)

    if body.version_id:
        v = db.get(BriefingVersion, uuid.UUID(body.version_id))
    else:
        v = _version_activa(db, b.id)
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay versión para exportar")

    data, content_type, ext = exportacion.render(v.contenido, body.formato, b.titulo, datetime.now(timezone.utc))

    key = f"export/{b.id}/v{v.numero_version}.{ext}"
    storage.put_bytes(key, data, content_type)
    db.add(Exportacion(
        version_id=v.id, formato=body.formato.upper(), objeto_minio=key,
        nivel_clasificacion=b.nivel_clasificacion, generado_por=uuid.UUID(user.id),
    ))
    db.commit()
    audit.registrar(db, accion="EXPORTACION", actor_id=user.id, entidad_tipo="briefing",
                    entidad_id=str(b.id), detalle={"formato": body.formato, "version": v.numero_version},
                    nivel_afectado=b.nivel_clasificacion)

    nombre = f"{b.titulo.replace(' ', '_')}_v{v.numero_version}.{ext}"
    return StreamingResponse(io.BytesIO(data), media_type=content_type,
                             headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
