import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from load_data import COLUMNAS, limpiar  # noqa: E402


def datos_de_prueba() -> pd.DataFrame:
    """Cinco clientes: dos válidos y tres con errores conocidos del dataset."""
    df = pd.DataFrame({
        "Unnamed: 0": [1, 2, 3, 4, 5],
        "SeriousDlqin2yrs": [0, 1, 0, 1, 0],
        "RevolvingUtilizationOfUnsecuredLines": [0.5, 0.9, 0.2, 0.4, 5000.0],
        "age": [35, 50, 0, 40, 30],
        "NumberOfTime30-59DaysPastDueNotWorse": [0, 2, 0, 98, 0],
        "DebtRatio": [0.3, 0.6, 0.1, 0.4, 0.2],
        "MonthlyIncome": [5000.0, np.nan, 3000.0, 4000.0, 2000.0],
        "NumberOfOpenCreditLinesAndLoans": [5, 8, 2, 3, 1],
        "NumberOfTimes90DaysLate": [0, 1, 0, 98, 0],
        "NumberRealEstateLoansOrLines": [1, 0, 0, 1, 0],
        "NumberOfTime60-89DaysPastDueNotWorse": [0, 1, 0, 98, 0],
        "NumberOfDependents": [2, np.nan, 0, 1, 0],
    })
    assert set(COLUMNAS) <= set(df.columns)
    return df


def test_elimina_registros_invalidos():
    limpio = limpiar(datos_de_prueba())
    # Se eliminan: edad 0 (id 3), código de mora 98 (id 4), utilización 5000 (id 5)
    assert limpio["cliente_id"].tolist() == [1, 2]


def test_imputa_ingreso_y_marca_bandera():
    limpio = limpiar(datos_de_prueba()).set_index("cliente_id")
    assert limpio.loc[2, "ingreso_imputado"] == 1
    assert limpio.loc[1, "ingreso_imputado"] == 0
    assert limpio["ingreso_mensual"].notna().all()


def test_dependientes_sin_nulos():
    limpio = limpiar(datos_de_prueba())
    assert limpio["dependientes"].notna().all()
    assert limpio["dependientes"].dtype.kind == "i"
