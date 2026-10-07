"""Entrena el modelo de probabilidad de impago y guarda modelo, métricas y predicciones.

Compara una regresión logística (modelo base, interpretable) con un Gradient Boosting
usando validación cruzada, elige el mejor por AUC y lo evalúa una sola vez en un
conjunto de prueba que nunca vio durante el entrenamiento.

Uso:
    python src/train_model.py
"""

import json
import logging
import sqlite3
from datetime import date

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from features import DB, MODELO, OBJETIVO, REPORTS, VARIABLES, crear_features, segmentar

SEMILLA = 42
OUT_DIR = REPORTS / "model"

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)


def candidatos() -> dict:
    """Modelos a comparar. La logística usa log1p porque ingreso y ratios tienen colas largas."""
    return {
        "Regresión logística": make_pipeline(
            FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            StandardScaler(),
            LogisticRegression(max_iter=1000),
        ),
        "Gradient Boosting": HistGradientBoostingClassifier(
            learning_rate=0.05, max_iter=300, max_leaf_nodes=31,
            min_samples_leaf=100, l2_regularization=1.0, random_state=SEMILLA,
        ),
    }


def ks(y, prob) -> float:
    """Estadístico Kolmogorov-Smirnov: máxima separación entre buenos y malos pagadores."""
    fpr, tpr, _ = roc_curve(y, prob)
    return float(np.max(tpr - fpr))


def tabla_deciles(y, prob) -> pd.DataFrame:
    """Agrupa en 10 deciles de riesgo (10 = más riesgoso) y compara tasa predicha vs. real."""
    df = pd.DataFrame({"real": np.asarray(y), "prob": prob})
    df["decil"] = pd.qcut(df["prob"].rank(method="first"), 10, labels=range(1, 11)).astype(int)
    tabla = df.groupby("decil").agg(
        clientes=("real", "size"),
        prob_promedio=("prob", "mean"),
        tasa_impago_real=("real", "mean"),
        impagos=("real", "sum"),
    ).reset_index()
    # % de todos los impagos capturados al revisar desde el decil más riesgoso hacia abajo
    tabla = tabla.sort_values("decil", ascending=False)
    tabla["impagos_capturados_acum"] = tabla["impagos"].cumsum() / tabla["impagos"].sum()
    return tabla.sort_values("decil").reset_index(drop=True)


def main() -> None:
    if not DB.exists():
        raise SystemExit("Primero ejecuta: python src/load_data.py")
    with sqlite3.connect(DB) as conn:
        datos = pd.read_sql_query("SELECT * FROM clientes", conn)

    X, y = crear_features(datos), datos[OBJETIVO]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEMILLA)
    log.info("Entrenamiento: %d clientes | Prueba: %d clientes", len(X_train), len(X_test))

    # 1. Comparar modelos con validación cruzada en el conjunto de entrenamiento
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMILLA)
    comparacion = {}
    for nombre, modelo in candidatos().items():
        auc = cross_val_score(modelo, X_train, y_train, cv=cv, scoring="roc_auc")
        comparacion[nombre] = {"auc_cv": round(auc.mean(), 4), "auc_cv_std": round(auc.std(), 4)}
        log.info("%-20s AUC CV = %.4f ± %.4f", nombre, auc.mean(), auc.std())
    elegido = max(comparacion, key=lambda n: comparacion[n]["auc_cv"])
    log.info("Modelo elegido: %s", elegido)

    # 2. Entrenar el elegido y evaluarlo una sola vez en prueba
    modelo = candidatos()[elegido].fit(X_train, y_train)
    prob_test = modelo.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, prob_test)
    metricas = {
        "modelo": elegido,
        "fecha_entrenamiento": date.today().isoformat(),
        "clientes_entrenamiento": len(X_train),
        "clientes_prueba": len(X_test),
        "tasa_impago": round(float(y.mean()), 4),
        "auc": round(auc, 4),
        "gini": round(2 * auc - 1, 4),
        "ks": round(ks(y_test, prob_test), 4),
        "brier": round(brier_score_loss(y_test, prob_test), 4),
        "comparacion_cv": comparacion,
    }
    log.info("Prueba -> AUC %.4f | Gini %.4f | KS %.4f | Brier %.4f",
             metricas["auc"], metricas["gini"], metricas["ks"], metricas["brier"])

    # 3. Importancia de variables (por permutación, comparable entre modelos)
    imp = permutation_importance(modelo, X_test, y_test, scoring="roc_auc",
                                 n_repeats=5, random_state=SEMILLA, n_jobs=-1)
    importancia = (pd.DataFrame({"variable": VARIABLES, "importancia": imp.importances_mean})
                   .sort_values("importancia", ascending=False))

    # 4. Probabilidad para toda la cartera. Se usan predicciones fuera de muestra
    #    (cross_val_predict) para que ningún cliente sea calificado por un modelo que ya lo vio.
    prob_cartera = cross_val_predict(candidatos()[elegido], X, y, cv=cv, method="predict_proba")[:, 1]
    predicciones = pd.DataFrame({
        "cliente_id": datos["cliente_id"],
        "prob_impago": prob_cartera.round(4),
        "segmento_riesgo": segmentar(pd.Series(prob_cartera)),
    })

    # 5. Guardar todo
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MODELO.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "variables": VARIABLES, "metricas": metricas}, MODELO)
    (OUT_DIR / "metricas.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False), encoding="utf-8")
    tabla_deciles(y_test, prob_test).to_csv(OUT_DIR / "deciles.csv", index=False)
    importancia.to_csv(OUT_DIR / "importancia_variables.csv", index=False)
    with sqlite3.connect(DB) as conn:
        predicciones.to_sql("predicciones", conn, if_exists="replace", index=False)

    log.info("Modelo guardado en %s", MODELO)
    log.info("Segmentos:\n%s", predicciones["segmento_riesgo"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
