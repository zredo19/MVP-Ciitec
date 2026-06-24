from app.pipeline import extraccion, ingesta, normalizacion


def test_normalizar_fecha_iso():
    n = normalizacion.normalizar_hecho({"ocurrido_en": "05-05-2026", "ubicacion": " Arica "})
    assert n["fecha_iso"].startswith("2026-05-05")
    assert n["ubicacion"] == "Arica"


def test_normalizar_responsable_canon():
    n = normalizacion.normalizar_hecho({"responsable": "JAF Arica"})
    assert "Jefatura" in n["responsable"]


def test_ingesta_texto_plano():
    txt = ingesta.extraer_texto("línea 1\nlínea 2".encode("utf-8"), "BITACORA", "x.txt")
    assert "línea 1" in txt


class _ProviderStub:
    """Mock del LLMProvider en su límite de abstracción (sin red)."""
    def extraer_hechos(self, texto):
        return [{
            "evento": "Apoyo a incendio forestal",
            "ocurrido_en": "05-05-2026",
            "ubicacion": "Temuco",
            "responsable": "JDN Araucanía",
            "impacto": "30 efectivos",
            "estado": "EN_CURSO",
            "texto_origen": "Apoyo a incendio forestal en Temuco",
        }]
    def sintetizar_briefing(self, hechos, parametros):
        return {"resumen_ejecutivo": ["bullet"], "trazabilidad": {}}
    def detectar_contradicciones(self, hechos):
        return []


def test_extraccion_estructura(monkeypatch):
    # Evita cargar sentence-transformers en el test.
    monkeypatch.setattr(extraccion.embeddings, "embed", lambda t: [0.0] * 384)
    out = extraccion.extraer("texto", _ProviderStub())
    assert len(out) == 1
    h = out[0]
    assert h["evento"] == "Apoyo a incendio forestal"
    assert h["estado"] == "EN_CURSO"
    assert h["ocurrido_en"].year == 2026
    assert len(h["embedding"]) == 384
    assert h["normalizado"]["responsable"].startswith("Jefatura")
