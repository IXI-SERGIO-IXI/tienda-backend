# altas, renovaciones y cortes de las suscripciones en la base de datos.
# ojo: los nombres de tabla que van con f-string salen siempre del código, nunca de la petición

import logging
from datetime import datetime, timezone

from dateutil.relativedelta import relativedelta

from app import db

log = logging.getLogger(__name__)


def _ahora():
    # en la base de datos las fechas van en utc y sin zona
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def caducidad_por_defecto():
    # un mes y un día de margen para que no caduque justo antes de que llegue la renovación
    return _ahora() + relativedelta(months=1, days=1)


def fin_de_acceso(data):
    """hasta cuándo ha pagado, según el ends_at del entitlement. si no viene, un mes"""
    fin = data.get("ends_at")
    if not fin:
        return caducidad_por_defecto()
    try:
        fecha = datetime.fromisoformat(str(fin).replace("Z", "+00:00"))
    except ValueError:
        log.warning("ends_at ilegible (%r), pongo un mes", fin)
        return caducidad_por_defecto()
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
    return fecha.replace(microsecond=0)


async def alta_producto1(guild_id, user_id):
    await db.ejecutar("""
        INSERT INTO servidores_producto1 (server_id, subscription_type, expires_at, nombre)
        VALUES (%s, 'basic', %s, %s)
        ON DUPLICATE KEY UPDATE
            expires_at = VALUES(expires_at),
            subscription_type = 'basic',
            status = 'active'
    """, (guild_id, caducidad_por_defecto(), str(user_id)))


async def alta_producto2(guild_id, user_id, max_servers):
    await db.ejecutar("""
        INSERT INTO servidores_producto2
            (server_id, subscription_type, expires_at, nombre, max_servers)
        VALUES (%s, 'basic', %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            expires_at = VALUES(expires_at),
            subscription_type = 'basic',
            status = 'active',
            max_servers = VALUES(max_servers)
    """, (guild_id, caducidad_por_defecto(), str(user_id), max_servers))


async def alta_producto3(guild_id, user_id, max_bots, expira):
    """sirve para el alta y para la renovación"""
    nombre = str(user_id)[:20]
    if max_bots is None:
        # sku que no conozco: max_bots se queda como esté en la tabla
        await db.ejecutar("""
            INSERT INTO clientes_producto3 (guild_id, buyer_user_id, expires_at, nombre)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                expires_at = VALUES(expires_at),
                status = 'active',
                buyer_user_id = VALUES(buyer_user_id)
        """, (guild_id, user_id, expira, nombre))
    else:
        await db.ejecutar("""
            INSERT INTO clientes_producto3
                (guild_id, buyer_user_id, expires_at, nombre, max_bots)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                expires_at = VALUES(expires_at),
                status = 'active',
                buyer_user_id = VALUES(buyer_user_id),
                max_bots = VALUES(max_bots)
        """, (guild_id, user_id, expira, nombre, max_bots))


async def alta_cuenta_producto4(guild_id, usuario, hash_clave, entitlement_id):
    # el entitlement va por cuenta y no por servidor: un servidor puede tener varias licencias
    await db.ejecutar("""
        INSERT INTO cuentas_producto4
            (server_id, username, password_hash, expires_at, entitlement_id)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            expires_at = VALUES(expires_at),
            status = 'active',
            entitlement_id = VALUES(entitlement_id)
    """, (guild_id, usuario, hash_clave, caducidad_por_defecto(), entitlement_id))


# ENTITLEMENT_DELETE no es una baja normal (esas discord las deja caducar solas), es un
# reembolso o un contracargo. por eso se corta en el momento y no a fin de mes.
# se pone a 0 el entitlement y también la fecha: los bots dan acceso si vale cualquiera de los dos

async def cortar_servidor(tabla, guild_id):
    await db.ejecutar(f"""
        UPDATE {tabla} SET entitlement = 0, status = 'expired', expires_at = UTC_TIMESTAMP()
        WHERE server_id = %s
    """, (guild_id,))
    log.info("%s: suscripción de %s cortada", tabla, guild_id)


async def cortar_producto3(guild_id, user_id):
    if user_id is not None:
        # si el reembolso es de un comprador anterior (un contracargo puede llegar semanas
        # después) no se corta: el servidor puede tenerlo pagado ahora otra persona
        fila = await db.buscar(
            "SELECT buyer_user_id FROM clientes_producto3 WHERE guild_id = %s", (guild_id,))
        if fila and fila[0] is not None and str(fila[0]) != str(user_id):
            log.info("producto3: reembolso de %s en %s, que no es el comprador; no corto",
                     user_id, guild_id)
            return
    await db.ejecutar("""
        UPDATE clientes_producto3
        SET entitlement = 0, status = 'expired', expires_at = UTC_TIMESTAMP()
        WHERE guild_id = %s
    """, (guild_id,))
    log.info("producto3: suscripción de %s cortada", guild_id)
