# Backend de la tienda

Backend en Python que gestiona las suscripciones de cuatro bots de Discord que se venden en
la tienda de Discord. Cuando alguien compra, renueva o pide un reembolso, Discord lo avisa por
webhook y el backend activa o corta el servicio en la base de datos, apunta la venta, la avisa
en un canal privado y le manda un DM al cliente.

Trabaja junto a la [tienda web](https://github.com/IXI-SERGIO-IXI/tienda-web): el Worker de
Cloudflare de la web recibe los webhooks de Discord y los reenvía aquí.

Los nombres de los productos, los planes y los precios son de ejemplo.

## Tecnologías

- Python y FastAPI
- MySQL
- PyNaCl para comprobar las firmas Ed25519 de Discord
- aiohttp para la API de Discord

## Productos

| Producto | Cómo se vende |
|---|---|
| 1 | Suscripción mensual para un servidor de Discord |
| 2 | Suscripción con planes según en cuántos servidores se usa |
| 3 | Suscripción con planes que se renueva con la fecha que manda Discord |
| 4 | Licencia de una aplicación de escritorio, con usuario y contraseña |

## Qué hace

- Cada app de Discord manda sus eventos a su ruta (`/webhook/bot-1` … `/webhook/bot-4`). Lo
  primero es comprobar la firma con la clave pública de esa app: sin ella nadie puede mandar
  compras falsas aunque conozca la URL.
- Una compra da de alta el servidor en la tabla de su producto, una renovación actualiza la
  fecha de caducidad y un reembolso corta el servicio en el momento. Si el reembolso es de un
  comprador anterior del mismo servidor (un contracargo puede llegar semanas después), no se le
  corta al que paga ahora.
- Los códigos de respuesta están pensados para los reintentos de Discord: si falla algo nuestro
  (la base de datos, por ejemplo) devuelve 500 y Discord vuelve a mandar el evento. Una firma
  mala o unos datos rotos devuelven 401 o 400 y no se reintentan.
- Discord puede mandar el mismo evento más de una vez, así que cada venta se apunta una sola
  vez y la cuenta del producto 4 no se crea dos veces.
- El producto 4 genera un usuario y una contraseña aleatorios y se los manda al cliente por DM.
  En la base de datos solo se guarda el hash (PBKDF2 con sal), y la contraseña no sale nunca en
  los logs. Si el DM no llega, `python -m app.nueva_clave <usuario>` genera otra.
- El conector de MySQL es síncrono, así que cada consulta va a un hilo aparte y usa un pool de
  conexiones: la API sigue atendiendo mientras espera a la base de datos.
- El aviso al canal de ventas y el DM de bienvenida van en segundo plano para contestar a
  Discord cuanto antes. Los DM se mandan con la API REST de Discord, sin tener un bot conectado.

## Estructura

```
app/
  main.py           arranque de la API
  webhooks.py       ruta de entrada, firma y códigos de respuesta
  productos.py      qué hace cada producto con cada evento
  suscripciones.py  altas, renovaciones y cortes en la base de datos
  ventas.py         registro de ventas y aviso en el canal
  mensajes.py       DMs a los clientes
  claves.py         usuarios, contraseñas y hashes del producto 4
  nueva_clave.py    comando para darle una contraseña nueva a una cuenta
  db.py             pool de conexiones a MySQL
  tareas.py         tareas en segundo plano
  config.py         configuración y variables de entorno
assets/             imágenes de los DM
```

## En local

Probado con Python 3.13.

```bash
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

Antes de arrancar hay que rellenar el `.env`. Si falta alguna variable, el programa no arranca
y dice cuál es. La API queda en `http://localhost:8080`.

## Despliegue

En el servidor se ponen las mismas variables de entorno que en `.env.example` y se arranca con
`python -m app.main`. Escucha en el puerto 8080.

En el portal de developers de cada app de Discord, la URL de los webhooks apunta al Worker de
la web (`/webhook/discord/bot-1`, etc.), que es el que los reenvía a este backend.
