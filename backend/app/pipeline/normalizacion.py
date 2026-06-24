"""
Filtro 2 — NORMALIZACIÓN (RF-002): lleva los campos de cada hecho extraído a un
esquema común (fechas ISO 8601, lugares/responsables limpios, unidades).

Se normalizan los hechos YA extraídos (estructurados); el resultado se guarda en
`hechos.normalizado` (JSONB) sin perder los valores originales.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dateparser

# Abreviaturas/sinónimos institucionales -> forma canónica (ejemplos).
_UNIDAD_CANON = {
    "i de": "I División de Ejército",
    "ii de": "II División de Ejército",
    "jaf": "Jefatura de la Fuerza",
    "jdn": "Jefatura de la Defensa Nacional",
    "ft": "Fuerza de Tarea",
    "bae": "Base Antártica Ejército",
}


def _fecha_iso(valor: str | None) -> str | None:
    if not valor:
        return None
    try:
        dt = dateparser.parse(valor, dayfirst=True, fuzzy=True)
        if dt is None:
            return None
        return dt.isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def _canon_responsable(valor: str | None) -> str | None:
    if not valor:
        return None
    bajo = valor.strip().lower()
    for k, v in _UNIDAD_CANON.items():
        if re.search(rf"\b{re.escape(k)}\b", bajo):
            return v
    return valor.strip()


def normalizar_hecho(hecho: dict[str, Any]) -> dict[str, Any]:
    """Devuelve el bloque `normalizado` para un hecho (RF-002)."""
    fecha_iso = _fecha_iso(hecho.get("ocurrido_en"))
    return {
        "fecha_iso": fecha_iso,
        "ubicacion": (hecho.get("ubicacion") or "").strip() or None,
        "responsable": _canon_responsable(hecho.get("responsable")),
        "impacto": (hecho.get("impacto") or "").strip() or None,
        "estado": hecho.get("estado") or "ABIERTO",
        "normalizado_en": datetime.now(timezone.utc).isoformat(),
    }
