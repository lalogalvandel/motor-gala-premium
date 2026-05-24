import numpy as np

def generar_escenarios_tasas(tasa_inicial, n_escenarios, n_pasos, kappa, theta, sigma):
    """
    Genera caminos estocásticos de tasas usando Vasicek:
    dr = kappa * (theta - r) * dt + sigma * dW
    """
    dt = 1/12  # Pasos mensuales
    tasas = np.zeros((n_pasos, n_escenarios))
    tasas[0] = tasa_inicial
    
    for t in range(1, n_pasos):
        dr = kappa * (theta - tasas[t-1]) * dt + sigma * np.sqrt(dt) * np.random.normal(0, 1, n_escenarios)
        tasas[t] = tasas[t-1] + dr
        
    return tasas
