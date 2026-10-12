# configuración del backend. lo secreto y lo que cambia entre entornos va en variables de
# entorno (en local, en el fichero .env)

import os

from dotenv import load_dotenv

load_dotenv()


def _variable(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        raise RuntimeError(f"falta la variable de entorno {nombre}")
    return valor


DB = {
    "host": _variable("DB_HOST"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": _variable("DB_USER"),
    "password": _variable("DB_PASSWORD"),
    "database": _variable("DB_NAME"),
}
TOKEN_BOT = _variable("DISCORD_BOT_TOKEN")  # el bot que manda los DM a los clientes
WEBHOOK_VENTAS = _variable("SALES_WEBHOOK_URL")  # canal privado donde me llegan las ventas

# cada app de discord firma sus webhooks con su propia clave pública
# (developer portal > general information)
CLAVES_PUBLICAS = {
    "producto1": _variable("DISCORD_PUBLIC_KEY_1"),
    "producto2": _variable("DISCORD_PUBLIC_KEY_2"),
    "producto3": _variable("DISCORD_PUBLIC_KEY_3"),
    "producto4": _variable("DISCORD_PUBLIC_KEY_4"),
}

USER_AGENT = "TiendaBackend/1.0"  # discord rechaza las peticiones sin user-agent

# canales que salen mencionados en los DM
CANAL_SOPORTE = 0
CANAL_TUTORIAL = 0

# sku de la tienda de discord -> cuántos servidores o bots incluye el plan.
# el bot de cada producto tiene el mismo mapa: si se cambia aquí, hay que cambiarlo allí
PLANES_PRODUCTO2 = {
    "sku_producto2_x1": 1,
    "sku_producto2_x2": 2,
    "sku_producto2_x3": 3,
    "sku_producto2_x4": 4,
}
PLANES_PRODUCTO3 = {
    "sku_producto3_x1": 1,
    "sku_producto3_x2": 2,
    "sku_producto3_x3": 3,
}

# los eventos de discord no traen el importe, así que el precio sale de aquí (de ejemplo)
PRECIOS = {
    "sku_producto1": 10.00,
    "sku_producto2_x1": 10.00,
    "sku_producto2_x2": 15.00,
    "sku_producto2_x3": 20.00,
    "sku_producto2_x4": 25.00,
    "sku_producto3_x1": 10.00,
    "sku_producto3_x2": 15.00,
    "sku_producto3_x3": 20.00,
    "sku_producto4_mensual": 10.00,
    "sku_producto4_plan1": 50.00,
    "sku_producto4_plan2": 75.00,
    "sku_producto4_plan3": 100.00,
}

# lo que me queda de cada venta después de la comisión de discord (sacado de ventas reales)
DISCORD_NETO = 0.799

NOMBRES = {
    "producto1": "Producto 1",
    "producto2": "Producto 2",
    "producto3": "Producto 3",
    "producto4": "Producto 4",
}
