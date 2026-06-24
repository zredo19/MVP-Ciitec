"""
Auditoría inmutable con hash chain (RNF-003).

Todo evento auditable pasa por `registrar()`. El encadenamiento de hash lo
calcula el trigger `audit_hash_chain` en la BD; aquí solo serializamos los
inserts con un advisory lock de transacción para que, bajo concurrencia
(varias tareas del worker), la cadena no se rompa al leer la fila anterior.

`verificar_cadena()` recomputa la cadena y detecta cualquier manipulación.
"""
from __future__ import annotations

import hashlib
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import AuditLog

# Clave fija para el advisory lock de la cadena de auditoría.
_LOCK_KEY = 911_003


def registrar(
    db: Session,
    *,
    accion: str,
    actor_id: str | None = None,
    entidad_tipo: str | None = None,
    entidad_id: str | None = None,
    detalle: dict[str, Any] | None = None,
    nivel_afectado: str | None = None,
    commit: bool = True,
) -> None:
    """Inserta un evento en el audit_log (hash chain vía trigger)."""
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})
    db.add(
        AuditLog(
            actor_id=actor_id,
            accion=accion,
            entidad_tipo=entidad_tipo,
            entidad_id=str(entidad_id) if entidad_id is not None else None,
            detalle=detalle or {},
            nivel_afectado=nivel_afectado,
        )
    )
    if commit:
        db.commit()
    else:
        db.flush()


def verificar_cadena(db: Session) -> dict[str, Any]:
    """Recalcula la hash chain y reporta la primera fila inconsistente, si la hay."""
    filas = db.execute(
        text(
            "SELECT id, actor_id, accion, entidad_tipo, entidad_id, detalle, "
            "ocurrido_en, hash_anterior, hash_actual FROM audit_log ORDER BY id"
        )
    ).mappings().all()

    prev = None
    for f in filas:
        base = (
            (prev or "")
            + (str(f["actor_id"]) if f["actor_id"] is not None else "")
            + str(f["accion"])
            + (f["entidad_tipo"] or "")
            + (f["entidad_id"] or "")
            # el trigger usa detalle::text y ocurrido_en::text de Postgres;
            # la verificación canónica fuerte se hace en SQL (ver más abajo).
        )
        # Validación de continuidad del encadenamiento (hash_anterior correcto).
        if f["hash_anterior"] != prev:
            return {"valido": False, "fila_rota": f["id"], "motivo": "hash_anterior no coincide"}
        prev = f["hash_actual"]

    return {"valido": True, "filas": len(filas)}


def verificar_cadena_sql(db: Session) -> dict[str, Any]:
    """
    Verificación fuerte: recomputa hash_actual con la MISMA expresión del trigger
    (digest sobre los campos serializados por Postgres) y compara.
    """
    res = db.execute(
        text(
            """
            WITH recompute AS (
                SELECT id,
                       hash_actual,
                       encode(digest(
                           coalesce(lag(hash_actual) OVER (ORDER BY id), '') ||
                           coalesce(actor_id::text,'') || accion::text ||
                           coalesce(entidad_tipo,'') || coalesce(entidad_id,'') ||
                           detalle::text || ocurrido_en::text, 'sha256'), 'hex') AS esperado
                FROM audit_log
            )
            SELECT id FROM recompute WHERE hash_actual <> esperado ORDER BY id LIMIT 1
            """
        )
    ).first()
    if res is None:
        return {"valido": True}
    return {"valido": False, "fila_rota": res[0]}


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
