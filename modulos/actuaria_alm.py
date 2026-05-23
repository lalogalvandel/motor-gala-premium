import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import minimize

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO ALM Y SOLVENCIA II - MOTOR GALA INSTITUCIONAL
# ══════════════════════════════════════════════════════════════════════════════

def calcular_duracion_convexidad(flujos: np.ndarray, tiempos: np.ndarray, ytm: float) -> tuple[float, float, float]:
    # Factores de descuento 1/(1+ytm)^t  –  forma más directa y numéricamente estable
    valores_presentes = flujos * (1 + ytm) ** -tiempos
    precio = np.sum(valores_presentes)

    d_mac = np.dot(tiempos, valores_presentes) / precio
    d_mod = d_mac / (1 + ytm)

    # Convexidad: (1/P) * Σ [t(t+1) * VP_t] / (1+y)^2
    convexidad = np.dot(tiempos * (tiempos + 1), valores_presentes) / (precio * (1 + ytm) ** 2)

    return precio, d_mod, convexidad


def simular_brecha_duracion(d_activos: float, d_pasivos: float, v_activos: float, v_pasivos: float) -> float:
    # Fórmula directa de la brecha de duración (sin cambios necesarios)
    return d_activos - (v_pasivos / v_activos) * d_pasivos


def calcular_rcs_mercado(exposicion: float, volatilidad_anual: float, nivel_confianza: float = 0.995) -> float:
    # Cálculo del requerimiento de capital por riesgo de mercado (ya óptimo)
    return exposicion * volatilidad_anual * norm.ppf(nivel_confianza)


def optimizar_inmunizacion(duraciones_activos: np.ndarray,
                           convexidades_activos: np.ndarray,
                           rendimientos_activos: np.ndarray,
                           duracion_pasivo: float,
                           convexidad_pasivo: float) -> dict:

    num_activos = len(duraciones_activos)

    # Maximizar rendimiento => minimizar su negativo
    def funcion_objetivo(pesos):
        return -np.dot(pesos, rendimientos_activos)

    restricciones = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0},
        {'type': 'eq', 'fun': lambda w: np.dot(w, duraciones_activos) - duracion_pasivo},
        {'type': 'ineq', 'fun': lambda w: np.dot(w, convexidades_activos) - convexidad_pasivo}
    ]

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
        return {"exito": False, "mensaje": "Imposible lograr inmunización total (Duración + Convexidad)."}

    pesos_optimos = resultado.x

    return {
        "exito": True,
        "pesos": pesos_optimos,
        "duracion_lograda": np.dot(pesos_optimos, duraciones_activos),
        "convexidad_lograda": np.dot(pesos_optimos, convexidades_activos),
        "rendimiento_esperado": np.dot(pesos_optimos, rendimientos_activos)
    }


# ── Pruebas unitarias internas ──
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
