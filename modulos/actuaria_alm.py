import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO ALM Y SOLVENCIA II - MOTOR GALA INSTITUCIONAL
# ══════════════════════════════════════════════════════════════════════════════

def calcular_duracion_convexidad(flujos: np.ndarray, tiempos: np.ndarray, ytm: float) -> tuple[float, float, float]:
    valores_presentes = flujos * (1 + ytm) ** -tiempos
    precio = np.sum(valores_presentes)
    d_mac = np.dot(tiempos, valores_presentes) / precio
    d_mod = d_mac / (1 + ytm)
    convexidad = np.dot(tiempos * (tiempos + 1), valores_presentes) / (precio * (1 + ytm) ** 2)
    return precio, d_mod, convexidad


def simular_brecha_duracion(d_activos: float, d_pasivos: float, v_activos: float, v_pasivos: float) -> float:
    return d_activos - (v_pasivos / v_activos) * d_pasivos


def calcular_rcs_mercado(exposicion: float, volatilidad_anual: float, nivel_confianza: float = 0.995) -> float:
    return exposicion * volatilidad_anual * norm.ppf(nivel_confianza)


def optimizar_inmunizacion(duraciones_activos: np.ndarray,
                           convexidades_activos: np.ndarray,
                           rendimientos_activos: np.ndarray,
                           duracion_pasivo: float,
                           convexidad_pasivo: float,
                           v_activos: float = None,
                           v_pasivos: float = None,
                           vol_activos: float = None,
                           d_activos: float = None) -> dict:

    num_activos = len(duraciones_activos)

    def funcion_objetivo(pesos):
        return -np.dot(pesos, rendimientos_activos)

    restricciones = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
        {'type': 'eq', 'fun': lambda w: np.dot(w, duraciones_activos) - duracion_pasivo},
        {'type': 'ineq', 'fun': lambda w: np.dot(w, convexidades_activos) - convexidad_pasivo}
    ]

    usa_restriccion_capital = False
    if all(v is not None for v in [v_activos, v_pasivos, vol_activos, d_activos]):
        superavit = v_activos - v_pasivos
        if superavit > 0 and d_activos > 0:
            usa_restriccion_capital = True
            z_score = norm.ppf(0.995)
            sigma_y = vol_activos / d_activos

            def scr_constraint(w):
                cartera_vol = sigma_y * np.sqrt(np.sum((w * duraciones_activos) ** 2))
                scr = v_activos * cartera_vol * z_score
                return superavit - scr
            restricciones.append({'type': 'ineq', 'fun': scr_constraint})

    limites = tuple((0.0, 1.0) for _ in range(num_activos))
    pesos_iniciales = np.ones(num_activos) / num_activos

    resultado = minimize(
        funcion_objetivo,
        pesos_iniciales,
        method='SLSQP',
        bounds=limites,
        constraints=restricciones
    )

    if not resultado.success:
        if usa_restriccion_capital:
            mensaje = ("Imposible lograr inmunización total con el capital disponible "
                       "(Duración + Convexidad + Restricción de SCR).")
        else:
            mensaje = "Imposible lograr inmunización total (Duración + Convexidad)."
        return {"exito": False, "mensaje": mensaje}

    pesos_optimos = resultado.x
    return {
        "exito": True,
        "pesos": pesos_optimos,
        "duracion_lograda": np.dot(pesos_optimos, duraciones_activos),
        "convexidad_lograda": np.dot(pesos_optimos, convexidades_activos),
        "rendimiento_esperado": np.dot(pesos_optimos, rendimientos_activos)
    }


def frontera_eficiente_alm(duraciones_activos, convexidades_activos, rendimientos_activos,
                           duracion_pasivo, convexidad_pasivo,
                           v_activos, v_pasivos, vol_activos, d_activos,
                           num_puntos=20):
    """
    Traza la frontera eficiente: maximiza yield variando la duración objetivo
    desde la mínima de los activos hasta la del pasivo apalancado,
    respetando convexidad y restricción de capital (si procede).
    Retorna lista de diccionarios con {duracion, yield, scr_est, pesos, exito}.
    """
    ratio_ap = v_pasivos / v_activos
    target_max = duracion_pasivo
    target_min = np.min(duraciones_activos)
    if target_min >= target_max:
        target_min = target_max * 0.8

    objetivos = np.linspace(target_min, target_max, num_puntos)
    frontera = []

    for d_target in objetivos:
        res = optimizar_inmunizacion(
            duraciones_activos, convexidades_activos, rendimientos_activos,
            d_target, convexidad_pasivo,
            v_activos=v_activos, v_pasivos=v_pasivos,
            vol_activos=vol_activos, d_activos=d_activos
        )
        if res["exito"]:
            sigma_y = vol_activos / d_activos if d_activos > 0 else 0
            cartera_vol = sigma_y * np.sqrt(np.sum((res["pesos"] * duraciones_activos) ** 2))
            scr_est = v_activos * cartera_vol * norm.ppf(0.995)
            frontera.append({
                "duracion": res["duracion_lograda"],
                "yield": res["rendimiento_esperado"],
                "scr_est": scr_est,
                "pesos": res["pesos"],
                "exito": True
            })
        else:
            frontera.append({
                "duracion": d_target,
                "yield": None,
                "scr_est": None,
                "pesos": None,
                "exito": False
            })
    return frontera


if __name__ == "__main__":
    print("--- DIAGNÓSTICO ALM ---")
    flujos_pasivos = np.array([100, 100, 100, 100, 1100])
    tiempos = np.array([1, 2, 3, 4, 5])
    tasa_dummy = 0.065

    valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(flujos_pasivos, tiempos, tasa_dummy)

    print(f"Valor Presente de Pasivos: ${valor_pasivo:,.2f}")
    print(f"Duración Modificada Exigida: {dur_pasivo:.2f} años")
    print(f"Convexidad Exigida: {conv_pasivo:.2f}\n")

    print("--- OPTIMIZADOR DE RESERVAS (SHOCK-PROOF) ---")
    nombres_bonos = ["CETES 1A", "Mbono 3A", "Mbono 10A", "Deuda Corp 5A"]
    duraciones_mercado = np.array([0.9, 2.8, 8.1, 4.2])
    convexidades_mercado = np.array([1.2, 9.5, 78.4, 22.1])
    yields_mercado = np.array([0.10, 0.09, 0.085, 0.11])

    resultado = optimizar_inmunizacion(
        duraciones_mercado,
        convexidades_mercado,
        yields_mercado,
        dur_pasivo,
        conv_pasivo
    )

    if resultado["exito"]:
        print(f"Duración Lograda: {resultado['duracion_lograda']:.2f} años")
        print(f"Convexidad Lograda: {resultado['convexidad_lograda']:.2f} (Supera la exigida de {conv_pasivo:.2f})")
        print(f"Rendimiento de la Cartera: {resultado['rendimiento_esperado']*100:.2f}%\n")
        print("Pesos a Invertir:")
        for nombre, peso in zip(nombres_bonos, resultado["pesos"]):
            if peso > 0.001:
                print(f"- {nombre}: {peso*100:.1f}%")
    else:
        print(f"Falla: {resultado['mensaje']}")
