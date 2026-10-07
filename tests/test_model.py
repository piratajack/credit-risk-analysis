import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from features import VARIABLES, crear_features, segmentar  # noqa: E402
from load_data import limpiar  # noqa: E402
from make_sample_data import generar  # noqa: E402
from train_model import ks, tabla_deciles  # noqa: E402


def test_crear_features_columnas_y_valores():
    df = pd.DataFrame([{
        "utilizacion_credito": 0.5, "edad": 40, "mora_30_59_dias": 1, "mora_60_89_dias": 2,
        "mora_90_dias": 1, "ratio_deuda": 0.3, "ingreso_mensual": 6000.0, "ingreso_imputado": 0,
        "lineas_credito_abiertas": 5, "creditos_hipotecarios": 1, "dependientes": 2,
    }])
    X = crear_features(df)
    assert list(X.columns) == VARIABLES
    assert X.loc[0, "total_moras"] == 4
    assert X.loc[0, "ingreso_por_persona"] == 2000
    assert X.loc[0, "tuvo_mora_grave"] == 1


def test_segmentar_cortes():
    seg = segmentar(pd.Series([0.0, 0.049, 0.05, 0.2, 0.3, 1.0]))
    assert seg.tolist() == ["1. Bajo", "1. Bajo", "2. Medio", "3. Alto", "4. Muy alto", "4. Muy alto"]


def test_ks_separacion_perfecta_y_azar():
    y = np.array([0, 0, 1, 1])
    assert ks(y, np.array([0.1, 0.2, 0.8, 0.9])) == 1.0
    assert ks(y, np.array([0.5, 0.5, 0.5, 0.5])) == 0.0


def test_tabla_deciles():
    rng = np.random.default_rng(0)
    prob = rng.random(1000)
    y = rng.binomial(1, prob)
    tabla = tabla_deciles(y, prob)
    assert tabla["decil"].tolist() == list(range(1, 11))
    assert tabla["clientes"].sum() == 1000
    assert tabla.loc[9, "tasa_impago_real"] > tabla.loc[0, "tasa_impago_real"]
    assert np.isclose(tabla.loc[0, "impagos_capturados_acum"], 1.0)


def test_datos_sinteticos_pasan_la_limpieza():
    limpio = limpiar(generar(2000))
    assert 0 < len(limpio) < 2000
    assert limpio["edad"].min() >= 18
    assert limpio[["mora_30_59_dias", "mora_60_89_dias", "mora_90_dias"]].max().max() < 96
    assert crear_features(limpio).notna().all().all()
