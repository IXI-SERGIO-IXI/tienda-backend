# acceso a mysql. el conector es síncrono, así que cada consulta va a un hilo aparte con
# asyncio.to_thread y la api sigue atendiendo mientras espera a la base de datos

import asyncio
import threading

from mysql.connector import pooling

from app import config

CONEXIONES = 5

_pool = None
_lock = threading.Lock()
# el pool da error si se le piden más conexiones de las que tiene, en vez de esperar.
# por eso no dejo que haya más consultas a la vez que conexiones
_turnos = asyncio.Semaphore(CONEXIONES)


def _conexion():
    global _pool
    with _lock:
        if _pool is None:
            _pool = pooling.MySQLConnectionPool(pool_name="tienda", pool_size=CONEXIONES,
                                                autocommit=True, **config.DB)
    conexion = _pool.get_connection()
    # el pool resetea la sesión al devolver cada conexión, así que la zona horaria se pone
    # cada vez que se coge una
    cursor = conexion.cursor()
    cursor.execute("SET time_zone = '+00:00'")
    cursor.close()
    return conexion


def _ejecutar(sql, params):
    conexion = _conexion()
    try:
        cursor = conexion.cursor()
        cursor.execute(sql, params)
        filas = cursor.rowcount
        cursor.close()
        return filas
    finally:
        conexion.close()  # con el pool, close() la devuelve en vez de cerrarla


def _buscar(sql, params):
    conexion = _conexion()
    try:
        cursor = conexion.cursor(buffered=True)
        cursor.execute(sql, params)
        fila = cursor.fetchone()
        cursor.close()
        return fila
    finally:
        conexion.close()


async def ejecutar(sql, params=()):
    """devuelve cuántas filas ha tocado"""
    async with _turnos:
        return await asyncio.to_thread(_ejecutar, sql, params)


async def buscar(sql, params=()):
    async with _turnos:
        return await asyncio.to_thread(_buscar, sql, params)
