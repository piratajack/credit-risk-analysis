"""Genera un CSV sintético con el mismo formato que cs-training.csv de Kaggle.

Sirve para probar el pipeline completo sin descargar el dataset real. Incluye los
mismos errores de captura (edad 0, códigos 96/98, utilización absurda, nulos) para
que la limpieza tenga algo que hacer. Los resultados NO representan clientes reales.

Uso:
    python src/make_sample_data.py
    python src/load_data.py --csv data/raw/sample-training.csv
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def generar(n: int, semilla: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    edad = rng.normal(52, 14, n).clip(21, 100).astype(int)
    utilizacion = rng.beta(0.6, 1.4, n) * 1.1
    ingreso = rng.lognormal(8.6, 0.6, n).round(0)
    dependientes = rng.poisson(0.75, n)
    lineas = rng.poisson(8, n)
    hipotecas = rng.poisson(1, n)
    ratio_deuda = rng.gamma(1.5, 0.25, n)

    # Las moras dependen de la utilización y la edad, como en la realidad
    riesgo_latente = 1.8 * utilizacion - 0.02 * (edad - 50) + rng.normal(0, 1, n)
    mora_30 = rng.poisson(np.exp(-1.6 + 0.8 * riesgo_latente).clip(0, 6))
    mora_60 = rng.poisson(np.exp(-2.8 + 0.8 * riesgo_latente).clip(0, 4))
    mora_90 = rng.poisson(np.exp(-2.9 + 0.9 * riesgo_latente).clip(0, 4))

    logit = (-4.1 + 1.6 * utilizacion + 0.45 * mora_30 + 0.7 * mora_60 + 0.9 * mora_90
             - 0.025 * (edad - 50) - 0.25 * (np.log(ingreso) - 8.6) + 0.1 * dependientes)
    impago = rng.binomial(1, 1 / (1 + np.exp(-logit)))

    df = pd.DataFrame({
        "": np.arange(1, n + 1),
        "SeriousDlqin2yrs": impago,
        "RevolvingUtilizationOfUnsecuredLines": utilizacion,
        "age": edad,
        "NumberOfTime30-59DaysPastDueNotWorse": mora_30,
        "DebtRatio": ratio_deuda,
        "MonthlyIncome": ingreso,
        "NumberOfOpenCreditLinesAndLoans": lineas,
        "NumberOfTimes90DaysLate": mora_90,
        "NumberRealEstateLoansOrLines": hipotecas,
        "NumberOfTime60-89DaysPastDueNotWorse": mora_60,
        "NumberOfDependents": dependientes.astype(float),
    })

    # Errores de captura como los del dataset original
    def filas(p):
        return rng.random(n) < p
    df.loc[filas(0.2), "MonthlyIncome"] = np.nan
    df.loc[filas(0.025), "NumberOfDependents"] = np.nan
    df.loc[filas(0.0005), "age"] = 0
    codigos = filas(0.002)
    for col in ["NumberOfTime30-59DaysPastDueNotWorse", "NumberOfTimes90DaysLate",
                "NumberOfTime60-89DaysPastDueNotWorse"]:
        df.loc[codigos, col] = 98
    df.loc[filas(0.002), "RevolvingUtilizationOfUnsecuredLines"] = 5000.0
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=30_000)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "raw" / "sample-training.csv")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    generar(args.n).to_csv(args.out, index=False)
    print(f"CSV sintético con {args.n} clientes en {args.out}")


if __name__ == "__main__":
    main()
