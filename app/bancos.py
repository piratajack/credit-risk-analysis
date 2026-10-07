"""Catálogo de bancos, cálculos de crédito y sugerencias para el buscador de créditos."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

# codigo_entidad (Superfinanciera) -> datos de presentación. Los dominios se verificaron a mano.
CATALOGO = {
    7: ("Bancolombia", "bancolombia.com", "El banco más grande de Colombia, con la red de oficinas y cajeros más amplia del país."),
    39: ("Davivienda", "davivienda.com", "Uno de los bancos más grandes del país, fuerte en crédito de vivienda y banca digital (DaviPlata)."),
    42: ("Davibank", "davibank.com", "Antes Scotiabank Colpatria. Hoy hace parte del Grupo Bolívar, junto con Davivienda."),
    1: ("Banco de Bogotá", "bancodebogota.com", "El banco más antiguo del país y cabeza del Grupo Aval."),
    56: ("Banco Falabella", "bancofalabella.com.co", "Banco del grupo Falabella, conocido por su tarjeta CMR y beneficios en sus tiendas."),
    13: ("BBVA Colombia", "bbva.com.co", "Filial del grupo español BBVA, con buena oferta digital para créditos de consumo."),
    23: ("Banco de Occidente", "bancodeoccidente.com.co", "Banco del Grupo Aval, con presencia fuerte en el occidente del país y en crédito de vehículo."),
    49: ("Banco AV Villas", "avvillas.com.co", "Banco del Grupo Aval, enfocado en personas y crédito de vivienda."),
    30: ("Banco Caja Social", "bancocajasocial.com", "Banco de la Fundación Social, enfocado en familias y trabajadores independientes."),
    63: ("Banco Serfinanza", "bancoserfinanza.com", "Banco de la Organización Olímpica, con tarjetas y créditos de consumo."),
    2: ("Banco Popular", "bancopopular.com.co", "Banco del Grupo Aval, líder en créditos de libranza para empleados y pensionados."),
    65: ("Lulo Bank", "lulobank.com", "Banco 100 % digital: todo el proceso se hace desde la app."),
    55: ("Banco Finandina", "bancofinandina.com", "Banco especializado en crédito de vehículo y crédito de consumo digital."),
    54: ("Bancoomeva", "bancoomeva.com.co", "Banco del grupo cooperativo Coomeva, con beneficios para sus asociados."),
    12: ("Banco GNB Sudameris", "gnbsudameris.com.co", "Banco con fuerte presencia en libranza para empleados públicos y pensionados."),
    43: ("Banco Agrario", "bancoagrario.gov.co", "Banco del Estado, con presencia en zonas rurales y apoyo al sector agropecuario."),
    51: ("Bancien", "ban100.com.co", "Banco antes conocido como Ban100, con créditos de libranza y tarjetas."),
    53: ("Banco W", "bancow.com.co", "Banco enfocado en microempresarios y personas con poco historial de crédito."),
    60: ("Banco Mundo Mujer", "bmm.com.co", "Banco de microfinanzas para emprendedores y personas sin historial crediticio."),
    6: ("Itaú", "itau.co", "Filial del banco brasileño Itaú, el más grande de América Latina."),
    58: ("Banco Coopcentral", "coopcentral.com.co", "Banco cooperativo que atiende a asociados de cooperativas en todo el país."),
    67: ("Banco Unión", "bancounion.com", "Banco conocido por el envío y pago de giros, con créditos de consumo."),
    59: ("Banco Santander", "santander.com.co", "Filial del grupo español Santander, enfocada en crédito de vehículo y empresas."),
    57: ("Banco Pichincha", "bancopichincha.com.co", "Filial del banco ecuatoriano Pichincha, activo en libranza y consumo."),
    62: ("Mibanco", "mibanco.com.co", "Banco de microfinanzas para emprendedores y pequeños negocios."),
}

PRODUCTOS = {
    # producto: (ícono, plazo mínimo, plazo máximo, plazo por defecto, monto por defecto, es_consumo)
    "Libre inversión": ("💰", 6, 84, 36, 10_000_000, True),
    "Libranza": ("🧾", 12, 144, 60, 15_000_000, True),
    "Vehículo": ("🚗", 12, 84, 60, 60_000_000, True),
    "Vivienda": ("🏠", 60, 360, 180, 200_000_000, False),
    "Vivienda VIS": ("🏡", 60, 360, 240, 120_000_000, False),
    "Tarjeta de crédito": ("💳", 1, 36, 12, 3_000_000, True),
}
DESCRIPCION_PRODUCTO = {
    "Libre inversión": "Dinero para lo que necesites, sin justificar en qué lo usas.",
    "Libranza": "Se descuenta de tu nómina o pensión. Suele tener la tasa más baja de consumo.",
    "Vehículo": "Para comprar carro o moto. El vehículo queda como garantía.",
    "Vivienda": "Para comprar vivienda que no es de interés social (No VIS).",
    "Vivienda VIS": "Para vivienda de interés social, con tasas más bajas.",
    "Tarjeta de crédito": "Cupo rotativo para compras. Tasa calculada a 12 cuotas por defecto.",
}

SEGMENTO_POSICION = {"1. Bajo": "bajo", "2. Medio": "medio", "3. Alto": "alto", "4. Muy alto": "muy_alto"}
MIN_CREDITOS = 30  # bancos con menos créditos reportados no tienen una tasa confiable


@dataclass
class Perfil:
    edad: int
    situacion: str          # Empleado, Pensionado o Independiente
    ingreso: float          # COP mensuales
    pagos_deudas: float     # COP mensuales que ya paga en otras deudas
    dependientes: int
    creditos_abiertos: int
    creditos_vivienda: int
    uso_tarjetas: float     # 0 a 1.5
    mora_30: int
    mora_60: int
    mora_90: int

    @property
    def total_moras(self) -> int:
        return self.mora_30 + self.mora_60 + self.mora_90


def tasa_mensual(tea_pct: float) -> float:
    return (1 + tea_pct / 100) ** (1 / 12) - 1


def cuota(monto: float, tea_pct: float, meses: int) -> float:
    """Cuota fija mensual (sistema francés)."""
    i = tasa_mensual(tea_pct)
    return monto / meses if i == 0 else monto * i / (1 - (1 + i) ** -meses)


def monto_maximo(cuota_max: float, tea_pct: float, meses: int) -> float:
    """Monto que se puede pedir pagando como máximo `cuota_max` al mes."""
    i = tasa_mensual(tea_pct)
    return cuota_max * meses if i == 0 else cuota_max * (1 - (1 + i) ** -meses) / i


def plazo_categoria(meses: int) -> str:
    """Convierte meses a la categoría de plazo del Formato 088."""
    for limite, etiqueta in [(12, "Entre 31 días y 1 año"), (36, "Más de 1 año y hasta 3 años"),
                             (60, "Más de 3 años y hasta 5 años"), (84, "Más de 5 años y hasta 7 años"),
                             (120, "Más de 7 años y hasta 10 años")]:
        if meses <= limite:
            return etiqueta
    return "Más de 10 años"


def capacidad_pago(perfil: Perfil, producto: str) -> float:
    """Cuota máxima recomendada. Las deudas no deberían pasar del 40 % del ingreso;
    en vivienda la cuota tampoco debería superar el 30 % del ingreso."""
    libre = 0.40 * perfil.ingreso - perfil.pagos_deudas
    if producto.startswith("Vivienda"):
        libre = min(libre, 0.30 * perfil.ingreso)
    return max(libre, 0.0)


def tasa_estimada(promedio: float, minima: float, maxima: float, segmento: str) -> float:
    """Ubica al cliente dentro del rango de tasas del banco según su riesgo."""
    minima = max(minima, 0.6 * promedio)  # descarta tasas atípicas (p. ej. créditos a empleados)
    posicion = SEGMENTO_POSICION.get(segmento, "medio")
    return {
        "bajo": promedio - 0.35 * (promedio - minima),
        "medio": promedio,
        "alto": promedio + 0.5 * (maxima - promedio),
        "muy_alto": maxima,
    }[posicion]


def _ponderada(g: pd.DataFrame) -> pd.Series:
    return pd.Series({
        "tasa": np.average(g["tasa"], weights=g["monto"]),
        "tasa_min": g["tasa_min"].min(),
        "tasa_max": g["tasa_max"].max(),
        "creditos": g["creditos"].sum(),
    })


def buscar_bancos(tasas: pd.DataFrame, perfil: Perfil, segmento: str, producto: str,
                  monto: float, meses: int, usura: float) -> pd.DataFrame:
    """Calcula tasa, cuota y probabilidad de aprobación en cada banco que ofrece el producto."""
    datos = tasas[tasas["producto"] == producto]
    if datos.empty:
        return pd.DataFrame()
    general = datos.groupby("codigo_entidad")[["tasa", "monto", "tasa_min", "tasa_max", "creditos"]] \
                   .apply(_ponderada)
    general = general[general["creditos"] >= MIN_CREDITOS]
    en_plazo = datos[(datos["plazo"] == plazo_categoria(meses)) & (datos["creditos"] >= 5)] \
        .set_index("codigo_entidad")

    capacidad = capacidad_pago(perfil, producto)
    es_consumo = PRODUCTOS[producto][5]
    filas = []
    for codigo, g in general.iterrows():
        usa_plazo = codigo in en_plazo.index
        base = en_plazo.loc[codigo] if usa_plazo else g
        tasa = tasa_estimada(base["tasa"], base["tasa_min"], base["tasa_max"], segmento)
        if es_consumo:
            tasa = min(tasa, usura)
        valor_cuota = cuota(monto, tasa, meses)
        relacion = valor_cuota / capacidad if capacidad else np.inf
        riesgo_ok = segmento in ("1. Bajo", "2. Medio")
        if relacion <= 1 and riesgo_ok:
            aprobacion = "Alta"
        elif (relacion <= 1 and segmento == "3. Alto") or (relacion <= 1.15 and riesgo_ok):
            aprobacion = "Media"
        else:
            aprobacion = "Baja"
        nombre, dominio, descripcion = CATALOGO.get(
            int(codigo), (str(codigo), None, "Establecimiento bancario vigilado por la Superintendencia Financiera."))
        filas.append({
            "codigo": int(codigo), "banco": nombre, "dominio": dominio, "descripcion": descripcion,
            "tasa_estimada": round(tasa, 2), "tasa_promedio": round(base["tasa"], 2),
            "tasa_min": round(base["tasa_min"], 2), "tasa_max": round(base["tasa_max"], 2),
            "creditos_mes": int(g["creditos"]), "dato_del_plazo": usa_plazo,
            "cuota": valor_cuota, "total_pagar": valor_cuota * meses,
            "monto_maximo": monto_maximo(capacidad, tasa, meses),
            "aprobacion": aprobacion, "se_ajusta": aprobacion != "Baja",
        })
    orden = {"Alta": 0, "Media": 1, "Baja": 2}
    return (pd.DataFrame(filas)
            .assign(_o=lambda d: d["aprobacion"].map(orden))
            .sort_values(["_o", "cuota"]).drop(columns="_o").reset_index(drop=True))


def pesos(valor: float) -> str:
    return "$" + f"{valor:,.0f}".replace(",", ".")


def porcentaje(valor: float, decimales: int = 1) -> str:
    """Porcentaje con coma decimal, como se escribe en Colombia: 18,25 %."""
    return f"{valor:.{decimales}f}".replace(".", ",") + " %"


def sugerencias(perfil: Perfil, segmento: str, producto: str, monto: float, meses: int,
                resultados: pd.DataFrame, tasas: pd.DataFrame) -> list[tuple[str, str, str]]:
    """Devuelve (ícono, título, texto) con consejos según el perfil y los resultados."""
    tips = []
    capacidad = capacidad_pago(perfil, producto)
    plazo_max = PRODUCTOS[producto][2]

    if capacidad == 0:
        tips.append(("🛑", "Tus deudas actuales ya ocupan tu capacidad de pago",
                     "Tus pagos mensuales superan el 40 % de tu ingreso. Antes de pedir un crédito nuevo, "
                     "intenta reducir o unificar tus deudas actuales."))
    elif not resultados.empty and not resultados["se_ajusta"].any():
        mejor = resultados.sort_values("tasa_estimada").iloc[0]
        texto = (f"Con tu ingreso, la cuota máxima recomendada es **{pesos(capacidad)}**. "
                 f"A {meses} meses podrías pedir hasta **{pesos(mejor['monto_maximo'])}**.")
        for m in range(meses + 12, plazo_max + 1, 12):
            if cuota(monto, mejor["tasa_estimada"], m) <= capacidad:
                texto += f" O mantener el monto y ampliar el plazo a **{m} meses**."
                break
        tips.append(("📏", "Ajusta el monto o el plazo", texto))

    if producto == "Libre inversión" and perfil.situacion in ("Empleado", "Pensionado"):
        lib = tasas[tasas["producto"] == "Libranza"]
        libre = tasas[tasas["producto"] == "Libre inversión"]
        if not lib.empty and not libre.empty:
            t_lib = np.average(lib["tasa"], weights=lib["monto"])
            t_libre = np.average(libre["tasa"], weights=libre["monto"])
            if t_lib < t_libre:
                ahorro = (cuota(monto, t_libre, meses) - cuota(monto, t_lib, meses)) * meses
                tips.append(("🧾", "Pregunta por un crédito de libranza",
                             f"Como eres {perfil.situacion.lower()}, puedes pedirlo con descuento de nómina. "
                             f"La tasa promedio es **{porcentaje(t_lib)}** frente a **{porcentaje(t_libre)}** en libre "
                             f"inversión: te ahorrarías cerca de **{pesos(ahorro)}** en total."))

    if len(resultados) > 1:
        dif = resultados["total_pagar"].max() - resultados["total_pagar"].min()
        tips.append(("🔍", "Comparar sí vale la pena",
                     f"Entre el banco más barato y el más caro hay **{pesos(dif)}** de diferencia "
                     "en el total a pagar por el mismo crédito."))

    if perfil.uso_tarjetas > 0.7:
        tips.append(("💳", "Baja el uso de tus tarjetas",
                     f"Usas el {porcentaje(100 * perfil.uso_tarjetas, 0)} de tu cupo. Mantenerlo por debajo del 30 % "
                     "es una de las formas más rápidas de mejorar tu perfil de riesgo."))

    if perfil.total_moras:
        tips.append(("📋", "Revisa tu historial de crédito",
                     "Tus atrasos pesan en la decisión de los bancos. Ponte al día y consulta gratis tu "
                     "reporte en [Datacrédito](https://www.midatacredito.com) o "
                     "[TransUnion](https://www.transunion.co) para verificar que esté correcto."))

    if segmento == "4. Muy alto":
        tips.append(("🌱", "Considera bancos de microfinanzas",
                     "Con tu perfil actual es difícil que un banco tradicional apruebe el crédito. Bancos como "
                     "Mundo Mujer, Banco W o Mibanco atienden a personas con poco o ningún historial."))

    if producto.startswith("Vivienda"):
        tips.append(("🏠", "Prepara la cuota inicial",
                     "Los bancos suelen financiar hasta el 70 % del valor de la vivienda (80 % si es VIS). "
                     "La cuota no debería superar el 30 % de tus ingresos familiares."))
    elif producto == "Vehículo":
        tips.append(("🚗", "Da una buena cuota inicial",
                     "Entre más alta la cuota inicial, menor el riesgo para el banco y mejor la tasa que te pueden ofrecer."))
    elif producto == "Tarjeta de crédito":
        tips.append(("💡", "Paga a una sola cuota cuando puedas",
                     "Las compras a una cuota que pagas completas en la fecha límite normalmente no generan intereses."))

    if perfil.situacion == "Independiente":
        tips.append(("📂", "Ten tus soportes de ingreso listos",
                     "Como independiente, los bancos suelen pedir extractos bancarios, declaración de renta "
                     "o certificado de ingresos firmado por un contador."))
    return tips
