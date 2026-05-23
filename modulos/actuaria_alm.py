import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import minimize
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


def calcular_rcs_mercado(exposicion: float, volatilidad_anual: float, nivel_confianza: float = 0.995) -> float:
    """
    Calcula el Requerimiento de Capital de Solvencia (RCS / SCR) bajo la fórmula estándar.
    Solvencia II (CUSF) exige cubrir el VaR a 1 año con un nivel de confianza del 99.5%.
    """
    z_score = norm.ppf(nivel_confianza)
    # Pérdida máxima esperada en 1 año (Capital que debe tener en reserva líquida)
    scr = exposicion * volatilidad_anual * z_score
    return scr

# ── Pruebas unitarias internas (Se ignoran al importar desde app_institucional.py) ──
if __name__ == "__main__":
    # Ejemplo: Aseguradora tiene que pagar 100M anuales por 5 años (Pasivos)
    flujos_pasivos = np.array([100, 100, 100, 100, 1100]) # 1100 en el año 5 por vencimientos
    tiempos = np.array([1, 2, 3, 4, 5])
    
    # NOTA ARCHITECTURE: Dejamos la tasa estática aquí para pruebas locales offline. 
    # En producción, app_institucional.py se encarga de inyectar la tasa en vivo de Banxico.
    tasa_libre_riesgo_dummy = 0.065 
    
    valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(flujos_pasivos, tiempos, tasa_libre_riesgo_dummy)
    
    print(f"Valor Presente de Pasivos: ${valor_pasivo:,.2f}")
    print(f"Duración Modificada Exigida: {dur_pasivo:.2f} años")
    print(f"Convexidad: {conv_pasivo:.2f}")
    
if __name__ == "__main__":
    print("--- DIAGNÓSTICO ALM ---")
    flujos_pasivos = np.array([100, 100, 100, 100, 1100])
    tiempos = np.array([1, 2, 3, 4, 5])
    tasa_dummy = 0.065 
    
    valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(flujos_pasivos, tiempos, tasa_dummy)
    
    print(f"Valor Presente de Pasivos: ${valor_pasivo:,.2f}")
    print(f"Duración Modificada Exigida: {dur_pasivo:.2f} años\n")
    
    print("--- OPTIMIZACIÓN DE RESERVAS ---")
    # Simulamos el mercado: Bonos disponibles para la aseguradora
    nombres_bonos = ["CETES 1A", "Mbono 3A", "Mbono 10A", "Deuda Corp 5A"]
    duraciones_mercado = np.array([0.9, 2.8, 8.1, 4.2]) # En años
    yields_mercado = np.array([0.10, 0.09, 0.085, 0.11]) # Rendimientos
    
    resultado = optimizar_inmunizacion(duraciones_mercado, yields_mercado, dur_pasivo)
    
    if resultado["exito"]:
        print(f"Duración Lograda: {resultado['duracion_lograda']:.2f} años")
        print(f"Rendimiento de la Cartera: {resultado['rendimiento_esperado']*100:.2f}%")
        print("Pesos a Invertir:")
        for nombre, peso in zip(nombres_bonos, resultado["pesos"]):
            print(f"- {nombre}: {peso*100:.1f}%")
    else:
        print(f"Falla: {resultado['mensaje']}")
    
def optimizar_inmunizacion(duraciones_activos: np.ndarray, rendimientos_activos: np.ndarray, duracion_pasivo: float) -> dict:
    """
    Encuentra los pesos óptimos de un portafolio de bonos para inmunizar 
    la cartera contra el riesgo de tasas de interés (Duration Matching),
    maximizando el rendimiento de la cartera.
    """
    num_activos = len(duraciones_activos)
    
    # Función objetivo: Maximizar rendimiento = Minimizar el rendimiento negativo
    def funcion_objetivo(pesos):
        return -np.sum(pesos * rendimientos_activos)
        
    # Restricciones de Solvencia
    restricciones = [
        # 1. La suma de pesos debe ser exactamente 1 (100% del capital invertido)
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}, 
        
        # 2. CALCE DE DURACIÓN: La duración del portafolio debe ser igual a la del pasivo
        {'type': 'eq', 'fun': lambda w: np.sum(w * duraciones_activos) - duracion_pasivo}
    ]
    
    # Límites: Las aseguradoras no pueden vender bonos en corto, los pesos van de 0 a 1 (0% a 100%)
    limites = tuple((0.0, 1.0) for _ in range(num_activos))
    
    # Suposición inicial para arrancar el motor (Distribución equitativa)
    pesos_iniciales = np.ones(num_activos) / num_activos
    
    # Ejecutar Optimizador
    resultado = minimize(
        funcion_objetivo, 
        pesos_iniciales, 
        method='SLSQP', 
        bounds=limites, 
        constraints=restricciones
    )
    
    # Validar si matemáticamente es posible el calce (ej. si el pasivo dura 10 años pero solo tienes bonos de 1 a 3 años, es imposible)
    if not resultado.success:
        return {"exito": False, "mensaje": "Imposible calzar la duración con los activos proporcionados."}
        
    pesos_optimos = resultado.x
    
    return {
        "exito": True,
        "pesos": pesos_optimos,
        "duracion_lograda": np.sum(pesos_optimos * duraciones_activos),
        "rendimiento_esperado": np.sum(pesos_optimos * rendimientos_activos)
    }
