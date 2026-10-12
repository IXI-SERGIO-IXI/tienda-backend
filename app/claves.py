# usuarios y contraseñas del producto 4. en la base de datos solo se guarda el hash, nunca la
# contraseña. uso pbkdf2 porque viene en la librería estándar de casi cualquier lenguaje y el
# login de la app de escritorio lo puede comprobar sin nada raro

import hashlib
import hmac
import secrets
import string

ITERACIONES = 600_000  # lo que recomienda owasp para pbkdf2-sha256


def _aleatorio(caracteres, largo):
    return "".join(secrets.choice(caracteres) for _ in range(largo))


def nuevo_usuario():
    return "user_" + _aleatorio(string.ascii_lowercase + string.digits, 8)


def nueva_clave():
    return _aleatorio(string.ascii_letters + string.digits, 12)


def hashear(clave):
    sal = secrets.token_bytes(16)
    resumen = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${resumen.hex()}"


def comprobar(clave, guardado):
    """así lo comprueba el login de la app"""
    try:
        _, iteraciones, sal, resumen = guardado.split("$")
        calculado = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal),
                                        int(iteraciones))
    except ValueError:
        return False
    # compare_digest tarda lo mismo acierte o falle: así no se puede adivinar por el tiempo
    return hmac.compare_digest(calculado.hex(), resumen)
