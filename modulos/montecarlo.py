import numpy as np
from scipy import stats

def calibrar_grados_libertad(retornos_diarios) -> float:
    """
    Calibra los grados de libertad de la t de Student
    ajustando a los retornos históricos reales del portafolio.
    Típicamente entre 3 y 6 para activos financieros.
    """
    params = stats.t.fit(retornos_diarios, floc=0)
    df_calibrado = params[0]
    # Clampear entre 3 y 30 para estabilidad numérica
    return float(np.clip(df_calibrado, 3, 30))

def simular_capital(
    capital_inicial: float,
    aportacion_periodica: float,
    rendimiento_anual: float,
    volatilidad_anual: float,
    meses: int = 36,
    frecuencia_aportacion: str = 'Mensual',  #  Nueva variable (Mensual, Trimestral, Anual)
    tasa_benchmark: float = 0.0705,          #  Tasa de Banxico/Seguro para comparar
    num_simulaciones: int = 1000,
    seed: int = 42,
    retornos_diarios=None,
) -> tuple:
    """
    Movimiento Browniano Geométrico mensual con shocks
    de distribución t de Student (fat tails) y aportaciones dinámicas.
    """
    np.random.seed(seed)

    mu  = rendimiento_anual / 12
    sig = volatilidad_anual / np.sqrt(12)

    # Calibrar grados de libertad
    if retornos_diarios is not None:
        df_t = calibrar_grados_libertad(retornos_diarios)
    else:
        df_t = 5.0  # estándar conservador para mercados emergentes

    # Shocks con fat tails — t de Student normalizada
    shocks_t = stats.t.rvs(
        df=df_t,
        size=(meses, num_simulaciones)
    )
    shocks_t /= np.sqrt(df_t / (df_t - 2))

    escenarios = np.zeros((meses + 1, num_simulaciones))
    escenarios[0] = capital_inicial

    #Inicializamos el cálculo aburrido (línea determinista)
    benchmark_fijo = np.zeros(meses + 1)
    benchmark_fijo[0] = capital_inicial
    tasa_bench_mensual = tasa_benchmark / 12

    for t in range(1, meses + 1):
        # 🚦 El Semáforo de Inyecciones
        inyeccion_hoy = 0
        if frecuencia_aportacion == 'Mensual':
            inyeccion_hoy = aportacion_periodica
        elif frecuencia_aportacion == 'Trimestral' and t % 3 == 0:
            inyeccion_hoy = aportacion_periodica
        elif frecuencia_aportacion == 'Anual' and t % 12 == 0:
            inyeccion_hoy = aportacion_periodica

        # Simulación de Markowitz
        escenarios[t] = (
            (escenarios[t - 1] + inyeccion_hoy)
            * np.exp((mu - 0.5 * sig**2) + sig * shocks_t[t - 1])
        )
        
        # Simulación del Banco / Aseguradora
        benchmark_fijo[t] = (benchmark_fijo[t - 1] + inyeccion_hoy) * (1 + tasa_bench_mensual)

    p5  = np.percentile(escenarios, 5,  axis=1)
    p50 = np.percentile(escenarios, 50, axis=1)
    p95 = np.percentile(escenarios, 95, axis=1)

    return escenarios, p5, p50, p95, benchmark_fijo, df_t