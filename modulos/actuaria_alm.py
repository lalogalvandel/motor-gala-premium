import numpy as np
import pandas as pd
from scipy.stats import norm

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO ALM Y SOLVENCIA II - MOTOR GALA INSTITUCIONAL
# ══════════════════════════════════════════════════════════════════════════════

def calcular_duracion_convexidad(flujos: np.ndarray, tiempos: np.ndarray, ytm: float) -> tuple[float, float, float]:
    """
    Calcula el precio, Duración Modificada y Convexidad de un bono o portafolio de pasivos.
    
    Args:
        flujos: Array con los flujos de efectivo (cupones/siniestros).
        tiempos: Array con el tiempo en años para cada flujo.
        ytm: Yield to Maturity (Tasa de rendimiento o tasa de descuento regulatoria).
        
    Returns:
        Precio actual, Duración Modificada, Convexidad.
    """
    factores_descuento = (1 + ytm) ** tiempos
    valores_presentes = flujos / factores_descuento
    
    precio = np.sum(valores_presentes)
    
    # Macaulay Duration
    d_mac = np.sum(tiempos * valores_presentes) / precio
    
    # Modified Duration
    d_mod = d_mac / (1 + ytm)
    
    # Convexity
    convexidad = np.sum((tiempos ** 2 + tiempos) * valores_presentes / ((1 + ytm)**2)) / precio
    
    return precio, d_mod, convexidad


def simular_brecha_duracion(d_activos: float, d_pasivos: float, v_activos: float, v_pasivos: float) -> float:
    """
    Calcula el Duration Gap (Brecha de Duración). 
    Si la brecha no es cero, la aseguradora tiene exposición al riesgo de tasas de interés.
    """
    # Brecha de duración ajustada por el ratio de apalancamiento
    gap = d_activos - (v_pasivos / v_activos) * d_pasivos
    return gap


def calcular_rcs_mercado(exposicion: float, volatilidad: float, nivel_confianza: float = 0.995) -> float:
    """
    Calcula el Requerimiento de Capital de Solvencia (RCS / SCR) bajo la fórmula estándar.
    Solvencia II exige cubrir el VaR a 1 año con un nivel de confianza del 99.5%.
    """
    z_score = norm.ppf(nivel_confianza)
    # Pérdida máxima esperada en 1 año (Capital que debe tener en reserva líquida)
    scr = exposicion * volatilidad * z_score
    return scr

# ── Pruebas unitarias internas (Se ignoran al importar) ──
if __name__ == "__main__":
    # Ejemplo: Aseguradora tiene que pagar 100M anuales por 5 años (Pasivos)
    flujos_pasivos = np.array([100, 100, 100, 100, 1100]) # 1100 en el año 5 por vencimientos
    tiempos = np.array([1, 2, 3, 4, 5])
    tasa_libre_riesgo = 0.065 # Banxico actual aprox
    
    valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(flujos_pasivos, tiempos, tasa_libre_riesgo)
    
    print(f"Valor Presente de Pasivos: ${valor_pasivo:,.2f}")
    print(f"Duración Modificada Exigida: {dur_pasivo:.2f} años")
    print(f"Convexidad: {conv_pasivo:.2f}")
