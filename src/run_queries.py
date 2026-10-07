"""Ejecuta las consultas de sql/queries.sql, las muestra y las guarda como CSV en reports/.

Uso:
    python src/run_queries.py
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "credito.db"
QUERIES = ROOT / "sql" / "queries.sql"
OUT_DIR = ROOT / "reports" / "sql"


def leer_consultas(path: Path) -> dict[str, str]:
    """Separa el archivo .sql en consultas usando los marcadores '-- name: ...'."""
    bloques = re.split(r"^-- name:\s*(\w+)\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    # bloques = [encabezado, nombre1, sql1, nombre2, sql2, ...]
    return {nombre: sql.strip() for nombre, sql in zip(bloques[1::2], bloques[2::2])}


def main() -> None:
    if not DB.exists():
        raise SystemExit("Primero ejecuta: python src/load_data.py")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB) as conn:
        for nombre, sql in leer_consultas(QUERIES).items():
            df = pd.read_sql_query(sql, conn)
            df.to_csv(OUT_DIR / f"{nombre}.csv", index=False)
            print(f"\n=== {nombre} ===")
            print(df.to_string(index=False))

    print(f"\nResultados guardados en {OUT_DIR}")


if __name__ == "__main__":
    main()
