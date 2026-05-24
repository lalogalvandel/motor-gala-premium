import numpy as np

def generar_escenarios_tasas(tasa_inicial, n_escenarios, n_pasos, kappa, theta, sigma):
    dt = 1/12
    tasas = np.zeros((n_pasos, n_escenarios))
    tasas[0] = tasa_inicial
    a = np.exp(-kappa * dt)
    b = theta * (1 - a)
    if kappa > 0:
        var = sigma**2 * (1 - a**2) / (2 * kappa)
    else:
        var = sigma**2 * dt
    std = np.sqrt(var)

    for t in range(1, n_pasos):
        if n_escenarios % 2 == 0:
            Z = np.random.standard_normal(n_escenarios // 2)
            Z = np.concatenate([Z, -Z])
        else:
            Z = np.random.standard_normal(n_escenarios)
        tasas[t] = a * tasas[t-1] + b + std * Z
    return tasas

def valorizar_portafolio_en_escenarios(tasas_escenarios, flujos, vencimientos):
    """
    Calcula el valor presente del portafolio en cada escenario
    usando la tasa final de cada camino (simplificación).
    flujos: array de flujos de caja
    vencimientos: array de tiempos en años
    Retorna array 1D con el VP para cada escenario.
    """
    # tasas_escenarios[-1] tiene la tasa final de cada camino
    tasas_finales = tasas_escenarios[-1]
    # VP = sum(flujo / (1+r)^t)
    factores = (1 + tasas_finales[:, None]) ** vencimientos[None, :]
    vp = np.sum(flujos[None, :] / factores, axis=1)
    return vp

def calcular_var_portafolio(valores_portafolio, confianza=0.995):
    """VaR no paramétrico sobre los valores del portafolio."""
    return np.percentile(valores_portafolio, (1 - confianza) * 100)
