"""
Retención del audit log a 5 años (RNF-003).

El `audit_log` es inmutable (un trigger bloquea UPDATE/DELETE), por eso la purga
NO borra filas: archiva a almacén frío (MinIO) los eventos más antiguos que la
política de retención y deja constancia. La eliminación física definitiva se hace
fuera de banda (DBA) sobre el archivo exportado. Aquí se exporta + se registra.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from sqlalchemy import text

from . import storage
from .config import settings
from .db import SessionLocal


def purgar() -> dict:
    """Exporta a MinIO los eventos de auditoría fuera de la ventana de retención."""
    storage.ensure_bucket()
    with SessionLocal() as db:
        filas = db.execute(
            text(
                "SELECT * FROM audit_log "
                "WHERE ocurrido_en < now() - (:anios || ' years')::interval ORDER BY id"
            ),
            {"anios": settings.audit_retention_years},
        ).mappings().all()

        if not filas:
            return {"archivados": 0}

        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=list(filas[0].keys()))
        w.writeheader()
        for f in filas:
            w.writerow(dict(f))

        key = f"audit-archive/{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.csv"
        storage.put_bytes(key, buf.getvalue().encode("utf-8"), "text/csv")
        return {"archivados": len(filas), "objeto": key}
