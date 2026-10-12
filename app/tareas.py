import asyncio

# asyncio solo guarda una referencia débil a las tareas. si no las guardo yo, el recolector
# de basura se las puede llevar a medias
_vivas = set()


def en_segundo_plano(coro):
    tarea = asyncio.create_task(coro)
    _vivas.add(tarea)
    tarea.add_done_callback(_vivas.discard)
