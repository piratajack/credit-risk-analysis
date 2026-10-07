"""Descarga las tasas de crédito reales por banco desde datos.gov.co y las guarda en SQLite.

Fuente: Superintendencia Financiera de Colombia (Formato 088), publicada en datos abiertos.
  - Tasas por tipo de crédito, últimos dos meses: dataset qzsc-9esp
  - Interés bancario corriente (para calcular la tasa de usura): dataset pare-7x5i

Se toma el último mes disponible y se calcula, por banco, producto y plazo, la tasa
promedio ponderada por monto desembolsado (TEA), la mínima y la máxima.

Uso:
    python src/load_bank_rates.py
"""

import json
import logging
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import pandas as pd

from features import DB

API = "https://www.datos.gov.co/resource/{dataset}.json?"
TASAS, IBC = "qzsc-9esp", "pare-7x5i"

# Producto que ve el usuario -> productos del Formato 088
PRODUCTOS = {
    "Libre inversión": ["Libre inversión"],
    "Libranza": ["Libranza otros"],
    "Vehículo": ["Vehículo"],
    "Vivienda": ["Adquisición de vivienda no vis (colocación en pesos)"],
    "Vivienda VIS": ["Adquisición de vivienda vis (colocación en pesos)"],
    "Tarjeta de crédito": ["Tarjeta de crédito para ingresos superiores a 2 SMMLV",
                           "Tarjeta de crédito para ingresos hasta 2 SMMLV"],
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def consultar(dataset: str, **params) -> list[dict]:
    url = API.format(dataset=dataset) + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=300) as resp:
        return json.load(resp)


def ultima_fecha() -> datetime:
    fila = consultar(TASAS, **{"$select": "max(fecha_corte) as f",
                               "$where": "producto_de_cr_dito='Libre inversión'"})[0]
    return datetime.fromisoformat(fila["f"][:10])


def descargar_tasas(desde: datetime) -> pd.DataFrame:
    filas = []
    for producto, originales in PRODUCTOS.items():
        lista = ", ".join(f"'{p}'" for p in originales)
        datos = consultar(TASAS, **{
            "$select": ("codigo_entidad, nombre_entidad, plazo_de_cr_dito AS plazo, "
                        "sum(montos_desembolsados) AS monto, sum(numero_de_creditos) AS creditos, "
                        "sum(tasa_efectiva_promedio * montos_desembolsados) / sum(montos_desembolsados) AS tasa, "
                        "min(tasa_efectiva_promedio) AS tasa_min, max(tasa_efectiva_promedio) AS tasa_max"),
            "$where": (f"tipo_entidad='1' AND tipo_de_persona='Natural' AND producto_de_cr_dito IN ({lista}) "
                       f"AND fecha_corte >= '{desde:%Y-%m-%d}' AND montos_desembolsados > 0"),
            "$group": "codigo_entidad, nombre_entidad, plazo_de_cr_dito",
            "$limit": 5000,
        })
        log.info("%-20s %d combinaciones banco-plazo", producto, len(datos))
        filas += [{**d, "producto": producto} for d in datos]

    df = pd.DataFrame(filas)
    for col in ["monto", "creditos", "tasa", "tasa_min", "tasa_max"]:
        df[col] = pd.to_numeric(df[col])
    df["codigo_entidad"] = df["codigo_entidad"].astype(int)
    return df


def descargar_usura() -> pd.DataFrame:
    """La tasa de usura es 1,5 veces el interés bancario corriente vigente."""
    filas = consultar(IBC, **{"$order": "vigencia_desde DESC", "$limit": 20})
    df = pd.DataFrame(filas)
    df = df[df["vigencia_desde"] == df["vigencia_desde"].max()]
    df["ibc"] = df["interes_bancario_corriente"].str.rstrip("%").astype(float)
    df["usura"] = (df["ibc"] * 1.5).round(2)
    df["vigencia_desde"] = df["vigencia_desde"].str[:10]
    df["vigencia_hasta"] = df["vigencia_hasta"].str[:10]
    return df[["modalidad", "ibc", "usura", "vigencia_desde", "vigencia_hasta"]]


def main() -> None:
    fin = ultima_fecha()
    desde = fin - timedelta(days=27)  # las últimas 4 semanas reportadas
    log.info("Descargando tasas reportadas entre %s y %s", f"{desde:%Y-%m-%d}", f"{fin:%Y-%m-%d}")
    tasas = descargar_tasas(desde)
    tasas["periodo"] = f"{desde:%Y-%m-%d} a {fin:%Y-%m-%d}"
    usura = descargar_usura()

    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as conn:
        tasas.to_sql("tasas_bancos", conn, if_exists="replace", index=False)
        usura.to_sql("tasa_usura", conn, if_exists="replace", index=False)
    log.info("%d filas guardadas en tasas_bancos (%d bancos)", len(tasas), tasas["codigo_entidad"].nunique())
    log.info("Usura consumo vigente: %s %%",
             usura.loc[usura["modalidad"] == "CONSUMO Y ORDINARIO", "usura"].iloc[0])


if __name__ == "__main__":
    main()
