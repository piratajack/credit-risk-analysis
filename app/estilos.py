"""Estilos CSS y encabezado animado del dashboard."""

import html

import streamlit.components.v1 as components

CSS = """
<style>
:root {
  --morado: #534AB7; --morado-osc: #3C3489; --verde: #1D9E75; --ambar: #EF9F27; --rojo: #D85A30;
  --tarjeta: rgba(127, 127, 127, 0.07); --borde: rgba(127, 127, 127, 0.22);
}
/* Sin barra lateral */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none; }
.block-container { padding-top: 1.2rem; max-width: 1180px; }

/* Botones */
.stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stLinkButton"] a {
  border-radius: 12px; font-weight: 600; padding: 0.55rem 1.2rem;
  transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover, [data-testid="stLinkButton"] a:hover {
  transform: translateY(-2px); box-shadow: 0 6px 18px rgba(83, 74, 183, .35);
}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--morado), #1D9E75); border: none; color: #fff;
  font-size: 1.05rem; padding: 0.75rem 1.4rem;
}

/* Pestañas más grandes y claras */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
  border-radius: 10px 10px 0 0; padding: 10px 18px; font-weight: 600; background: var(--tarjeta);
}

/* Tarjetas */
.tarjeta { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 16px; padding: 18px 20px; height: 100%; }
.paso { text-align: center; }
.paso .num { display: inline-flex; width: 42px; height: 42px; border-radius: 50%; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--morado), var(--verde)); color: #fff; font-weight: 700; font-size: 1.2rem; margin-bottom: 8px; }
.paso .ico { font-size: 2.4rem; }
.kpi { font-size: .85rem; opacity: .75; margin-bottom: 2px; }
.kpi-valor { font-size: 1.6rem; font-weight: 700; }

.banco { background: var(--tarjeta); border: 1px solid var(--borde); border-radius: 16px; padding: 18px 20px; margin-bottom: 14px;
  transition: transform .15s ease, box-shadow .15s ease; }
.banco:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(0, 0, 0, .12); }
.banco-top { display: flex; align-items: center; gap: 12px; }
.banco-logo { width: 44px; height: 44px; border-radius: 10px; background: #fff; padding: 6px; border: 1px solid var(--borde); }
.banco-nombre { font-size: 1.15rem; font-weight: 700; flex: 1; }
.badge { padding: 4px 12px; border-radius: 999px; font-size: .8rem; font-weight: 700; color: #fff; white-space: nowrap; }
.badge.Alta { background: var(--verde); } .badge.Media { background: var(--ambar); } .badge.Baja { background: var(--rojo); }
.banco-desc { font-size: .9rem; opacity: .8; margin: 10px 0 12px; min-height: 2.6em; }
.banco-datos { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
.banco-datos div span { display: block; font-size: .75rem; opacity: .7; }
.banco-datos div b { font-size: 1.05rem; }
.banco-nota { font-size: .75rem; opacity: .6; margin-bottom: 12px; }
.banco-link { display: inline-block; padding: 8px 16px; border-radius: 10px; font-weight: 600; text-decoration: none !important;
  color: #fff !important; background: linear-gradient(135deg, var(--morado), var(--morado-osc)); transition: opacity .15s; }
.banco-link:hover { opacity: .85; }

.tip { background: var(--tarjeta); border-left: 4px solid var(--morado); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; height: 100%; }
.tip .t { font-weight: 700; margin-bottom: 4px; }

@media (max-width: 640px) { .banco-datos { grid-template-columns: 1fr 1fr; } }
</style>
"""

_HERO = """
<!doctype html><html><head><meta charset="utf-8"><style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Source Sans Pro", system-ui, sans-serif; background: transparent; }
.hero { position: relative; overflow: hidden; border-radius: 22px; height: __ALTO__px; color: #fff;
  background: linear-gradient(120deg, #3C3489, #534AB7 45%, #0F6E56); background-size: 200% 200%;
  animation: fondo 12s ease infinite; padding: __PAD__; display: flex; flex-direction: column; justify-content: center; }
@keyframes fondo { 0%,100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }
.flota { position: absolute; bottom: -60px; font-weight: 700; opacity: .0; animation: subir linear infinite; pointer-events: none; }
@keyframes subir { 0% { transform: translateY(0) rotate(0); opacity: 0; } 10% { opacity: .35; }
  90% { opacity: .25; } 100% { transform: translateY(-__SUBIDA__px) rotate(25deg); opacity: 0; } }
h1 { font-size: __H1__; line-height: 1.1; position: relative; z-index: 2; }
p.sub { font-size: 1.05rem; opacity: .9; margin-top: 8px; max-width: 640px; position: relative; z-index: 2; }
.contadores { display: flex; gap: 34px; margin-top: 18px; position: relative; z-index: 2; flex-wrap: wrap; }
.contadores b { display: block; font-size: 1.9rem; font-variant-numeric: tabular-nums; }
.contadores span { font-size: .85rem; opacity: .85; }
.ticker { position: absolute; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,.22); white-space: nowrap; overflow: hidden;
  font-size: .9rem; padding: 7px 0; z-index: 3; }
.ticker div { display: inline-block; padding-left: 100%; animation: correr __VEL__s linear infinite; }
@keyframes correr { to { transform: translateX(-100%); } }
.ticker em { font-style: normal; color: #9FE1CB; font-weight: 700; margin: 0 22px 0 6px; }
</style></head><body>
<div class="hero" id="hero">
  <h1>__TITULO__</h1>
  <p class="sub">__SUBTITULO__</p>
  <div class="contadores">__CONTADORES__</div>
  <div class="ticker"><div>__TICKER__</div></div>
</div>
<script>
__SIN_TRADUCCION__
const simbolos = ["$", "%", "📈", "💳", "🏦", "💰", "28,5", "12%", "$", "📊", "✓", "24"];
const hero = document.getElementById("hero");
for (let i = 0; i < 22; i++) {
  const s = document.createElement("span");
  s.className = "flota";
  s.textContent = simbolos[i % simbolos.length];
  s.style.left = (Math.random() * 100) + "%";
  s.style.fontSize = (16 + Math.random() * 26) + "px";
  s.style.animationDuration = (7 + Math.random() * 9) + "s";
  s.style.animationDelay = (-Math.random() * 14) + "s";
  hero.appendChild(s);
}
document.querySelectorAll("[data-fin]").forEach(el => {
  const fin = parseFloat(el.dataset.fin), dec = parseInt(el.dataset.dec || "0"), suf = el.dataset.suf || "";
  const t0 = performance.now(), dur = 1800;
  const paso = (t) => {
    const p = Math.min((t - t0) / dur, 1), v = fin * (1 - Math.pow(1 - p, 3));
    el.textContent = v.toLocaleString("es-CO", {minimumFractionDigits: dec, maximumFractionDigits: dec}) + suf;
    if (p < 1) requestAnimationFrame(paso);
  };
  requestAnimationFrame(paso);
});
</script></body></html>
"""


# Streamlit declara la página en inglés, así que Chrome ofrece traducirla. El traductor modifica
# el DOM que maneja React y provoca errores como "removeChild". Se marca la página como español
# y no traducible.
_SIN_TRADUCCION = """
try {
const d = window.parent.document;
d.documentElement.lang = "es";
d.documentElement.setAttribute("translate", "no");
d.documentElement.classList.add("notranslate");
d.body.setAttribute("translate", "no");
if (!d.querySelector('meta[name="google"]')) {
  const m = d.createElement("meta");
  m.name = "google"; m.content = "notranslate";
  d.head.appendChild(m);
}
} catch (e) {}
"""


def aplicar_css() -> None:
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def encabezado(titulo: str, subtitulo: str, contadores: list[tuple[float, int, str, str]],
               ticker: list[tuple[str, float]], grande: bool = True) -> None:
    """Encabezado con fondo animado, símbolos flotantes, contadores y cinta de tasas.

    contadores: (valor final, decimales, sufijo, etiqueta). ticker: (banco, tasa %).
    """
    alto = 330 if grande else 190
    cont = "".join(
        f'<div><b data-fin="{v}" data-dec="{d}" data-suf="{html.escape(s)}">0</b><span>{html.escape(e)}</span></div>'
        for v, d, s, e in contadores)
    cinta = "".join(f"{html.escape(b)}<em>{t:.2f} %</em>".replace(".", ",") for b, t in ticker)
    pagina = (_HERO.replace("__ALTO__", str(alto)).replace("__SUBIDA__", str(alto + 120))
              .replace("__PAD__", "34px 40px 50px" if grande else "20px 30px 44px")
              .replace("__H1__", "2.6rem" if grande else "1.7rem")
              .replace("__TITULO__", html.escape(titulo)).replace("__SUBTITULO__", html.escape(subtitulo))
              .replace("__CONTADORES__", cont if grande else "").replace("__TICKER__", cinta * 2)
              .replace("__VEL__", str(max(25, 3 * len(ticker))))
              .replace("__SIN_TRADUCCION__", _SIN_TRADUCCION))
    components.html(pagina, height=alto + 6)


def tarjeta_banco(fila, pesos, porcentaje) -> str:
    """HTML de la tarjeta de un banco en los resultados."""
    logo = (f'<img class="banco-logo" src="https://www.google.com/s2/favicons?domain={fila["dominio"]}&sz=64" alt="">'
            if fila["dominio"] else '<div class="banco-logo">🏦</div>')
    enlace = (f'<a class="banco-link" href="https://www.{fila["dominio"]}" target="_blank" rel="noopener noreferrer">'
              f'Ir a {html.escape(fila["banco"])} ↗</a>' if fila["dominio"] else "")
    nota = (f'Tasa promedio del banco: {porcentaje(fila["tasa_promedio"])} '
            f'(rango {porcentaje(fila["tasa_min"])} a {porcentaje(fila["tasa_max"])}) · '
            f'{pesos(fila["creditos_mes"])[1:]} créditos desembolsados en el último mes')
    if not fila["dato_del_plazo"]:
        nota += " · sin datos para ese plazo, se usa el promedio del banco"
    return f"""
<div class="banco">
  <div class="banco-top">{logo}<div class="banco-nombre">{html.escape(fila["banco"])}</div>
    <span class="badge {fila["aprobacion"]}">Aprobación {fila["aprobacion"].lower()}</span></div>
  <div class="banco-desc">{html.escape(fila["descripcion"])}</div>
  <div class="banco-datos">
    <div><span>Tasa estimada (E.A.)</span><b>{porcentaje(fila["tasa_estimada"], 2)}</b></div>
    <div><span>Cuota mensual</span><b>{pesos(fila["cuota"])}</b></div>
    <div><span>Total a pagar</span><b>{pesos(fila["total_pagar"])}</b></div>
  </div>
  <div class="banco-nota">{nota}</div>
  {enlace}
</div>"""

