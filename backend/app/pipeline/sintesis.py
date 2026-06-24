"""
Filtro 5 — SÍNTESIS (RF-004) + versionado/trazabilidad (RF-006, RF-007).

A partir de los hechos extraídos, el LLM genera el briefing institucional. Se
crea una NUEVA versión append-only y se persiste la trazabilidad bullet -> hecho.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..llm.provider import LLMProvider
from ..models import BriefingVersion, Fuente, Hecho, VersionBulletHecho

# Tope de contexto crudo que se entrega a la síntesis para rellenar cifras
# institucionales (personal, logística, meteo) que la extracción de hechos no captura.
_MAX_CONTEXTO = 8000


def _hechos_payload(hechos: list[Hecho]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(h.id),
            "evento": h.evento,
            "ocurrido_en": h.ocurrido_en.isoformat() if h.ocurrido_en else "",
            "ubicacion": h.ubicacion or "",
            "responsable": h.responsable or "",
            "impacto": h.impacto or "",
            "estado": h.estado or "",
        }
        for h in hechos
    ]


def sintetizar(
    db: Session,
    *,
    briefing_id: str,
    hechos: list[Hecho],
    fuente_ids: list[str],
    provider: LLMProvider,
    generado_por: str | None,
    parametros: dict[str, Any] | None = None,
    comentario: str = "Generación automática",
) -> BriefingVersion:
    # Contexto de las fuentes (acotado) para que la síntesis pueda completar
    # las casillas numéricas institucionales que no son "hechos" (RF-004).
    params = dict(parametros or {})
    if fuente_ids:
        textos = db.execute(
            select(Fuente.texto_extraido).where(Fuente.id.in_(fuente_ids))
        ).scalars().all()
        contexto = "\n---\n".join(t for t in textos if t)
        params["contexto_fuentes"] = contexto[:_MAX_CONTEXTO]

    contenido = provider.sintetizar_briefing(_hechos_payload(hechos), params)

    # numero_version siguiente (append-only, RF-007)
    actual = db.execute(
        select(func.coalesce(func.max(BriefingVersion.numero_version), 0)).where(
            BriefingVersion.briefing_id == briefing_id
        )
    ).scalar_one()
    version = BriefingVersion(
        briefing_id=briefing_id,
        numero_version=actual + 1,
        contenido=contenido,
        comentario_cambio=comentario,
        fuentes_agregadas=fuente_ids,
        generado_por=generado_por,
    )
    db.add(version)
    db.flush()  # obtener version.id

    # Trazabilidad bullet -> hecho (RF-006)
    ids_validos = {str(h.id) for h in hechos}
    traza = contenido.get("trazabilidad", {}) or {}
    vistos: set[tuple[str, str]] = set()
    for bullet_key, hecho_ids in traza.items():
        for hid in hecho_ids or []:
            hid = str(hid)
            if hid in ids_validos and (bullet_key, hid) not in vistos:
                vistos.add((bullet_key, hid))
                db.add(
                    VersionBulletHecho(
                        version_id=version.id,
                        bullet_key=bullet_key[:300],
                        hecho_id=hid,
                    )
                )
    return version
