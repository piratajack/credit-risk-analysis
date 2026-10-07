"""Rutas del proyecto y variables del modelo, compartidas por el entrenamiento, el reporte y el dashboard."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "credito.db"
MODELO = ROOT / "models" / "modelo_impago.joblib"
REPORTS = ROOT / "reports"

OBJETIVO = "impago_2_anios"
VARIABLES_BASE = [
    "utilizacion_credito",
    "edad",
    "mora_30_59_dias",
    "mora_60_89_dias",
    "mora_90_dias",
    "ratio_deuda",
    "ingreso_mensual",
    "ingreso_imputado",
    "lineas_credito_abiertas",
    "creditos_hipotecarios",
    "dependientes",
]
VARIABLES_NUEVAS = ["total_moras", "ingreso_por_persona", "tuvo_mora_grave"]
VARIABLES = VARIABLES_BASE + VARIABLES_NUEVAS

# Cortes de probabilidad para clasificar a cada cliente (la tasa base ronda el 6-7 %).
SEGMENTOS = [
    (0.00, 0.05, "1. Bajo"),
    (0.05, 0.15, "2. Medio"),
    (0.15, 0.30, "3. Alto"),
    (0.30, 1.01, "4. Muy alto"),
]


def crear_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega variables derivadas y devuelve solo las columnas que usa el modelo."""
    df = df.copy()
    df["total_moras"] = df["mora_30_59_dias"] + df["mora_60_89_dias"] + df["mora_90_dias"]
    df["ingreso_por_persona"] = df["ingreso_mensual"] / (df["dependientes"] + 1)
    df["tuvo_mora_grave"] = (df["mora_90_dias"] > 0).astype(int)
    return df[VARIABLES]


def segmentar(prob: pd.Series) -> pd.Series:
    """Asigna el segmento de riesgo según la probabilidad de impago."""
    cortes = [c[0] for c in SEGMENTOS] + [SEGMENTOS[-1][1]]
    etiquetas = [c[2] for c in SEGMENTOS]
    return pd.cut(prob, bins=cortes, labels=etiquetas, right=False).astype(str)
