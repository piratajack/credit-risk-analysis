import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import auth  # noqa: E402
from bancos import (Perfil, buscar_bancos, capacidad_pago, cuota, monto_maximo,  # noqa: E402
                    plazo_categoria, sugerencias, tasa_estimada)


def perfil(**cambios) -> Perfil:
    base = dict(edad=35, situacion="Empleado", ingreso=4_000_000, pagos_deudas=400_000, dependientes=1,
                creditos_abiertos=3, creditos_vivienda=0, uso_tarjetas=0.3, mora_30=0, mora_60=0, mora_90=0)
    return Perfil(**{**base, **cambios})


def tasas_prueba() -> pd.DataFrame:
    fila = dict(producto="Libre inversión", plazo="Más de 1 año y hasta 3 años", periodo="x")
    return pd.DataFrame([
        {**fila, "codigo_entidad": 7, "nombre_entidad": "A", "monto": 1e9, "creditos": 500, "tasa": 20.0, "tasa_min": 15.0, "tasa_max": 28.0},
        {**fila, "codigo_entidad": 39, "nombre_entidad": "B", "monto": 1e9, "creditos": 500, "tasa": 24.0, "tasa_min": 18.0, "tasa_max": 28.5},
        {**fila, "codigo_entidad": 62, "nombre_entidad": "C", "monto": 1e6, "creditos": 1, "tasa": 10.0, "tasa_min": 10.0, "tasa_max": 10.0},
        {**fila, "producto": "Libranza", "codigo_entidad": 2, "nombre_entidad": "D", "monto": 1e9, "creditos": 500, "tasa": 14.0, "tasa_min": 12.0, "tasa_max": 18.0},
    ])


def test_cuota_y_monto_maximo_son_inversos():
    c = cuota(10_000_000, 24.0, 36)
    assert 380_000 < c < 400_000  # cuota conocida para 24 % E.A. a 36 meses
    assert monto_maximo(c, 24.0, 36) == pytest.approx(10_000_000)
    assert cuota(1_200_000, 0, 12) == 100_000


def test_plazo_categoria():
    assert plazo_categoria(12) == "Entre 31 días y 1 año"
    assert plazo_categoria(36) == "Más de 1 año y hasta 3 años"
    assert plazo_categoria(240) == "Más de 10 años"


def test_capacidad_de_pago():
    assert capacidad_pago(perfil(), "Libre inversión") == pytest.approx(1_200_000)
    assert capacidad_pago(perfil(pagos_deudas=0), "Vivienda") == pytest.approx(1_200_000)
    assert capacidad_pago(perfil(pagos_deudas=3_000_000), "Libre inversión") == 0


def test_tasa_estimada_sube_con_el_riesgo():
    tasas = [tasa_estimada(20, 15, 28, s) for s in ["1. Bajo", "2. Medio", "3. Alto", "4. Muy alto"]]
    assert tasas == sorted(tasas)
    assert tasas[1] == 20 and tasas[3] == 28


def test_buscar_bancos():
    res = buscar_bancos(tasas_prueba(), perfil(), "2. Medio", "Libre inversión", 10_000_000, 36, usura=28.59)
    assert res["codigo"].tolist() == [7, 39]          # el banco con 1 crédito se descarta
    assert res.iloc[0]["aprobacion"] == "Alta"        # cuota ~380 mil < capacidad 1,2 millones
    alto = buscar_bancos(tasas_prueba(), perfil(), "4. Muy alto", "Libre inversión", 10_000_000, 36, usura=28.2)
    assert (alto["tasa_estimada"] <= 28.2).all()      # nunca supera la usura
    assert (alto["aprobacion"] == "Baja").all()


def test_sugerencias_libranza_y_monto():
    tasas = tasas_prueba()
    p = perfil(ingreso=1_500_000, pagos_deudas=300_000, uso_tarjetas=0.9, mora_30=2)
    res = buscar_bancos(tasas, p, "2. Medio", "Libre inversión", 30_000_000, 36, usura=28.59)
    titulos = [t for _, t, _ in sugerencias(p, "2. Medio", "Libre inversión", 30_000_000, 36, res, tasas)]
    assert "Ajusta el monto o el plazo" in titulos
    assert "Pregunta por un crédito de libranza" in titulos
    assert "Baja el uso de tus tarjetas" in titulos
    assert "Revisa tu historial de crédito" in titulos


def test_registro_y_login(tmp_path):
    db = f"sqlite:///{(tmp_path / 'u.db').as_posix()}"
    assert auth.registrar("Ana", "ana@correo.com", "clave-segura-1", True, db) is None
    assert auth.registrar("Ana", "ANA@correo.com", "otra-clave-99", True, db) == "Ya existe una cuenta con ese correo."
    assert auth.registrar("Ana", "no-es-correo", "clave-segura-1", True, db) == "El correo no es válido."
    assert auth.registrar("Ana", "b@correo.com", "corta1", True, db).startswith("La contraseña")
    assert auth.registrar("Ana", "b@correo.com", "solo-letras", True, db) == "La contraseña debe tener letras y números."
    assert auth.registrar("Ana", "b@correo.com", "abc12345", True, db) == "Esa contraseña es muy común. Elige otra."
    assert auth.registrar("Ana", "b@correo.com", "clave-segura-1", False, db).startswith("Debes aceptar")

    usuario, error = auth.iniciar_sesion("ana@correo.com", "mala-clave-1", db)
    assert usuario is None and error == "Correo o contraseña incorrectos."
    usuario, error = auth.iniciar_sesion(" Ana@Correo.com ", "clave-segura-1", db)
    assert error is None and usuario["nombre"] == "Ana"

    auth.guardar_busqueda(usuario["id"], {"producto": "Vehículo"}, db)
    assert auth.historial(usuario["id"], db)[0]["producto"] == "Vehículo"
    auth.eliminar_cuenta(usuario["id"], db)
    assert auth.historial(usuario["id"], db) == []
    assert auth.iniciar_sesion("ana@correo.com", "clave-segura-1", db)[0] is None


def test_bloqueo_tras_intentos_fallidos(tmp_path):
    db = f"sqlite:///{(tmp_path / 'u.db').as_posix()}"
    auth.registrar("Ana", "ana@correo.com", "clave-segura-1", True, db)
    for _ in range(auth.MAX_INTENTOS):
        assert auth.iniciar_sesion("ana@correo.com", "mala-clave-1", db)[0] is None
    # Bloqueado incluso con la contraseña correcta
    usuario, error = auth.iniciar_sesion("ana@correo.com", "clave-segura-1", db)
    assert usuario is None and error.startswith("Demasiados intentos")


def test_cuentas_antiguas_siguen_funcionando(tmp_path):
    """Las cuentas creadas con 200.000 iteraciones (sal sin prefijo) pueden seguir entrando."""
    db = f"sqlite:///{(tmp_path / 'u.db').as_posix()}"
    sal = "ab" * 16
    with auth.motor(db).begin() as conn:
        conn.execute(auth.insert(auth.usuarios).values(
            nombre="Viejo", email="v@correo.com", sal=sal, creado="2026-10-04",
            hash=auth._hash("clave-vieja-1", sal, auth.ITERACIONES_ANTIGUAS)))
    assert auth.iniciar_sesion("v@correo.com", "clave-vieja-1", db)[0]["nombre"] == "Viejo"
