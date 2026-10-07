"""Limpia el dataset "Give Me Some Credit" y lo carga en una base de datos SQLite.

Uso:
    python src/load_data.py
    python src/load_data.py --csv data/raw/cs-training.csv --db data/processed/credito.db
"""

import argparse
import logging
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "raw" / "cs-training.csv"
DEFAULT_DB = ROOT / "data" / "processed" / "credito.db"
SCHEMA = ROOT / "sql" / "schema.sql"

COLUMNAS = {
    "SeriousDlqin2yrs": "impago_2_anios",
    "RevolvingUtilizationOfUnsecuredLines": "utilizacion_credito",
    "age": "edad",
    "NumberOfTime30-59DaysPastDueNotWorse": "mora_30_59_dias",
    "DebtRatio": "ratio_deuda",
    "MonthlyIncome": "ingreso_mensual",
    "NumberOfOpenCreditLinesAndLoans": "lineas_credito_abiertas",
    "NumberOfTimes90DaysLate": "mora_90_dias",
    "NumberRealEstateLoansOrLines": "creditos_hipotecarios",
    "NumberOfTime60-89DaysPastDueNotWorse": "mora_60_89_dias",
    "NumberOfDependents": "dependientes",
}
COLUMNAS_MORA = ["mora_30_59_dias", "mora_60_89_dias", "mora_90_dias"]

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica las reglas de limpieza y devuelve un DataFrame listo para SQL."""
    df = df.rename(columns={df.columns[0]: "cliente_id"}).rename(columns=COLUMNAS)
    n_inicial = len(df)

    # 1. Edad: hay registros con edad 0, que son errores de captura.
    df = df[df["edad"] >= 18]

    # 2. Mora: los valores 96 y 98 son códigos especiales, no conteos reales.
    codigos_invalidos = df[COLUMNAS_MORA].isin([96, 98]).any(axis=1)
    df = df[~codigos_invalidos]

    # 3. Utilización: valores mayores a 10 (1000 %) son casi seguro errores.
    df = df[df["utilizacion_credito"] <= 10]

    # 4. Ingreso vacío: se imputa con la mediana y se marca con una bandera,
    #    porque la falta de ingreso puede ser informativa para el modelo.
    df["ingreso_imputado"] = df["ingreso_mensual"].isna().astype(int)
    df["ingreso_mensual"] = df["ingreso_mensual"].fillna(df["ingreso_mensual"].median())

    # 5. Dependientes vacíos: se asume 0.
    df["dependientes"] = df["dependientes"].fillna(0).astype(int)

    log.info("Filas: %d iniciales -> %d tras limpieza (%d eliminadas)",
             n_inicial, len(df), n_inicial - len(df))
    log.info("Ingresos imputados: %d", df["ingreso_imputado"].sum())
    log.info("Tasa de impago: %.2f %%", 100 * df["impago_2_anios"].mean())
    return df


def cargar(df: pd.DataFrame, db_path: Path) -> None:
    """Crea el esquema y carga los datos en SQLite."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        df.to_sql("clientes", conn, if_exists="append", index=False)
        total = conn.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    log.info("Base de datos creada en %s con %d clientes", db_path, total)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(
            f"No se encontró {args.csv}. Descarga cs-training.csv de "
            "https://www.kaggle.com/c/GiveMeSomeCredit/data y ponlo en data/raw/"
        )
    cargar(limpiar(pd.read_csv(args.csv)), args.db)


if __name__ == "__main__":
    main()
