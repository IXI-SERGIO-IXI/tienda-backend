# DMs a los clientes después de comprar. van por la api rest de discord con el token del bot,
# sin tener un bot conectado

import json
import logging
import mimetypes
from pathlib import Path

import aiohttp

from app import config
from app.tareas import en_segundo_plano

log = logging.getLogger(__name__)

API = "https://discord.com/api/v10"
IMAGENES = Path(__file__).resolve().parent.parent / "assets"
COLOR = 0x6000E9


def _ayuda(que):
    return (f"Need anything? Open a **ticket** in <#{config.CANAL_SOPORTE}> and I'll get back "
            f"to you. And if you can't get {que} configured for any reason, I can set it up "
            f"**for you** — just ask!")


BIENVENIDAS = {
    "producto1": {
        "titulo": "## ✅ PRODUCTO 1 — ACTIVATED",
        "nombre": "Producto 1",
        "cuerpo": "TEXTO CON LOS PRIMEROS PASOS",
        "imagen": "producto1.png",
    },
    "producto2": {
        "titulo": "## ✅ PRODUCTO 2 — ACTIVATED",
        "nombre": "Producto 2",
        "cuerpo": "TEXTO CON LOS PRIMEROS PASOS",
        "imagen": "producto2.png",
    },
    "producto3": {
        "titulo": "## ✅ PRODUCTO 3 — ACTIVATED",
        "nombre": "Producto 3",
        "cuerpo": "TEXTO CON LOS PRIMEROS PASOS",
        "imagen": "producto3.png",
    },
}

INSTRUCCIONES_PRODUCTO4 = "\n".join([
    "## INSTRUCTIONS",
    "- PASO 1: DESCARGAR LA APLICACIÓN",
    "- PASO 2: INICIAR SESIÓN CON EL USUARIO Y LA CONTRASEÑA DE ARRIBA",
    f"- PASO 3: VER EL TUTORIAL <#{config.CANAL_TUTORIAL}>",
])


def _texto(contenido):
    return {"type": 10, "content": contenido}


SEPARADOR = {"type": 14}


def bienvenida(user_id, producto):
    # en segundo plano: subir la imagen tarda y discord repetiría el webhook si esperamos
    if producto in BIENVENIDAS:
        en_segundo_plano(_bienvenida(user_id, BIENVENIDAS[producto]))


async def _bienvenida(user_id, plantilla):
    componentes = [
        _texto(plantilla["titulo"]),
        SEPARADOR,
        _texto(f"Thank you for your purchase! 💜 **{plantilla['nombre']}** is now active on "
               f"your server."),
        _texto(plantilla["cuerpo"]),
        _texto(_ayuda("the bot")),
        SEPARADOR,
        _texto(f"-# MARCA · {plantilla['nombre']} · Automated message — do not reply"),
    ]
    try:
        await _mandar_dm(user_id, componentes, plantilla["imagen"])
        log.info("bienvenida de %s enviada a %s", plantilla["nombre"], user_id)
    except Exception as e:
        log.warning("no pude mandar la bienvenida a %s (%s)", user_id, e)


async def credenciales_producto4(user_id, usuario, clave):
    componentes = [
        _texto("## ✅ PRODUCTO 4 — ACCOUNT READY"),
        SEPARADOR,
        _texto("Thank you for your purchase! 💜 Your **Producto 4** account is ready:"),
        _texto(f"**USERNAME:** `{usuario}`\n**PASSWORD:** `{clave}`"),
        SEPARADOR,
        _texto(INSTRUCCIONES_PRODUCTO4),
        SEPARADOR,
        _texto(_ayuda("it")),
        _texto("-# MARCA · Producto 4 · Automated message — do not reply"),
    ]
    try:
        await _mandar_dm(user_id, componentes, "producto4.png")
        log.info("credenciales enviadas a %s (usuario %s)", user_id, usuario)
    except Exception as e:
        # la contraseña no sale en el log. la cuenta ya está creada, así que se le genera
        # una nueva y se le da a mano
        log.warning("no pude mandar las credenciales a %s (%s). genera una clave nueva con: "
                    "python -m app.nueva_clave %s", user_id, e, usuario)


def _mensaje(componentes, imagen):
    """el mensaje en formato components v2 y la ruta de la imagen, si existe"""
    caja = {"type": 17, "accent_color": COLOR, "components": list(componentes)}
    mensaje = {"flags": 32768, "components": [caja]}
    ruta = IMAGENES / imagen if imagen else None
    if ruta is None or not ruta.exists():
        if imagen:
            log.warning("falta %s en assets/, el DM sale sin imagen", imagen)
        return mensaje, None
    galeria = {"type": 12, "items": [{"media": {"url": f"attachment://{imagen}"}}]}
    caja["components"].append(galeria)
    mensaje["attachments"] = [{"id": 0, "filename": imagen}]
    return mensaje, ruta


async def _mandar_dm(user_id, componentes, imagen=None):
    mensaje, ruta = _mensaje(componentes, imagen)
    cabeceras = {"Authorization": f"Bot {config.TOKEN_BOT}", "User-Agent": config.USER_AGENT}
    async with aiohttp.ClientSession(headers=cabeceras,
                                     timeout=aiohttp.ClientTimeout(total=30)) as sesion:
        # primero hay que abrir (o recuperar) el canal de DM con el usuario
        async with sesion.post(f"{API}/users/@me/channels",
                               json={"recipient_id": str(user_id)}) as r:
            if r.status >= 300:
                raise RuntimeError(f"no pude abrir el DM: {r.status}")
            canal = (await r.json())["id"]

        if ruta is None:
            envio = {"json": mensaje}
        else:
            # con imagen va como multipart: el json en payload_json y el fichero en files[0]
            form = aiohttp.FormData()
            form.add_field("payload_json", json.dumps(mensaje), content_type="application/json")
            form.add_field("files[0]", ruta.read_bytes(), filename=ruta.name,
                           content_type=mimetypes.guess_type(ruta.name)[0])
            envio = {"data": form}
        async with sesion.post(f"{API}/channels/{canal}/messages", **envio) as r:
            if r.status >= 300:
                raise RuntimeError(f"discord respondió {r.status}: {(await r.text())[:200]}")
