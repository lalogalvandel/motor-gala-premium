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
    tasas_finales = tasas_escenarios[-1]
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
    
    Los pasivos se valoran con la fórmula cerrada de Vasicek
    para bonos cupón cero, evitando la aproximación de tasa única.
    """
    # Generar caminos de tasa
    tasas = generar_escenarios_tasas(tasa_inicial, n_escenarios, n_pasos, kappa, theta, sigma)
    tasas_finales = tasas[-1]          # r(1) en cada escenario

    # --- Valor presente de los pasivos en cada escenario (Fórmula exacta Vasicek) ---
    T_liab = np.asarray(tiempos_pasivos, dtype=float)
    flujos = np.asarray(flujos_pasivos, dtype=float)
    # Tiempo restante hasta cada vencimiento desde el horizonte (t=1 año)
    tau = T_liab - 1.0                 # años que faltan para el pago

    # Parámetros del modelo
    k = kappa
    th = theta
    s = sigma

    # Calcular B(tau) y A(tau) para cada vencimiento
    # Si tau <= 0, el bono ya venció y su valor es 1 (se paga el flujo completo)
    B = np.where(tau > 0, (1 - np.exp(-k * tau)) / k, 0.0)
    A = np.where(
        tau > 0,
        (th - s**2/(2*k**2)) * (B - tau) - (s**2 * B**2) / (4*k),
        0.0
    )
    # Precio de cada bono cupón cero: P(tau, r) = exp(A - B * r)
    # Expandimos a dimensión de escenarios: (n_escenarios, n_flujos)
    descuentos = np.exp(A - B * tasas_finales[:, np.newaxis])
    vp_pasivos = np.sum(flujos * descuentos, axis=1)

    # --- Valor presente base (t=0) usando la misma fórmula de Vasicek ---
    tau0 = T_liab                          # años al vencimiento desde hoy
    B0 = (1 - np.exp(-k * tau0)) / k
    A0 = (th - s**2/(2*k**2)) * (B0 - tau0) - (s**2 * B0**2) / (4*k)
    precios_base = np.exp(A0 - B0 * tasa_inicial)
    vp_pasivos_base = np.sum(flujos * precios_base)

    # --- Valor de los activos en cada escenario (aproximación de Taylor) ---
    delta_y = tasas_finales - tasa_inicial
    v_activos_esc = activos_valor * (1 - activos_duracion * delta_y +
                                     0.5 * activos_convexidad * delta_y**2)

    # --- Excedente y pérdidas ---
    excedente_esc = v_activos_esc - vp_pasivos
    excedente_base = activos_valor - vp_pasivos_base
    perdidas = excedente_base - excedente_esc

    # VaR al nivel de confianza
    var = np.percentile(perdidas, confianza * 100)

    return var, perdidas, tasas_finales
