import numpy as np

def generar_escenarios_tasas(tasa_inicial, n_escenarios, n_pasos, kappa, theta, sigma):
    """
    Genera caminos de tasas Vasicek usando la transición exacta
    con reducción opcional de varianza (variables antitéticas).
    """
    dt = 1/12
    tasas = np.zeros((n_pasos, n_escenarios))
    tasas[0] = tasa_inicial

    a = np.exp(-kappa * dt)
    b = theta * (1 - a)
    # Varianza exacta (maneja el caso kappa=0)
    if kappa > 0:
        var = sigma**2 * (1 - a**2) / (2 * kappa)
    else:
        var = sigma**2 * dt
    std = np.sqrt(var)

    for t in range(1, n_pasos):
        # ── Aquí se inserta la técnica antitética ──
        if n_escenarios % 2 == 0:
            Z = np.random.standard_normal(n_escenarios // 2)
            Z = np.concatenate([Z, -Z])
        else:
            Z = np.random.standard_normal(n_escenarios)
        # ─────────────────────────────────────────
        tasas[t] = a * tasas[t-1] + b + std * Z

    return tasas
