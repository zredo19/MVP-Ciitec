"""
Canal WebSocket de progreso (RF-004/UX): WS /ws/task/{task_id}.

Requiere sesión válida (RNF-001): el navegador no puede fijar cabeceras en la
API WebSocket, así que el JWT viaja como query param `?token=`; se valida antes
de aceptar la conexión y se cierra con 4401 si es inválido o expiró.

Se suscribe al canal Redis pub/sub del task y reenvía cada mensaje de progreso
al navegador hasta que el pipeline reporta 'completado'.
"""
from __future__ import annotations

import json

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth.tokens import decodificar_token
from ..config import settings
from ..progress import canal

router = APIRouter()


@router.websocket("/ws/task/{task_id}")
async def ws_task(websocket: WebSocket, task_id: str, token: str | None = None):
    # Autenticación (RNF-001): sin token válido se rechaza antes de aceptar.
    if not token or decodificar_token(token) is None:
        await websocket.close(code=4401)  # 4401 = no autenticado/expirado
        return
    await websocket.accept()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    ps = r.pubsub()
    await ps.subscribe(canal(task_id))
    try:
        while True:
            msg = await ps.get_message(ignore_subscribe_messages=True, timeout=60)
            if msg and msg.get("type") == "message":
                await websocket.send_text(msg["data"])
                try:
                    if json.loads(msg["data"]).get("etapa") == "completado":
                        break
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await ps.unsubscribe(canal(task_id))
            await ps.aclose()
            await r.aclose()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
