-- Esquema de la base de datos de riesgo de crédito
-- Fuente: "Give Me Some Credit" (Kaggle), archivo cs-training.csv

DROP TABLE IF EXISTS clientes;

CREATE TABLE clientes (
    cliente_id              INTEGER PRIMARY KEY,
    impago_2_anios          INTEGER NOT NULL CHECK (impago_2_anios IN (0, 1)),  -- variable objetivo
    utilizacion_credito     REAL,     -- saldo de tarjetas / límite total
    edad                    INTEGER NOT NULL,
    mora_30_59_dias         INTEGER,  -- veces con mora de 30 a 59 días
    ratio_deuda             REAL,     -- pagos mensuales de deuda / ingreso mensual
    ingreso_mensual         REAL,
    ingreso_imputado        INTEGER NOT NULL DEFAULT 0,  -- 1 si el ingreso venía vacío
    lineas_credito_abiertas INTEGER,
    mora_90_dias            INTEGER,  -- veces con mora de 90 días o más
    creditos_hipotecarios   INTEGER,
    mora_60_89_dias         INTEGER,
    dependientes            INTEGER
);

CREATE INDEX idx_clientes_edad ON clientes (edad);
CREATE INDEX idx_clientes_impago ON clientes (impago_2_anios);
