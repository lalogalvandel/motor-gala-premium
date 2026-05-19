import numpy as np
from scipy.optimize import minimize

def simular_portafolios(retornos_anuales, matriz_cov, tasa_rf, num_portafolios=2000):
    """
    Versión vectorizada — sin loops Python, todo en NumPy.
    10x más rápido que la versión original.
    """
    n_activos = len(retornos_anuales)

    # Generar todos los pesos de golpe
    pesos_random = np.random.random((num_portafolios, n_activos))
    pesos_random /= pesos_random.sum(axis=1, keepdims=True)

    # Retornos: producto punto vectorizado
    retornos = pesos_random @ retornos_anuales.values

    # Volatilidades: vectorizado con einsum
    varianzas = np.einsum('ij,jk,ik->i', pesos_random, matriz_cov.values, pesos_random)
    volatilidades = np.sqrt(varianzas)

    # Sharpe
    sharpes = (retornos - tasa_rf) / volatilidades

    resultados = np.array([retornos, volatilidades, sharpes])

    return resultados, pesos_random


def portafolio_optimo(resultados, pesos_guardados, retornos_anuales, matriz_cov, tasa_rf):
    idx       = np.argmax(resultados[2])
    pesos     = pesos_guardados[idx]
    retorno   = resultados[0, idx]
    vol       = resultados[1, idx]
    sharpe    = resultados[2, idx]
    return pesos, retorno, vol, sharpe

def optimizar_sharpe_slsqp(retornos_anuales, matriz_cov, tasa_rf, peso_min=0.0, peso_max=1.0, max_riesgo_total=1.0, es_riesgo=None):
    """
    Motor Institucional con restricciones de concentración y Glide Path Actuarial.
    """
    n_activos = len(retornos_anuales)

    def funcion_objetivo(pesos):
        retorno = np.sum(pesos * retornos_anuales)
        vol = np.sqrt(np.dot(pesos.T, np.dot(matriz_cov, pesos)))
        sharpe = (retorno - tasa_rf) / vol
        return -sharpe 

    # Si no se define el riesgo, asumimos que todo es riesgo
    if es_riesgo is None:
        es_riesgo = np.ones(n_activos)

    def restriccion_riesgo(pesos):
        # La suma de dinero en activos de riesgo no debe superar el límite del Glide Path
        return max_riesgo_total - np.sum(pesos * es_riesgo)

    restricciones = [
        {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},          
        {'type': 'ineq', 'fun': restriccion_riesgo}              
    ]
    
    limites = tuple((peso_min, peso_max) for _ in range(n_activos))
    pesos_iniciales = np.array(n_activos * [1. / n_activos])

    resultado = minimize(funcion_objetivo, pesos_iniciales, 
                         method='SLSQP', bounds=limites, constraints=restricciones)

    return resultado.x