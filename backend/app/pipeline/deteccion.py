"""
Filtro 4 — DETECCIÓN DE INCONSISTENCIAS (RF-005):

- DUPLICADO    : similitud coseno de embeddings via pgvector (umbral configurable).
- CONTRADICCION: el LLM compara los hechos entre sí.
- DESACTUALIZADO: hechos cuya fecha supera el umbral de antigüedad.
- INCOMPLETO   : hechos con campos clave faltantes.

Devuelve dicts listos para persistir como filas de `inconsistencias`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..llm.provider import LLMProvider, LLMError
from ..models import Hecho


def _duplicados(db: Session, hechos: list[Hecho]) -> list[dict[str, Any]]:
    umbral = settings.dedup_threshold
    ids = [str(h.id) for h in hechos]
    if len(ids) < 2:
        return []
    vistos: set[frozenset[str]] = set()
    out: list[dict[str, Any]] = []
    # vecino más cercano por hecho usando el índice HNSW (operador <=> = distancia coseno)
    sql = text(
        """
        SELECT h2.id AS otro, 1 - (h1.embedding <=> h2.embedding) AS sim
        FROM hechos h1
        JOIN hechos h2 ON h2.id <> h1.id AND h2.id = ANY(:ids)
        WHERE h1.id = :hid AND h1.embedding IS NOT NULL AND h2.embedding IS NOT NULL
        ORDER BY h1.embedding <=> h2.embedding
        LIMIT 1
        """
    )
    for h in hechos:
        if h.embedding is None:
            continue
        fila = db.execute(sql, {"hid": str(h.id), "ids": ids}).first()
        if fila and fila.sim is not None and fila.sim >= umbral:
            par = frozenset({str(h.id), str(fila.otro)})
            if par not in vistos:
                vistos.add(par)
                out.append(
                    {
                        "tipo": "DUPLICADO",
                        "severidad": 2,
                        "descripcion": f"Dos hechos con similitud {fila.sim:.2f} (≥ {umbral}); posible duplicado.",
                        "hechos_involucrados": list(par),
                    }
                )
    return out


def _desactualizados(hechos: list[Hecho]) -> list[dict[str, Any]]:
    limite = datetime.now(timezone.utc) - timedelta(days=settings.desactualizado_dias)
    out = []
    for h in hechos:
        if h.ocurrido_en and h.ocurrido_en < limite:
            out.append(
                {
                    "tipo": "DESACTUALIZADO",
                    "severidad": 1,
                    "descripcion": f"Hecho con fecha {h.ocurrido_en.date()} supera el umbral de {settings.desactualizado_dias} días.",
                    "hechos_involucrados": [str(h.id)],
                }
            )
    return out


def _incompletos(hechos: list[Hecho]) -> list[dict[str, Any]]:
    out = []
    for h in hechos:
        faltan = [
            campo
            for campo, val in (("ubicacion", h.ubicacion), ("responsable", h.responsable), ("ocurrido_en", h.ocurrido_en))
            if not val
        ]
        if faltan:
            out.append(
                {
                    "tipo": "INCOMPLETO",
                    "severidad": 1,
                    "descripcion": f"Hecho con campos faltantes: {', '.join(faltan)}.",
                    "hechos_involucrados": [str(h.id)],
                }
            )
    return out


def _contradicciones(hechos: list[Hecho], provider: LLMProvider) -> list[dict[str, Any]]:
    payload = [
        {
            "id": str(h.id),
            "evento": h.evento,
            "ocurrido_en": h.ocurrido_en.isoformat() if h.ocurrido_en else "",
            "ubicacion": h.ubicacion or "",
            "responsable": h.responsable or "",
            "estado": h.estado or "",
        }
        for h in hechos
    ]
    try:
        crudas = provider.detectar_contradicciones(payload)
    except LLMError:
        return []
    return [
        {
            "tipo": "CONTRADICCION",
            "severidad": int(c.get("severidad", 2)),
            "descripcion": c.get("descripcion", "Contradicción detectada."),
            "hechos_involucrados": c.get("hechos_involucrados", []),
        }
        for c in crudas
    ]


def detectar(db: Session, hechos: list[Hecho], provider: LLMProvider) -> list[dict[str, Any]]:
    """Corre las cuatro detecciones y devuelve la lista de inconsistencias."""
    return (
        _duplicados(db, hechos)
        + _contradicciones(hechos, provider)
        + _desactualizados(hechos)
        + _incompletos(hechos)
    )
