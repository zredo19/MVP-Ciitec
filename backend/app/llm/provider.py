"""
Abstracción del proveedor de LLM.

Toda la lógica del sistema habla con esta interfaz, NUNCA con Groq/OpenAI
directamente. En el MVP se usa Groq (Llama 3.3 70B); en producción se reemplaza
por un modelo local (clasificación de datos) implementando LocalLLMProvider y
seteando LLM_PROVIDER=local, sin tocar el resto del código.

Groq no garantiza JSON-schema estricto, así que cada método:
  1) pide JSON con prompts MUY explícitos en español,
  2) parsea + valida con Pydantic (schemas/llm.py),
  3) reintenta con backoff exponencial; si agota, propaga LLMError.
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from typing import Any

from pydantic import ValidationError

from ..config import settings
from ..schemas.llm import (
    BriefingOut,
    ContradiccionesResponse,
    HechosResponse,
)


class LLMError(RuntimeError):
    """Falla irrecuperable del LLM tras agotar reintentos."""


# ---------------------------------------------------------------------------
#  Prompts (español, explícitos, sin preámbulo) — adaptados a Groq
# ---------------------------------------------------------------------------
_EXTRACT_SYS = """Eres un analista de operaciones del Ejército de Chile. Extrae los hechos
operacionales del documento entregado. Responde SOLO con un JSON válido (sin preámbulo,
sin texto adicional, sin markdown) con esta estructura exacta:
{
  "hechos": [
    {
      "evento": "qué ocurrió",
      "ocurrido_en": "cuándo (ISO 8601 si es posible, si no, vacío)",
      "ubicacion": "dónde (área/lugar)",
      "responsable": "quién (unidad/responsable)",
      "impacto": "impacto en personas/medios/servicio",
      "estado": "ABIERTO|EN_CURSO|CERRADO",
      "texto_origen": "cita textual exacta del documento que respalda el hecho"
    }
  ]
}
Reglas: no inventes datos; si un campo no aparece, déjalo como cadena vacía "".
Incluye SIEMPRE "texto_origen" con la cita textual exacta. Usa terminología institucional.
Si no hay hechos claros, devuelve {"hechos": []}."""

_SYNTH_SYS = """Eres un asesor de operaciones del Ejército de Chile. A partir de los HECHOS ya
extraídos (no de los documentos crudos), redacta un briefing operacional institucional.
Responde SOLO con un JSON válido (sin preámbulo, sin markdown) con esta estructura:
{
  "resumen_ejecutivo": ["5 a 10 bullets ejecutivos"],
  "asuntos_criticos": [{"asunto":"...","impacto":"...","responsable":"..."}],
  "proyeccion_24_72h": "proyección de las próximas 24 a 72 horas",
  "situacion": {"resumen":"panorama operacional general (situación) en 2-4 frases","aspectos":["aspecto relevante de la situación","..."]},
  "personal": {
    "parte_fuerza_institucional": {"OF":"-.-","SOF":"-.-","ECP":"-.-","SLTP":"-.-","ESCMIL":"-.-","ESCSOF":"-.-","ESCSERV":"-.-","personal_civil":"-.-","SLC":"-.-","total":"-.-"},
    "slc": {"clase_2006":"-.-","clase_2007":"-.-","total":"-.-"},
    "macrozonas": [{"zona":"...","fuerza":"-.-","forman":"-.-","faltan":"-.-"}],
    "catastrofe": {"fuerza":"-.-","forman":"-.-","faltan":"-.-"}
  },
  "inteligencia": {
    "incidentes_institucionales": [{"tipo":"...","descripcion":"..."}],
    "incidentes_mootw": [{"tipo":"...","unidad":"...","descripcion":"..."}],
    "sistema_alerta": [{"alerta":"...","area":"...","unidad_asociada":"...","apreciacion":"..."}],
    "analisis_meteo": "...",
    "proyeccion_meteo_48h": "..."
  },
  "operaciones": {
    "ops_catastrofe": [{"cantidad":"-.-","tipo":"...","unidad_origen":"...","zona_empleo":"...","inicio_empleo":"..."}],
    "relevos_norte": [{"n":"...","fecha":"...","jaf":"...","unidades":"..."}],
    "relevos_sur": [{"n":"...","fecha":"...","ft":"...","unidades":"..."}],
    "ops_antartica": [{"bae":"...","dotacion_estival":"-.-","cpccgu":"..."}],
    "ops_extranjero": [{"operacion":"...","efectivos":"-.-","ubicacion":"...","repliegue":"..."}],
    "guardian_soberano": [{"jaf":"...","fuerza":"-.-","planif":"-.-","ejecut":"-.-"}],
    "unidades_terreno_kpi": {"unidades_en_terreno":"-.-","fuerza_en_terreno":"-.-","lugares_activos":"-.-","actividad_principal":"..."},
    "traslados_uac": [{"uac":"...","unidades":"-.-"}],
    "unidades_terreno": [{"actividad":"...","comando_matriz":"...","ur":"...","fechas":"...","ubicacion":"...","fuerza":"-.-"}]
  },
  "logistica": {
    "resumen": {"total":"-.-","nop":"-.-"},
    "operacionalidad": [{"unidad":"...","total":"-.-","nop":"-.-","campana":"-.-","combate":"-.-","administrativos":"-.-","eq_ingenieros":"-.-"}]
  },
  "trazabilidad": {"resumen_ejecutivo[0]": ["id-de-hecho", "..."]}
}
Reglas: el briefing DEBE incluir un resumen por sección (RF-004): "situacion" (panorama
general), "personal", "logistica", incidentes (en "inteligencia") y meteorología (en
"inteligencia.analisis_meteo"); completa "situacion" con lo que aporten los hechos/contexto.
Cada bullet/casilla con dato debe poder rastrearse a los hechos que lo originan;
incluye sus ids en "trazabilidad" usando como clave la ruta del bullet (p.ej. "resumen_ejecutivo[0]").
Donde no haya dato, usa "-.-". No inventes cifras. Mantén entre 5 y 10 bullets en resumen_ejecutivo.
Si en "parametros.contexto_fuentes" aparecen cifras o datos (personal OF/SOF/ECP/total, fuerzas por
macrozona, operacionalidad/NOP, meteorología, incidentes), ÚSALOS para completar las casillas
institucionales correspondientes; si no aparecen en el contexto ni en los hechos, deja "-.-"."""

_CONTRA_SYS = """Eres un analista de operaciones del Ejército de Chile. Te entrego una lista de
HECHOS (cada uno con su id). Identifica CONTRADICCIONES entre ellos (afirmaciones
incompatibles sobre el mismo evento, cifras o estados). Responde SOLO con JSON válido:
{"contradicciones":[{"descripcion":"...","hechos_involucrados":["id1","id2"],"severidad":1}]}
severidad: 1 baja, 2 media, 3 alta. Si no hay contradicciones, devuelve {"contradicciones": []}."""


class LLMProvider(ABC):
    """Contrato que cumple cualquier proveedor (Groq hoy, modelo local mañana)."""

    @abstractmethod
    def extraer_hechos(self, texto: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def sintetizar_briefing(self, hechos: list[dict[str, Any]], parametros: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def detectar_contradicciones(self, hechos: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


def _strip_fences(s: str) -> str:
    """Quita ```json ... ``` si el modelo lo agrega pese a las instrucciones."""
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.endswith("```"):
            s = s[: s.rfind("```")]
    return s.strip()


class _OpenAICompatProvider(LLMProvider):
    """Base para back-ends con API estilo OpenAI (Groq, GitHub Models).

    Las subclases solo configuran `client`, `model` y `max_retries`; toda la
    lógica de prompts/JSON/reintentos vive aquí.
    """

    client: Any
    model: str
    max_retries: int

    def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        """Pide JSON al modelo; reintenta con backoff exponencial."""
        last_err: Exception | None = None
        for intento in range(self.max_retries):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw = _strip_fences(resp.choices[0].message.content or "")
                return json.loads(raw)
            except Exception as e:  # red, JSON inválido, etc.
                last_err = e
                if intento < self.max_retries - 1:
                    time.sleep(2 ** intento)  # 1s, 2s, 4s...
        raise LLMError(f"LLM falló tras {self.max_retries} intentos: {last_err}")

    def extraer_hechos(self, texto: str) -> list[dict[str, Any]]:
        data = self._chat_json(_EXTRACT_SYS, texto)
        try:
            parsed = HechosResponse.model_validate(data)
        except ValidationError as e:
            raise LLMError(f"Extracción con formato inválido: {e}")
        return [h.model_dump() for h in parsed.hechos]

    def sintetizar_briefing(self, hechos: list[dict[str, Any]], parametros: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps({"hechos": hechos, "parametros": parametros}, ensure_ascii=False)
        data = self._chat_json(_SYNTH_SYS, payload)
        try:
            return BriefingOut.model_validate(data).model_dump()
        except ValidationError as e:
            raise LLMError(f"Síntesis con formato inválido: {e}")

    def detectar_contradicciones(self, hechos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(hechos) < 2:
            return []
        payload = json.dumps({"hechos": hechos}, ensure_ascii=False)
        data = self._chat_json(_CONTRA_SYS, payload)
        try:
            return [c.model_dump() for c in ContradiccionesResponse.model_validate(data).contradicciones]
        except ValidationError:
            return []  # la detección de contradicciones es best-effort


class GroqProvider(_OpenAICompatProvider):
    def __init__(self) -> None:
        from groq import Groq  # import perezoso

        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY no configurada")
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
        self.max_retries = settings.groq_max_retries


class GitHubProvider(_OpenAICompatProvider):
    """GitHub Models (endpoint OpenAI-compatible) — gpt-4o."""

    def __init__(self) -> None:
        from openai import OpenAI  # import perezoso

        if not settings.github_token:
            raise LLMError("GITHUB_TOKEN no configurada")
        self.client = OpenAI(
            base_url=settings.github_base_url,
            api_key=settings.github_token,
        )
        self.model = settings.github_model
        self.max_retries = settings.llm_max_retries


class LocalLLMProvider(LLMProvider):
    """Stub para producción: aquí entra el modelo local (clasificación de datos)."""

    def extraer_hechos(self, texto: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Implementar con el modelo local on-premise.")

    def sintetizar_briefing(self, hechos: list[dict[str, Any]], parametros: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Implementar con el modelo local on-premise.")

    def detectar_contradicciones(self, hechos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError("Implementar con el modelo local on-premise.")


def get_llm_provider() -> LLMProvider:
    proveedor = settings.llm_provider.lower()
    if proveedor == "local":
        return LocalLLMProvider()
    if proveedor == "groq":
        return GroqProvider()
    return GitHubProvider()  # "github" (por defecto)
