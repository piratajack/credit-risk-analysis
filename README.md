# Análisis de Riesgo de Crédito

Sistema de punta a punta que predice la probabilidad de que un cliente caiga en impago en los próximos dos años, usando SQL, Python y Machine Learning, con reportes automáticos en Excel y un dashboard interactivo.


## Etapas del proyecto

| Etapa | Descripción | Estado |
|---|---|---|
| 1. Datos | Limpieza del dataset y reglas de calidad | ✅ |
| 2. SQL | Base de datos y consultas de negocio | ✅ |
| 3. Machine Learning | Modelo de probabilidad de impago | ✅ |
| 4. Excel + dashboard | Reporte automático y app en Streamlit | ✅ |

## Datos

Dataset [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit/data) (Kaggle): unos 150.000 clientes con historial de crédito anonimizado.

Reglas de limpieza aplicadas en `src/load_data.py`:

- Se eliminan clientes con edad menor a 18 (errores de captura).
- Se eliminan los códigos especiales 96 y 98 en las columnas de mora.
- Se eliminan utilizaciones de crédito mayores a 1000 %.
- El ingreso vacío se imputa con la mediana y se marca con `ingreso_imputado = 1`.

## Hallazgos del análisis SQL

<!-- Completa esta sección con tus resultados reales al ejecutar run_queries.py -->

- Tasa de impago general: **X %**
- Los clientes menores de 30 años tienen una tasa de impago de **X %**, frente a **X %** en mayores de 60.
- Haber tenido 3 o más moras multiplica el riesgo por **X**.

## Modelo de Machine Learning

`src/train_model.py` compara dos modelos con validación cruzada estratificada (5 folds) y se queda con el de mejor AUC:

- **Regresión logística** (con `log1p` + estandarización): modelo base, fácil de explicar.
- **Gradient Boosting** (`HistGradientBoostingClassifier`): captura relaciones no lineales.

Variables nuevas: `total_moras`, `ingreso_por_persona` (ingreso / (dependientes + 1)) y `tuvo_mora_grave`.

El modelo elegido se evalúa **una sola vez** en un 20 % de clientes reservado desde el inicio. Métricas reportadas:

| Métrica | Qué mide |
|---|---|
| AUC / Gini | Capacidad de ordenar clientes de menor a mayor riesgo (Gini = 2·AUC − 1) |
| KS | Máxima separación entre buenos y malos pagadores |
| Brier | Qué tan bien calibradas están las probabilidades |

<!-- Completa con tus resultados reales al entrenar con cs-training.csv -->
Resultados en el conjunto de prueba: AUC **X**, Gini **X**, KS **X**.

Cada cliente recibe una probabilidad de impago **fuera de muestra** (`cross_val_predict`, para que ningún cliente sea calificado por un modelo que ya lo vio) y un segmento:

| Segmento | Probabilidad de impago |
|---|---|
| Bajo | < 5 % |
| Medio | 5 – 15 % |
| Alto | 15 – 30 % |
| Muy alto | ≥ 30 % |

Se guardan en la tabla `predicciones` de la base de datos.

## Reporte en Excel y dashboard

- `src/make_report.py` genera `reports/reporte_riesgo_AAAA-MM.xlsx` con hojas de resumen, segmentos, calibración por deciles, importancia de variables, los 500 clientes más riesgosos y los resultados de cada consulta SQL, con formato y gráficos nativos de Excel.
- `app/dashboard.py` es una app en Streamlit (ver la sección siguiente).

## Buscador de créditos (app web)

Una app donde cada persona crea su cuenta, escribe sus propios datos y compara créditos reales de los bancos de Colombia:

1. **Inicio con registro e inicio de sesión** (`app/auth.py`):
   - Contraseñas con hash PBKDF2-SHA256 (600.000 iteraciones) y sal aleatoria por usuario.
   - Bloqueo de 15 minutos tras 5 intentos fallidos.
   - Contraseñas con letras y números, y rechazo de las más comunes.
   - Autorización de tratamiento de datos (Ley 1581 de 2012) y botón para que cada usuario borre su cuenta.
   - No se piden cédulas ni datos bancarios.
2. **Perfil de riesgo.** El modelo de la etapa 3 estima la probabilidad de impago a partir del historial de pagos, el uso de tarjetas y el nivel de endeudamiento.
3. **Capacidad de pago.** Las deudas no deberían superar el 40 % del ingreso (30 % para la cuota de vivienda).
4. **Comparación de bancos.** `src/load_bank_rates.py` descarga de [datos.gov.co](https://www.datos.gov.co/) las tasas que cada banco reportó a la Superintendencia Financiera en las últimas 4 semanas (Formato 088) y la tasa de usura vigente. Para cada banco se estima la tasa del usuario según su riesgo, la cuota mensual, el total a pagar y una probabilidad de aprobación, con la descripción del banco y el enlace a su sitio.
5. **Sugerencias personalizadas.** Ajustar monto o plazo, preguntar por libranza, bajar el uso de tarjetas, revisar el reporte en las centrales de riesgo, entre otras.
6. **Historial.** Cada usuario ve sus búsquedas anteriores.

> ⚠️ El modelo se entrenó con datos de Estados Unidos (*Give Me Some Credit*), así que el ingreso en pesos no entra al modelo: se usa solo para la capacidad de pago. Las tasas y la aprobación son estimaciones educativas, no una oferta ni asesoría financiera.

## Cómo ejecutarlo

```bash
git clone https://github.com/piratajack/credit-risk-analysis.git
cd credit-risk-analysis
pip install -r requirements.txt

# 1. Descarga cs-training.csv de Kaggle y ponlo en data/raw/
# 2. Limpia los datos y crea la base de datos
python src/load_data.py

# 3. Ejecuta las consultas de negocio (resultados en reports/sql/)
python src/run_queries.py

# 4. Entrena el modelo y califica a toda la cartera
python src/train_model.py

# 5. Genera el reporte en Excel y abre el dashboard
python src/make_report.py
python src/load_bank_rates.py   # tasas reales de los bancos (requiere internet)
python src/export_app_data.py --fuente kaggle   # empaqueta lo que usa la app en app_data/
streamlit run app/dashboard.py

# Tests
pytest
```

¿Sin cuenta de Kaggle? Puedes probar todo el flujo con datos sintéticos del mismo formato:

```bash
python src/make_sample_data.py
python src/load_data.py --csv data/raw/sample-training.csv
```

## Publicación en Streamlit Community Cloud

La app solo lee `app_data/` (no necesita los datos de Kaggle) y guarda los usuarios en PostgreSQL:

1. Crea una base PostgreSQL gratuita (por ejemplo en [Supabase](https://supabase.com) o [Neon](https://neon.tech)) y copia su cadena de conexión.
2. En [share.streamlit.io](https://share.streamlit.io), crea una app desde este repositorio con el archivo principal `app/dashboard.py`.
3. En **Advanced settings → Secrets**, agrega:
   ```toml
   DATABASE_URL = "postgresql://usuario:clave@servidor:5432/postgres"
   ```

Las tablas se crean solas la primera vez. En local, sin `DATABASE_URL`, se usa SQLite.

## Estructura

```
credit-risk-analysis/
├── data/
│   ├── raw/            # CSV original (no se sube a GitHub)
│   └── processed/      # Base de datos SQLite
├── sql/
│   ├── schema.sql      # Definición de tablas
│   └── queries.sql     # Consultas de negocio
├── src/
│   ├── load_data.py        # Limpieza y carga (ETL)
│   ├── run_queries.py      # Ejecuta consultas y exporta CSV
│   ├── features.py         # Variables del modelo y segmentos de riesgo
│   ├── train_model.py      # Entrenamiento, evaluación y predicciones
│   ├── make_report.py      # Reporte automático en Excel
│   ├── load_bank_rates.py  # Descarga tasas reales por banco (datos.gov.co)
│   ├── export_app_data.py  # Empaqueta los datos de la app en app_data/
│   └── make_sample_data.py # Datos sintéticos para pruebas
├── app/
│   ├── dashboard.py        # App en Streamlit: inicio, login y buscador de créditos
│   ├── bancos.py           # Catálogo de bancos, cuotas, capacidad de pago y sugerencias
│   ├── auth.py             # Registro, login, bloqueo por intentos, historial y borrado de cuenta
│   ├── politica_privacidad.md  # Política de tratamiento de datos (Ley 1581 de 2012)
│   └── estilos.py          # CSS y encabezado animado
├── app_data/           # Modelo, métricas, tasas y resúmenes que usa la app (sí se sube)
├── models/             # Modelo entrenado (.joblib)
├── tests/              # Tests con pytest
├── notebooks/          # Exploración
└── reports/            # Resultados y reportes
```

## Tecnologías

Python · Pandas · SQLite · SQL (CTEs, funciones de ventana) · scikit-learn · openpyxl · Streamlit · Plotly · API de datos abiertos (Socrata) · pytest

## Autor

**Omar Alejandro Rivera Molina** · [GitHub](https://github.com/piratajack)
