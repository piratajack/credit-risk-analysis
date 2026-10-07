-- Consultas de negocio sobre la cartera de crédito.
-- Cada consulta empieza con "-- name: <nombre>" para que src/run_queries.py la ejecute por separado.

-- name: resumen_cartera
-- ¿Cuántos clientes hay y qué porcentaje cayó en impago?
SELECT
    COUNT(*)                                AS total_clientes,
    SUM(impago_2_anios)                     AS clientes_en_impago,
    ROUND(100.0 * AVG(impago_2_anios), 2)   AS tasa_impago_pct,
    ROUND(AVG(ingreso_mensual), 0)          AS ingreso_promedio
FROM clientes;

-- name: impago_por_edad
-- ¿Cómo cambia el riesgo según la edad?
SELECT
    CASE
        WHEN edad < 30 THEN '1. Menor de 30'
        WHEN edad < 45 THEN '2. 30 a 44'
        WHEN edad < 60 THEN '3. 45 a 59'
        ELSE                '4. 60 o más'
    END                                     AS rango_edad,
    COUNT(*)                                AS clientes,
    ROUND(100.0 * AVG(impago_2_anios), 2)   AS tasa_impago_pct
FROM clientes
GROUP BY rango_edad
ORDER BY rango_edad;

-- name: impago_por_quintil_ingreso
-- Función de ventana NTILE: divide a los clientes en 5 grupos según su ingreso.
WITH quintiles AS (
    SELECT
        ingreso_mensual,
        impago_2_anios,
        NTILE(5) OVER (ORDER BY ingreso_mensual) AS quintil
    FROM clientes
    WHERE ingreso_imputado = 0
)
SELECT
    quintil,
    ROUND(MIN(ingreso_mensual), 0)          AS ingreso_min,
    ROUND(MAX(ingreso_mensual), 0)          AS ingreso_max,
    COUNT(*)                                AS clientes,
    ROUND(100.0 * AVG(impago_2_anios), 2)   AS tasa_impago_pct
FROM quintiles
GROUP BY quintil
ORDER BY quintil;

-- name: impago_por_historial_mora
-- ¿Haber tenido moras antes predice el impago futuro?
SELECT
    CASE
        WHEN mora_30_59_dias + mora_60_89_dias + mora_90_dias = 0 THEN '0 moras'
        WHEN mora_30_59_dias + mora_60_89_dias + mora_90_dias <= 2 THEN '1 a 2 moras'
        ELSE '3 o más moras'
    END                                     AS historial,
    COUNT(*)                                AS clientes,
    ROUND(100.0 * AVG(impago_2_anios), 2)   AS tasa_impago_pct
FROM clientes
GROUP BY historial
ORDER BY tasa_impago_pct;

-- name: impago_por_utilizacion
-- Uso del cupo de tarjetas: ¿los clientes "al tope" son más riesgosos?
SELECT
    CASE
        WHEN utilizacion_credito < 0.3 THEN '1. Bajo (<30 %)'
        WHEN utilizacion_credito < 0.7 THEN '2. Medio (30-70 %)'
        WHEN utilizacion_credito <= 1  THEN '3. Alto (70-100 %)'
        ELSE                                '4. Sobregirado (>100 %)'
    END                                     AS nivel_utilizacion,
    COUNT(*)                                AS clientes,
    ROUND(100.0 * AVG(impago_2_anios), 2)   AS tasa_impago_pct
FROM clientes
GROUP BY nivel_utilizacion
ORDER BY nivel_utilizacion;

-- name: segmentos_alto_riesgo
-- Combinación de factores: los 10 segmentos (edad x mora) con mayor tasa de impago,
-- con al menos 100 clientes para que el resultado sea estadísticamente útil.
WITH segmentos AS (
    SELECT
        (edad / 10) * 10                    AS decada_edad,
        MIN(mora_90_dias, 3)                AS moras_90_tope,
        impago_2_anios
    FROM clientes
)
SELECT
    decada_edad || 's'                      AS edad,
    CASE WHEN moras_90_tope = 3 THEN '3+' ELSE CAST(moras_90_tope AS TEXT) END AS moras_90_dias,
    COUNT(*)                                AS clientes,
    ROUND(100.0 * AVG(impago_2_anios), 2)   AS tasa_impago_pct,
    RANK() OVER (ORDER BY AVG(impago_2_anios) DESC) AS ranking_riesgo
FROM segmentos
GROUP BY decada_edad, moras_90_tope
HAVING COUNT(*) >= 100
ORDER BY ranking_riesgo
LIMIT 10;
