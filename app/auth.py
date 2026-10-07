"""Registro, inicio de sesión, historial de búsquedas y borrado de cuenta.

La base de datos se toma de la variable DATABASE_URL (PostgreSQL en la nube, p. ej. Supabase o Neon).
Si no existe, se usa un archivo SQLite local.

Seguridad:
- Las contraseñas nunca se guardan: se guarda un hash PBKDF2-SHA256 con sal aleatoria por usuario.
- Tras 5 intentos fallidos, el correo queda bloqueado 15 minutos.
- Se registra la fecha en que el usuario aceptó la política de tratamiento de datos (Ley 1581 de 2012).
"""

import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import (Column, ForeignKey, Integer, MetaData, String, Table, Text, create_engine, delete,
                        func, insert, inspect, select, text)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

DB_LOCAL = Path(__file__).resolve().parents[1] / "data" / "processed" / "usuarios.db"
ITERACIONES = 600_000          # recomendación de OWASP para PBKDF2-SHA256
ITERACIONES_ANTIGUAS = 200_000  # cuentas creadas antes del cambio
MAX_INTENTOS, BLOQUEO = 5, timedelta(minutes=15)
COLOMBIA = timezone(timedelta(hours=-5))
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
COMUNES = {"12345678", "123456789", "1234567890", "password", "password1", "contraseña", "qwerty123",
           "abc12345", "colombia", "colombia1", "iloveyou", "11111111", "00000000", "87654321", "admin123"}

metadata = MetaData()
usuarios = Table(
    "usuarios", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("nombre", String(100), nullable=False),
    Column("email", String(254), nullable=False, unique=True),
    Column("sal", String(80), nullable=False),
    Column("hash", String(128), nullable=False),
    Column("creado", String(32), nullable=False),
    Column("acepto_politica", String(32)),
)
busquedas = Table(
    "busquedas", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
    Column("fecha", String(32), nullable=False),
    Column("datos", Text, nullable=False),
)
intentos = Table(
    "intentos_login", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", String(254), nullable=False, index=True),
    Column("fecha", String(32), nullable=False),
)

_motores: dict[str, Engine] = {}


def url_base_datos() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        DB_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{DB_LOCAL.as_posix()}"
    # Supabase y Neon entregan "postgres://" o "postgresql://"; SQLAlchemy necesita el driver explícito
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg2://", url)


def motor(url: str | None = None) -> Engine:
    url = url or url_base_datos()
    if url not in _motores:
        eng = create_engine(url, pool_pre_ping=True)
        metadata.create_all(eng)
        # Bases creadas con la versión anterior no tienen esta columna
        if "acepto_politica" not in {c["name"] for c in inspect(eng).get_columns("usuarios")}:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN acepto_politica VARCHAR(32)"))
        _motores[url] = eng
    return _motores[url]


def _ahora() -> datetime:
    return datetime.now(COLOMBIA)


def _hash(password: str, sal: str, iteraciones: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), iteraciones).hex()


def _leer_sal(guardada: str) -> tuple[int, str]:
    """La sal se guarda como 'iteraciones$sal'. Las cuentas antiguas solo tienen la sal."""
    if "$" in guardada:
        n, sal = guardada.split("$", 1)
        return int(n), sal
    return ITERACIONES_ANTIGUAS, guardada


def validar_password(password: str) -> str | None:
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not (re.search(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]", password) and re.search(r"\d", password)):
        return "La contraseña debe tener letras y números."
    if password.lower() in COMUNES:
        return "Esa contraseña es muy común. Elige otra."
    return None


def registrar(nombre: str, email: str, password: str, acepta_politica: bool, url: str | None = None) -> str | None:
    """Crea el usuario. Devuelve un mensaje de error, o None si salió bien."""
    nombre, email = nombre.strip(), email.strip().lower()
    if len(nombre) < 2:
        return "Escribe tu nombre."
    if not EMAIL.match(email):
        return "El correo no es válido."
    if error := validar_password(password):
        return error
    if not acepta_politica:
        return "Debes aceptar la política de tratamiento de datos para crear tu cuenta."
    sal = secrets.token_hex(16)
    ahora = _ahora().isoformat(timespec="seconds")
    try:
        with motor(url).begin() as conn:
            conn.execute(insert(usuarios).values(
                nombre=nombre[:100], email=email, sal=f"{ITERACIONES}${sal}",
                hash=_hash(password, sal, ITERACIONES), creado=ahora, acepto_politica=ahora))
    except IntegrityError:
        return "Ya existe una cuenta con ese correo."
    return None


def iniciar_sesion(email: str, password: str, url: str | None = None) -> tuple[dict | None, str | None]:
    """Devuelve (usuario, None) si las credenciales son correctas, o (None, mensaje de error)."""
    email = email.strip().lower()
    eng = motor(url)
    desde = (_ahora() - BLOQUEO).isoformat(timespec="seconds")
    with eng.begin() as conn:
        fallidos = conn.execute(select(func.count()).select_from(intentos)
                                .where(intentos.c.email == email, intentos.c.fecha >= desde)).scalar()
        if fallidos >= MAX_INTENTOS:
            return None, "Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo."
        fila = conn.execute(select(usuarios.c.id, usuarios.c.nombre, usuarios.c.email, usuarios.c.sal, usuarios.c.hash)
                            .where(usuarios.c.email == email)).first()
        if fila:
            iteraciones, sal = _leer_sal(fila.sal)
            if hmac.compare_digest(_hash(password, sal, iteraciones), fila.hash):
                conn.execute(delete(intentos).where(intentos.c.email == email))
                return {"id": fila.id, "nombre": fila.nombre, "email": fila.email}, None
        conn.execute(insert(intentos).values(email=email, fecha=_ahora().isoformat(timespec="seconds")))
    return None, "Correo o contraseña incorrectos."


def guardar_busqueda(usuario_id: int, datos: dict, url: str | None = None) -> None:
    with motor(url).begin() as conn:
        conn.execute(insert(busquedas).values(usuario_id=usuario_id, fecha=_ahora().strftime("%Y-%m-%d %H:%M"),
                                              datos=json.dumps(datos, ensure_ascii=False)))


def historial(usuario_id: int, url: str | None = None) -> list[dict]:
    with motor(url).connect() as conn:
        filas = conn.execute(select(busquedas.c.fecha, busquedas.c.datos)
                             .where(busquedas.c.usuario_id == usuario_id)
                             .order_by(busquedas.c.id.desc()).limit(50)).all()
    return [{"fecha": f, **json.loads(d)} for f, d in filas]


def eliminar_cuenta(usuario_id: int, url: str | None = None) -> None:
    """Borra el usuario y todo su historial (derecho de supresión, Ley 1581 de 2012)."""
    with motor(url).begin() as conn:
        email = conn.execute(select(usuarios.c.email).where(usuarios.c.id == usuario_id)).scalar()
        conn.execute(delete(busquedas).where(busquedas.c.usuario_id == usuario_id))
        conn.execute(delete(intentos).where(intentos.c.email == email))
        conn.execute(delete(usuarios).where(usuarios.c.id == usuario_id))
