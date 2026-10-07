"""Empaqueta en app_data/ lo que necesita la app web para funcionar sin la base de datos completa.

La carpeta app_data/ sí se sube a GitHub: tiene el modelo, las métricas, las tasas de los bancos
y resúmenes de la cartera, pero ningún cliente individual (las reglas de Kaggle no permiten
redistribuir el dataset).

Uso (después de train_model.py y load_bank_rates.py):
    python src/export_app_data.py --fuente kaggle
    python src/export_app_data.py --fuente sinteticos
"""

import argparse
import json
import shutil
import sqlite3
from datetime import date

import pandas as pd

from features import DB, MODELO, REPORTS, ROOT

APP_DATA = ROOT / "app_data"
FUENTES = {
    "kaggle": "el dataset público Give Me Some Credit (Kaggle, clientes de Estados Unidos)",
    "sinteticos": "datos sintéticos de demostración con el formato de Give Me Some Credit",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fuente", choices=FUENTES, required=True,
                        help="Con qué datos se entrenó el modelo (se muestra en la app)")
    args = parser.parse_args()
    if not (DB.exists() and MODELO.exists()):
        raise SystemExit("Primero ejecuta load_data.py, train_model.py y load_bank_rates.py")

    APP_DATA.mkdir(exist_ok=True)
    shutil.copy(MODELO, APP_DATA / MODELO.name)
    for archivo in ["metricas.json", "deciles.csv", "importancia_variables.csv"]:
        shutil.copy(REPORTS / "model" / archivo, APP_DATA / archivo)

    with sqlite3.connect(DB) as conn:
        pd.read_sql_query("SELECT * FROM tasas_bancos", conn).to_csv(APP_DATA / "tasas_bancos.csv", index=False)
        pd.read_sql_query("SELECT * FROM tasa_usura", conn).to_csv(APP_DATA / "tasa_usura.csv", index=False)
        cartera = pd.read_sql_query(
            "SELECT c.ingreso_mensual, p.segmento_riesgo FROM clientes c JOIN predicciones p USING (cliente_id)", conn)

    resumen = {
        "clientes": len(cartera),
        "ingreso_mediana": float(cartera["ingreso_mensual"].median()),
        "segmentos": cartera["segmento_riesgo"].value_counts().sort_index().to_dict(),
        "fuente": args.fuente,
        "fuente_texto": FUENTES[args.fuente],
        "exportado": date.today().isoformat(),
    }
    (APP_DATA / "resumen_cartera.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Datos de la app guardados en {APP_DATA}")


if __name__ == "__main__":
    main()
