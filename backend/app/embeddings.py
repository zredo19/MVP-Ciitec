"""
Embeddings locales (on-premise) con sentence-transformers — RF-005.

El modelo se carga UNA vez por proceso (perezoso) y se reutiliza. En el worker
Celery la primera tarea paga la carga; las siguientes reutilizan el singleton.
Dimensión del modelo por defecto = 384 (coincide con `hechos.embedding vector(384)`).
"""
from __future__ import annotations

from functools import lru_cache

from .config import settings

EMBED_DIM = 384


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def embed(texto: str) -> list[float]:
    """Devuelve el vector de un texto como lista de floats (len = EMBED_DIM)."""
    vec = _model().encode(texto or "", normalize_embeddings=True)
    return vec.tolist()


def embed_batch(textos: list[str]) -> list[list[float]]:
    if not textos:
        return []
    vecs = _model().encode(textos, normalize_embeddings=True)
    return [v.tolist() for v in vecs]
