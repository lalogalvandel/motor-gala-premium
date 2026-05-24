import numpy as np

def generar_escenarios_tasas(tasa_inicial, n_escenarios, n_pasos, kappa, theta, sigma):
    """
    Genera caminos de tasas Vasicek usando la transición exacta:
        r_{t+dt} = r_t * e^{-kappa dt} + theta * (1 - e^{-kappa dt})
                   + sigma * sqrt((1 - e^{-2 kappa dt}) / (2 kappa)) * Z
    con Z ~ N(0,1).
    """
    dt = 1/12
    tasas = np.zeros((n_pasos, n_escenarios))
    tasas[0] = tasa_inicial

    a = np.exp(-kappa * dt)
    b = theta * (1 - a)
    # Varianza exacta (para kappa > 0; el límite kappa→0 sería sigma^2 * dt)
    var = sigma**2 * (1 - a**2) / (2 * kappa) if kappa > 0 else sigma**2 * dt
    std = np.sqrt(var)

    for t in range(1, n_pasos):
        Z = np.random.standard_normal(n_escenarios)   # más rápido que normal(0,1)
        tasas[t] = a * tasas[t-1] + b + std * Z

    return tasas
