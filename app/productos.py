# qué hace cada producto cuando llega un evento de discord.
# ENTITLEMENT_CREATE = compra, ENTITLEMENT_UPDATE = renovación o cambio de plan,
# ENTITLEMENT_DELETE = reembolso

import asyncio
import logging

from app import claves, config, mensajes, suscripciones, ventas

log = logging.getLogger(__name__)

OK = {"status": "ok"}
IGNORADO = {"status": "ignored"}


def _guild_y_usuario(data):
    guild_id, user_id = data.get("guild_id"), data.get("user_id")
    if not guild_id or not user_id:
        raise ValueError("faltan guild_id o user_id")
    return guild_id, user_id


def _guild(data):
    guild_id = data.get("guild_id")
    if not guild_id:
        raise ValueError("reembolso sin guild_id")
    return guild_id


async def _anotar(producto, tipo, data, etiqueta=None):
    sku = data.get("sku_id")
    await ventas.registrar(producto, str(sku), data.get("guild_id"), data.get("user_id"),
                           data.get("id"), tipo)
    ventas.avisar(tipo, producto, etiqueta or sku, data.get("guild_id"), data.get("user_id"))


async def producto1(tipo, data):
    """suscripción mensual para un servidor de discord"""
    if tipo == "ENTITLEMENT_CREATE":
        guild_id, user_id = _guild_y_usuario(data)
        await suscripciones.alta_producto1(guild_id, user_id)
        await _anotar("producto1", tipo, data)
        mensajes.bienvenida(user_id, "producto1")
        return OK
    if tipo == "ENTITLEMENT_DELETE":
        await suscripciones.cortar_servidor("servidores_producto1", _guild(data))
        await _anotar("producto1", tipo, data)
        return OK
    return IGNORADO


async def producto2(tipo, data):
    """como el 1, pero el plan dice en cuántos servidores se puede usar"""
    if tipo == "ENTITLEMENT_CREATE":
        guild_id, user_id = _guild_y_usuario(data)
        max_servers = config.PLANES_PRODUCTO2.get(str(data.get("sku_id")), 1)
        await suscripciones.alta_producto2(guild_id, user_id, max_servers)
        await _anotar("producto2", tipo, data, f"x{max_servers} servers")
        mensajes.bienvenida(user_id, "producto2")
        return OK
    if tipo == "ENTITLEMENT_DELETE":
        await suscripciones.cortar_servidor("servidores_producto2", _guild(data))
        await _anotar("producto2", tipo, data)
        return OK
    return IGNORADO


async def producto3(tipo, data):
    """suscripción con planes que se renueva con la fecha que manda discord"""
    if tipo in ("ENTITLEMENT_CREATE", "ENTITLEMENT_UPDATE"):
        # la renovación es el mismo upsert con la fecha nueva. sin esto expires_at se
        # quedaría en la fecha de la primera compra
        guild_id, user_id = _guild_y_usuario(data)
        sku = str(data.get("sku_id"))
        max_bots = config.PLANES_PRODUCTO3.get(sku)
        if max_bots is None:
            log.warning("producto3: sku %s desconocida, no toco max_bots", sku)
        await suscripciones.alta_producto3(guild_id, str(user_id), max_bots,
                                           suscripciones.fin_de_acceso(data))
        await _anotar("producto3", tipo, data, f"x{config.PLANES_PRODUCTO3.get(sku, '?')} bots")
        if tipo == "ENTITLEMENT_CREATE":
            mensajes.bienvenida(user_id, "producto3")
        return OK
    if tipo == "ENTITLEMENT_DELETE":
        await suscripciones.cortar_producto3(_guild(data), data.get("user_id"))
        await _anotar("producto3", tipo, data)
        return OK
    return IGNORADO


async def producto4(tipo, data):
    """licencia de una aplicación de escritorio: se crea una cuenta y se manda por DM"""
    if tipo == "ENTITLEMENT_CREATE":
        guild_id, user_id = _guild_y_usuario(data)
        # si discord repite el evento la cuenta ya existe. sin esto se crearía otra con
        # credenciales distintas y el cliente recibiría dos DM
        if await ventas.ya_apuntada(data.get("id"), tipo):
            log.info("producto4: el entitlement %s ya tiene cuenta, no hago otra", data.get("id"))
            return OK
        usuario, clave = claves.nuevo_usuario(), claves.nueva_clave()
        # el hash tarda unas décimas a propósito (es lo que lo hace seguro), por eso va a otro
        # hilo y no frena al resto de peticiones
        hash_clave = await asyncio.to_thread(claves.hashear, clave)
        await suscripciones.alta_cuenta_producto4(guild_id, usuario, hash_clave, data.get("id"))
        await _anotar("producto4", tipo, data)
        await mensajes.credenciales_producto4(user_id, usuario, clave)
        return OK
    if tipo == "ENTITLEMENT_DELETE":
        await suscripciones.cortar_servidor("cuentas_producto4", _guild(data))
        await _anotar("producto4", tipo, data)
        return OK
    return IGNORADO
