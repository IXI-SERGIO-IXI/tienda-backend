# registro de cada venta en la tabla ventas y aviso en el canal privado de ventas

import logging
import re

import aiohttp

from app import config, db
from app.tareas import en_segundo_plano

log = logging.getLogger(__name__)

AVISOS = {
    "ENTITLEMENT_CREATE": ("## 💰 NEW SALE — DISCORD", 0x45E0CF),
    "ENTITLEMENT_UPDATE": ("## 🔁 RENEWAL — DISCORD", 0x6000E9),
    "ENTITLEMENT_DELETE": ("## ↩️ REFUND / ADJUSTMENT — DISCORD", 0xED4245),
}

_PLANES = {
    "producto2": config.PLANES_PRODUCTO2,
    "producto3": config.PLANES_PRODUCTO3,
}


async def ya_apuntada(id_evento, tipo):
    if not id_evento:
        return False
    fila = await db.buscar("""
        SELECT id FROM ventas
        WHERE txn_id = %s AND event_type = %s AND created_at > UTC_TIMESTAMP() - INTERVAL 1 DAY
        LIMIT 1
    """, (str(id_evento), tipo))
    return fila is not None


async def registrar(producto, tier, guild_id, user_id, id_evento, tipo):
    # discord puede mandar el mismo evento más de una vez. si ya está apuntado en las
    # últimas 24 h no se repite (la renovación del mes siguiente sí entra)
    try:
        if await ya_apuntada(id_evento, tipo):
            return
        await db.ejecutar("""
            INSERT INTO ventas
                (source, product, tier, guild_id, buyer_user_id, txn_id, event_type)
            VALUES ('discord', %s, %s, %s, %s, %s, %s)
        """, (producto, tier, guild_id, user_id, str(id_evento) if id_evento else None, tipo))
    except Exception:
        log.exception("no pude apuntar la venta; la activación sigue igual")


def avisar(tipo, producto, tier, guild_id, user_id):
    # en segundo plano: el webhook tiene que contestar a discord cuanto antes o lo repite
    en_segundo_plano(_publicar(tipo, producto, tier, guild_id, user_id))


def _importe(producto, tier):
    # el tier llega como sku (productos 1 y 4) o como "x2 servers" en los productos con planes
    precio = config.PRECIOS.get(str(tier))
    if precio is None:
        m = re.match(r"x(\d+)\b", str(tier).strip())
        mapa = _PLANES.get(producto)
        if m and mapa:
            sku = next((k for k, v in mapa.items() if v == int(m.group(1))), None)
            precio = config.PRECIOS.get(sku)
    if precio is None:
        return None
    return f"**Total:** `${precio:.2f}`  ·  **Earnings:** `${precio * config.DISCORD_NETO:.2f}`"


async def _publicar(tipo, producto, tier, guild_id, user_id):
    titulo, color = AVISOS.get(tipo, AVISOS["ENTITLEMENT_DELETE"])
    lineas = [f"**Product:** {config.NOMBRES.get(producto, producto)}"]
    if tier:
        lineas.append(f"**Tier/SKU:** `{tier}`")
    importe = _importe(producto, tier)
    if importe:
        lineas.append(importe)
    if guild_id:
        lineas.append(f"**Guild:** `{guild_id}`")
    if user_id:
        lineas.append(f"**Buyer:** <@{user_id}> · `{user_id}`")

    # tarjeta de discord: caja (17) con título, separadores (14) y líneas de texto (10)
    mensaje = {
        "flags": 32768,
        "components": [{
            "type": 17,
            "accent_color": color,
            "components": [
                {"type": 10, "content": titulo},
                {"type": 14},
                *({"type": 10, "content": linea} for linea in lineas),
                {"type": 14},
                {"type": 10, "content": f"-# Discord · {tipo}"},
            ],
        }],
    }
    try:
        async with aiohttp.ClientSession() as sesion:
            # sin with_components=true discord rechaza los mensajes con components v2
            async with sesion.post(f"{config.WEBHOOK_VENTAS}?with_components=true", json=mensaje,
                                   headers={"User-Agent": config.USER_AGENT},
                                   timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status >= 300:
                    log.warning("el canal de ventas respondió %s: %s", r.status,
                                (await r.text())[:300])
    except Exception:
        log.exception("no pude avisar en el canal de ventas")
