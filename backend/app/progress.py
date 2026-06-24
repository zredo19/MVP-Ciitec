"""
Canal de progreso en vivo (RF/UX): el worker publica avances por Redis pub/sub
y el endpoint WebSocket los reenvía al navegador.

Canal: `task:{task_id}`. Mensajes JSON: {etapa, doc_actual, doc_nombre, total, pct, estado}.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import redis

from .config import settings


@lru_cache(maxsize=1)
def _redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def canal(task_id: str) -> str:
    return f"task:{task_id}"


def publicar(task_id: str, payload: dict[str, Any]) -> None:
    try:
        _redis().publish(canal(task_id), json.dumps(payload, ensure_ascii=False))
    except Exception:
        # el progreso es informativo; nunca debe tumbar el pipeline
        pass
