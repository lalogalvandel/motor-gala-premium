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

def calcular_var_estocastico(valores_portafolio, confianza=0.995):
    """VaR no paramétrico sobre los valores del portafolio."""
    return np.percentile(valores_portafolio, (1 - confianza) * 100)

def calcular_var_excedente(flujos_pasivos, tiempos_pasivos,
                           activos_valor, activos_duracion, activos_convexidad,
                           tasa_inicial, n_escenarios=1000, n_pasos=12,
                           kappa=0.15, theta=0.065, sigma=0.02, confianza=0.995):
    """
    Calcula el VaR del excedente (activos - pasivos) mediante Monte Carlo
    usando el modelo Vasicek exacto con variables antitéticas.
    Retorna: var_99_5, distribucion_perdidas, escenarios_finales_tasa.
    """
    # Generar caminos de tasa
    tasas = generar_escenarios_tasas(tasa_inicial, n_escenarios, n_pasos, kappa, theta, sigma)
    tasas_finales = tasas[-1]  # tasas al final del horizonte (1 año = 12 pasos mensuales)

    # Valor presente de pasivos en cada escenario (usando la tasa final como tasa de descuento simple)
    vp_pasivos = np.sum(flujos_pasivos * (1 + tasas_finales[:, np.newaxis]) ** -tiempos_pasivos, axis=1)

    # Valor de activos en cada escenario: aproximación de segundo orden con duración y convexidad
    # Δy = tasa_final - tasa_inicial
    delta_y = tasas_finales - tasa_inicial
    v_activos_esc = activos_valor * (1 - activos_duracion * delta_y + 0.5 * activos_convexidad * delta_y**2)

    # Excedente
    excedente_esc = v_activos_esc - vp_pasivos

    # Pérdida respecto al excedente base (calculado con tasa_inicial)
    vp_pasivos_base = np.sum(flujos_pasivos * (1 + tasa_inicial) ** -tiempos_pasivos)
    v_activos_base = activos_valor  # asumimos que a tasa_inicial no hay cambio
    excedente_base = v_activos_base - vp_pasivos_base
    perdidas = excedente_base - excedente_esc

    # VaR al nivel de confianza (percentil de las pérdidas)
    var = np.percentile(perdidas, confianza * 100)

    return var, perdidas, tasas_finales
