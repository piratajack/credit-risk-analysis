"""Buscador de créditos: compara tasas reales de bancos colombianos según el perfil de riesgo del usuario.

Uso:
    streamlit run app/dashboard.py
"""

import html
import json
import os
import re
import sys
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "app"))
import auth  # noqa: E402
from bancos import (DESCRIPCION_PRODUCTO, PRODUCTOS, Perfil, buscar_bancos, capacidad_pago,  # noqa: E402
                    pesos, porcentaje, sugerencias)
from estilos import aplicar_css, encabezado, tarjeta_banco  # noqa: E402
from features import crear_features, segmentar  # noqa: E402

APP_DATA = ROOT / "app_data"
POLITICA = (ROOT / "app" / "politica_privacidad.md").read_text(encoding="utf-8")
COLORES = {"1. Bajo": "#1D9E75", "2. Medio": "#EF9F27", "3. Alto": "#D85A30", "4. Muy alto": "#A32D2D"}
COLORES_APROBACION = {"Alta": "#1D9E75", "Media": "#EF9F27", "Baja": "#D85A30"}

st.set_page_config(page_title="Encuentra tu crédito", page_icon="🏦", layout="wide")
aplicar_css()

# En Streamlit Cloud la conexión a la base de usuarios llega como secreto
try:
    if "DATABASE_URL" in st.secrets:
        os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
except Exception:  # en local no hay secrets.toml: se usa SQLite
    pass


# ---------- Datos ----------
@st.cache_data
def cargar_tasas() -> tuple[pd.DataFrame, float, str, str]:
    tasas = pd.read_csv(APP_DATA / "tasas_bancos.csv")
    usura = pd.read_csv(APP_DATA / "tasa_usura.csv")
    usura = usura[usura["modalidad"] == "CONSUMO Y ORDINARIO"].iloc[0]
    vigencia = f"{usura['vigencia_desde']} a {usura['vigencia_hasta']}"
    return tasas, float(usura["usura"]), vigencia, tasas["periodo"].iloc[0]


@st.cache_data
def cargar_resumen() -> dict:
    return json.loads((APP_DATA / "resumen_cartera.json").read_text(encoding="utf-8"))


@st.cache_resource
def cargar_modelo() -> dict:
    return joblib.load(APP_DATA / "modelo_impago.joblib")


if not (APP_DATA / "resumen_cartera.json").exists():
    st.error("Faltan los datos de la app. Ejecuta el pipeline y luego `python src/export_app_data.py`.")
    st.stop()

tasas, usura, vigencia_usura, periodo_tasas = cargar_tasas()
resumen = cargar_resumen()
artefacto = cargar_modelo()


def ticker() -> list[tuple[str, float]]:
    from bancos import CATALOGO, MIN_CREDITOS
    libre = tasas[tasas["producto"] == "Libre inversión"]
    resumen = libre.groupby("codigo_entidad").apply(
        lambda g: pd.Series({"tasa": (g["tasa"] * g["monto"]).sum() / g["monto"].sum(), "creditos": g["creditos"].sum()}),
        include_groups=False)
    resumen = resumen[resumen["creditos"] >= MIN_CREDITOS].sort_values("tasa")
    return [(CATALOGO.get(c, (str(c),))[0], t) for c, t in resumen["tasa"].items()]


def md_a_html(texto: str) -> str:
    """Convierte **negrita** y [enlaces](url) de las sugerencias a HTML seguro."""
    texto = html.escape(texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    return re.sub(r"\[(.+?)\]\((https://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', texto)


# ---------- Inicio: presentación + login ----------
def pantalla_inicio() -> None:
    encabezado(
        "Encuentra el crédito que se ajusta a ti",
        "Compara tasas reales de los bancos de Colombia según tu perfil, con datos oficiales "
        "de la Superintendencia Financiera.",
        [(tasas["codigo_entidad"].nunique(), 0, "", "bancos comparados"),
         (len(PRODUCTOS), 0, "", "tipos de crédito"),
         (int(tasas["creditos"].sum()), 0, "", "operaciones de crédito analizadas"),
         (usura, 2, " %", "tasa de usura vigente")],
        ticker(),
    )
    st.write("")
    izq, der = st.columns([1.35, 1], gap="large")
    with izq:
        st.markdown("### ¿Cómo funciona?")
        pasos = [("📝", "Cuéntanos de ti", "Tus ingresos, tus deudas y el crédito que buscas. Toma 2 minutos."),
                 ("🤖", "Calculamos tu perfil", "Un modelo de Machine Learning estima tu nivel de riesgo y tu capacidad de pago."),
                 ("🏦", "Compara bancos", "Ves la tasa, la cuota y el total a pagar en cada banco, con el enlace para solicitarlo.")]
        cols = st.columns(3)
        for i, (col, (ico, titulo, texto)) in enumerate(zip(cols, pasos), start=1):
            col.markdown(f'<div class="tarjeta paso"><div class="num">{i}</div><div class="ico">{ico}</div>'
                         f'<h4>{titulo}</h4><p style="opacity:.8;font-size:.92rem">{texto}</p></div>',
                         unsafe_allow_html=True)
        st.write("")
        st.markdown("##### Créditos que puedes comparar")
        st.markdown(" ".join(f"`{v[0]} {k}`" for k, v in PRODUCTOS.items()))
    with der:
        with st.container(border=True):
            entrar, registro = st.tabs(["🔑 Iniciar sesión", "✨ Crear cuenta"])
            with entrar:
                with st.form("login"):
                    email = st.text_input("Correo electrónico", placeholder="tu@correo.com")
                    password = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                        usuario, error = auth.iniciar_sesion(email, password)
                        if usuario:
                            st.session_state["usuario"] = usuario
                            st.rerun()
                        st.error(error)
            with registro:
                with st.form("registro"):
                    nombre = st.text_input("Nombre", placeholder="¿Cómo te llamas?")
                    email_r = st.text_input("Correo electrónico", placeholder="tu@correo.com", key="email_r")
                    pass_r = st.text_input("Contraseña", type="password", key="pass_r",
                                           help="Mínimo 8 caracteres, con letras y números")
                    pass_r2 = st.text_input("Repite la contraseña", type="password")
                    acepta = st.checkbox("Autorizo el tratamiento de mis datos según la política de privacidad "
                                         "(Ley 1581 de 2012)")
                    if st.form_submit_button("Crear mi cuenta", type="primary", use_container_width=True):
                        if pass_r != pass_r2:
                            st.error("Las contraseñas no coinciden.")
                        elif error := auth.registrar(nombre, email_r, pass_r, acepta):
                            st.error(error)
                        else:
                            st.session_state["usuario"], _ = auth.iniciar_sesion(email_r, pass_r)
                            st.rerun()
                with st.expander("📄 Leer la política de privacidad"):
                    st.markdown(POLITICA)
            st.caption("🔒 Tu contraseña se guarda cifrada. No pedimos cédula ni datos bancarios.")


if "usuario" not in st.session_state:
    pantalla_inicio()
    st.stop()

usuario = st.session_state["usuario"]


# ---------- App ----------
def perfil_riesgo(perfil: Perfil) -> tuple[float, str]:
    """Probabilidad de impago con el modelo. El ingreso se fija en la mediana de la cartera porque
    el modelo se entrenó con datos en dólares; el ingreso en pesos se evalúa en la capacidad de pago."""
    cliente = pd.DataFrame([{
        "utilizacion_credito": perfil.uso_tarjetas, "edad": perfil.edad,
        "mora_30_59_dias": perfil.mora_30, "mora_60_89_dias": perfil.mora_60, "mora_90_dias": perfil.mora_90,
        "ratio_deuda": perfil.pagos_deudas / perfil.ingreso if perfil.ingreso else 1.0,
        "ingreso_mensual": resumen["ingreso_mediana"], "ingreso_imputado": 0,
        "lineas_credito_abiertas": perfil.creditos_abiertos, "creditos_hipotecarios": perfil.creditos_vivienda,
        "dependientes": perfil.dependientes,
    }])
    prob = float(artefacto["modelo"].predict_proba(crear_features(cliente))[:, 1][0])
    return prob, segmentar(pd.Series([prob]))[0]


cab, salir = st.columns([8, 1.6])
with cab:
    encabezado(f"Hola, {usuario['nombre'].split()[0]} 👋", "Compara créditos con tasas oficiales actualizadas.",
               [], ticker(), grande=False)
with salir:
    st.write("")
    st.write("")
    if st.button("↩ Cerrar sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

tab_buscar, tab_historial, tab_como = st.tabs(["🏦 Buscar crédito", "🕘 Mis búsquedas", "🤖 Cómo funciona"])

with tab_buscar:
    st.markdown("#### 1. ¿Qué crédito necesitas?")
    opciones = {f"{v[0]} {k}": k for k, v in PRODUCTOS.items()}
    eleccion = st.pills("Tipo de crédito", list(opciones), default=list(opciones)[0], label_visibility="collapsed")
    producto = opciones[eleccion or list(opciones)[0]]
    _, plazo_min, plazo_max, plazo_def, monto_def, _ = PRODUCTOS[producto]
    st.caption(DESCRIPCION_PRODUCTO[producto])

    with st.form("perfil"):
        a, b = st.columns(2)
        monto = a.number_input("💵 ¿Cuánto dinero necesitas? (COP)", 500_000, 2_000_000_000, monto_def, step=500_000,
                               format="%d", key=f"monto_{producto}")
        meses = b.slider("📅 ¿En cuántos meses quieres pagarlo?", plazo_min, plazo_max, plazo_def, key=f"plazo_{producto}")

        st.markdown("#### 2. Cuéntanos de ti")
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1.container(border=True):
            st.markdown("**👤 Sobre ti**")
            edad = st.number_input("Edad", 18, 100, 30)
            situacion = st.selectbox("Situación laboral", ["Empleado", "Independiente", "Pensionado"])
            dependientes = st.number_input("Personas que dependen de ti", 0, 15, 0)
        with c2.container(border=True):
            st.markdown("**💰 Tus finanzas**")
            ingreso = st.number_input("Ingreso mensual (COP)", 0, 500_000_000, 3_500_000, step=100_000, format="%d")
            pagos = st.number_input("¿Cuánto pagas al mes en otras deudas? (COP)", 0, 500_000_000, 0, step=50_000,
                                    format="%d", help="Suma de cuotas de créditos y tarjetas que ya tienes")
            abiertos = st.number_input("Créditos y tarjetas que tienes abiertos", 0, 60, 2)
            vivienda = st.number_input("Créditos de vivienda que tienes", 0, 10, 0)
        with c3.container(border=True):
            st.markdown("**📋 Tu historial**")
            uso = st.slider("¿Qué porcentaje del cupo de tus tarjetas usas?", 0, 150, 30, 5, format="%d %%",
                            help="Si tu cupo es $1.000.000 y debes $300.000, usas el 30 %. Pon 0 si no tienes tarjetas.")
            st.caption("En los últimos 2 años, ¿cuántas veces te atrasaste en un pago?")
            m30 = st.number_input("Entre 30 y 59 días", 0, 30, 0)
            m60 = st.number_input("Entre 60 y 89 días", 0, 30, 0)
            m90 = st.number_input("90 días o más", 0, 30, 0)
        buscar = st.form_submit_button("🔍  Buscar mis bancos", type="primary", use_container_width=True)

    if buscar:
        if ingreso <= 0:
            st.error("Escribe tu ingreso mensual para calcular tu capacidad de pago.")
        else:
            perfil = Perfil(edad, situacion, ingreso, pagos, dependientes, abiertos, vivienda, uso / 100, m30, m60, m90)
            prob, segmento = perfil_riesgo(perfil)
            res = buscar_bancos(tasas, perfil, segmento, producto, monto, meses, usura)
            st.session_state["resultado"] = dict(perfil=perfil, prob=prob, segmento=segmento, producto=producto,
                                                 monto=monto, meses=meses, res=res)
            mejor = res.iloc[0] if not res.empty else None
            auth.guardar_busqueda(usuario["id"], {
                "producto": producto, "monto": monto, "meses": meses, "riesgo": segmento.split(". ")[1],
                "prob_impago": round(prob, 4), "bancos_que_se_ajustan": int(res["se_ajusta"].sum()) if not res.empty else 0,
                "mejor_banco": mejor["banco"] if mejor is not None else None,
                "cuota": round(float(mejor["cuota"])) if mejor is not None else None,
            })

    r = st.session_state.get("resultado")
    if r:
        perfil, res, segmento = r["perfil"], r["res"], r["segmento"]
        capacidad = capacidad_pago(perfil, r["producto"])
        st.divider()
        st.markdown(f"#### 3. Tus resultados · {PRODUCTOS[r['producto']][0]} {r['producto']} de "
                    f"{pesos(r['monto'])} a {r['meses']} meses")
        nivel = segmento.split(". ")[1]
        ajustan = int(res["se_ajusta"].sum()) if not res.empty else 0
        kpis = [("Tu nivel de riesgo", f'<span style="color:{COLORES[segmento]}">● {nivel}</span>',
                 f"Probabilidad estimada de impago: {r['prob']:.1%}".replace(".", ",")),
                ("Cuota máxima recomendada", pesos(capacidad), "40 % de tu ingreso menos tus deudas actuales"),
                ("Cuota en la mejor opción", pesos(res.iloc[0]["cuota"]) if not res.empty else "—",
                 res.iloc[0]["banco"] if not res.empty else ""),
                ("Bancos que se ajustan", f"{ajustan} de {len(res)}", "con aprobación alta o media")]
        for col, (titulo, valor, nota) in zip(st.columns(4), kpis):
            col.markdown(f'<div class="tarjeta"><div class="kpi">{titulo}</div><div class="kpi-valor">{valor}</div>'
                         f'<div class="kpi" style="margin-top:4px">{html.escape(nota)}</div></div>', unsafe_allow_html=True)

        tips = sugerencias(perfil, segmento, r["producto"], r["monto"], r["meses"], res, tasas)
        if tips:
            st.markdown("#### 💡 Sugerencias para ti")
            cols = st.columns(2)
            for i, (ico, titulo, texto) in enumerate(tips):
                cols[i % 2].markdown(f'<div class="tip"><div class="t">{ico} {html.escape(titulo)}</div>'
                                     f'{md_a_html(texto)}</div>', unsafe_allow_html=True)

        if res.empty:
            st.warning("No hay bancos con datos suficientes para este tipo de crédito.")
        else:
            st.markdown("#### 🏦 Bancos para ti")
            ver_todos = st.toggle("Mostrar también los bancos donde la cuota supera tu capacidad", value=ajustan == 0)
            visibles = res if ver_todos else res[res["se_ajusta"]]
            if visibles.empty:
                st.info("Ningún banco se ajusta a tu capacidad con este monto y plazo. Revisa las sugerencias "
                        "o activa la opción de arriba para ver todos los bancos.")
            cols = st.columns(2)
            for i, (_, fila) in enumerate(visibles.iterrows()):
                cols[i % 2].markdown(tarjeta_banco(fila, pesos, porcentaje), unsafe_allow_html=True)

            graf = res.sort_values("total_pagar", ascending=False)
            fig = px.bar(graf, x="total_pagar", y="banco", orientation="h", color="aprobacion",
                         color_discrete_map=COLORES_APROBACION, title="¿Cuánto pagarías en total en cada banco?",
                         labels={"total_pagar": "Total a pagar (COP)", "banco": "", "aprobacion": "Aprobación"},
                         hover_data={"tasa_estimada": ":.2f", "cuota": ":,.0f"})
            fig.add_vline(x=r["monto"], line_dash="dot", annotation_text="Monto pedido")
            st.plotly_chart(fig.update_layout(height=max(320, 32 * len(graf))), use_container_width=True)

        st.caption(f"Tasas: Superintendencia Financiera de Colombia (Formato 088, datos.gov.co), créditos desembolsados "
                   f"a personas entre {periodo_tasas}. Tasa de usura de consumo vigente ({vigencia_usura}): "
                   f"{porcentaje(usura, 2)} E.A. La tasa, la cuota y la probabilidad de aprobación son estimaciones "
                   "educativas, no una oferta ni asesoría financiera; cada banco decide con su propio estudio de crédito.")

with tab_historial:
    busquedas = auth.historial(usuario["id"])
    if not busquedas:
        st.info("Todavía no has hecho búsquedas. Ve a **🏦 Buscar crédito** para empezar.")
    else:
        hist = pd.DataFrame(busquedas)
        hist["fecha"] = hist["fecha"].str.replace("T", " ")
        st.dataframe(hist, hide_index=True, use_container_width=True, column_config={
            "fecha": "Fecha", "producto": "Crédito", "monto": st.column_config.NumberColumn("Monto", format="$%,d"),
            "meses": "Meses", "riesgo": "Riesgo", "prob_impago": st.column_config.NumberColumn("Prob. impago", format="percent"),
            "bancos_que_se_ajustan": "Bancos que se ajustan", "mejor_banco": "Mejor opción",
            "cuota": st.column_config.NumberColumn("Cuota", format="$%,d")})

    st.divider()
    with st.expander("⚙️ Mi cuenta y mis datos"):
        st.write(f"**Nombre:** {usuario['nombre']}  \n**Correo:** {usuario['email']}")
        st.markdown("Puedes borrar tu cuenta cuando quieras. Se eliminan tu nombre, tu correo y todo tu historial, "
                    "y no se puede deshacer.")
        confirmar = st.checkbox("Entiendo que esto borra mi cuenta para siempre")
        if st.button("🗑️ Eliminar mi cuenta", disabled=not confirmar):
            auth.eliminar_cuenta(usuario["id"])
            st.session_state.clear()
            st.rerun()
        st.markdown("---")
        st.markdown(POLITICA)

with tab_como:
    metricas = artefacto["metricas"]
    st.markdown("#### Cómo calculamos tus resultados")
    pasos = [("🤖", "Nivel de riesgo", f"Un modelo de {metricas['modelo'].lower()} entrenado con {pesos(resumen['clientes'])[1:]} clientes "
              "estima tu probabilidad de impago a partir de tu historial de pagos, el uso de tus tarjetas y tus deudas."),
             ("📏", "Capacidad de pago", "Tus deudas no deberían superar el 40 % de tu ingreso (30 % en vivienda). "
              "Con eso calculamos la cuota máxima que puedes asumir."),
             ("🏦", "Tasa por banco", "Usamos las tasas reales que cada banco reportó a la Superintendencia Financiera "
              "y te ubicamos dentro de su rango según tu nivel de riesgo, sin superar la tasa de usura.")]
    for col, (ico, t, texto) in zip(st.columns(3), pasos):
        col.markdown(f'<div class="tarjeta"><div style="font-size:2rem">{ico}</div><h4>{t}</h4>'
                     f'<p style="opacity:.8">{texto}</p></div>', unsafe_allow_html=True)

    st.markdown("#### Calidad del modelo")
    for col, (t, v) in zip(st.columns(4), [("AUC", metricas["auc"]), ("Gini", metricas["gini"]),
                                           ("KS", metricas["ks"]), ("Brier", metricas["brier"])]):
        col.metric(t, f"{v:.3f}")
    izq, der = st.columns(2)
    deciles = pd.read_csv(APP_DATA / "deciles.csv")
    calib = deciles.melt(id_vars="decil", value_vars=["prob_promedio", "tasa_impago_real"], var_name="serie", value_name="tasa")
    calib["serie"] = calib["serie"].map({"prob_promedio": "Predicha", "tasa_impago_real": "Real"})
    izq.plotly_chart(px.line(calib, x="decil", y="tasa", color="serie", markers=True, title="Calibración por decil",
                             labels={"decil": "Decil de riesgo (10 = más riesgo)", "tasa": "Tasa de impago", "serie": ""})
                     .update_layout(yaxis_tickformat=".0%"), use_container_width=True)
    importancia = pd.read_csv(APP_DATA / "importancia_variables.csv").sort_values("importancia")
    der.plotly_chart(px.bar(importancia, x="importancia", y="variable", orientation="h", title="Qué pesa más en el riesgo",
                            labels={"importancia": "Caída de AUC al permutar", "variable": ""},
                            color_discrete_sequence=["#534AB7"]), use_container_width=True)

    seg = pd.DataFrame(list(resumen["segmentos"].items()), columns=["segmento_riesgo", "count"])
    st.plotly_chart(px.bar(seg, x="segmento_riesgo", y="count", color="segmento_riesgo", color_discrete_map=COLORES,
                           text_auto=True, title="Clientes de entrenamiento por nivel de riesgo",
                           labels={"segmento_riesgo": "", "count": "Clientes"}).update_layout(showlegend=False),
                    use_container_width=True)
    st.info(f"⚠️ El modelo se entrenó con {resumen['fuente_texto']}. Por eso tu ingreso en pesos no entra al "
            "modelo: se usa solo para calcular tu capacidad de pago.")
