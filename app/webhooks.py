# entrada de los webhooks de discord: una ruta por app, con su clave y su producto

import json
import logging

from fastapi import APIRouter, HTTPException, Request, Response
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from app import config, productos

log = logging.getLogger(__name__)
router = APIRouter()

RUTAS = {
    "bot-1": (config.CLAVES_PUBLICAS["producto1"], productos.producto1),
    "bot-2": (config.CLAVES_PUBLICAS["producto2"], productos.producto2),
    "bot-3": (config.CLAVES_PUBLICAS["producto3"], productos.producto3),
    "bot-4": (config.CLAVES_PUBLICAS["producto4"], productos.producto4),
}


def firma_valida(request, body, clave_publica):
    # discord firma cada webhook con la clave de la app (ed25519). sin comprobarlo,
    # cualquiera que conozca la url podría mandarnos compras falsas
    firma = request.headers.get("X-Signature-Ed25519")
    momento = request.headers.get("X-Signature-Timestamp")
    if not firma or not momento:
        return False
    try:
        VerifyKey(bytes.fromhex(clave_publica)).verify(momento.encode() + body, bytes.fromhex(firma))
        return True
    except (BadSignatureError, ValueError):
        return False


@router.post("/webhook/{nombre}")
async def recibir(nombre: str, request: Request):
    if nombre not in RUTAS:
        raise HTTPException(status_code=404)
    clave, manejar = RUTAS[nombre]

    body = await request.body()
    if not firma_valida(request, body, clave):
        log.warning("/webhook/%s: firma inválida", nombre)
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Los codigos con un 5xx discord vuelve a mandar el evento y con un 4xx no.
    try:
        payload = json.loads(body)
        if payload.get("type") == 0:  # ping que manda discord al guardar la url
            return Response(status_code=204)
        evento = payload.get("event") or {}
        log.debug("/webhook/%s: %s", nombre, evento)
        return await manejar(evento.get("type"), evento.get("data") or {})
    except ValueError as e:
        log.warning("/webhook/%s: datos incorrectos (%s)", nombre, e)
        raise HTTPException(status_code=400, detail="Bad request")
    except Exception:
        log.exception("/webhook/%s: error procesando el evento", nombre)
        raise HTTPException(status_code=500, detail="Internal error")
