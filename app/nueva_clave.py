# contraseña nueva para una cuenta del producto 4, para cuando el DM con las credenciales no
# llega. como solo se guarda el hash, la antigua no se puede recuperar.
# uso: python -m app.nueva_clave <usuario>

import asyncio
import sys

from app import claves, db


async def main(usuario):
    clave = claves.nueva_clave()
    hash_clave = await asyncio.to_thread(claves.hashear, clave)
    cambiadas = await db.ejecutar(
        "UPDATE cuentas_producto4 SET password_hash = %s WHERE username = %s",
        (hash_clave, usuario))
    if not cambiadas:
        sys.exit(f"no existe la cuenta {usuario}")
    # solo sale por pantalla esta vez, no se guarda en ningún sitio
    print(f"nueva contraseña de {usuario}: {clave}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python -m app.nueva_clave <usuario>")
    asyncio.run(main(sys.argv[1]))
