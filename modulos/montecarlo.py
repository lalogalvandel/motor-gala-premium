import scipy.stats as stats
import numpy as np

def simular_tasas_cir(r0, tasa_neutral, velocidad_reversion, volatilidad_tasa, meses, num_simulaciones):
    """
    Modelo de Cox-Ingersoll-Ross (CIR) para proyección estocástica de tasas de interés.
    Garantiza reversión a la media y estricta positividad de las tasas.
    """
    dt = 1 / 12  # Paso mensual
    tasas = np.zeros((meses, num_simulaciones))
    tasas[0] = r0  # Tasa Banxico actual
    
    for t in range(1, meses):
        # Ecuación diferencial estocástica CIR: dr = a(b-r)dt + sigma * sqrt(r) * dW
        dr = (velocidad_reversion * (tasa_neutral - tasas[t-1]) * dt + 
              volatilidad_tasa * np.sqrt(tasas[t-1]) * np.random.normal(0, np.sqrt(dt), num_simulaciones))
        
        # Actualizamos la tasa y aplicamos un piso (floor) de 0.1% para evitar colapsos matemáticos
        tasas[t] = np.maximum(tasas[t-1] + dr, 0.001)
        
    return tasas

def calibrar_grados_libertad(retornos_diarios):
    """
    Calibra los grados de libertad de una distribución t-Student.
    Blindado contra inanición de datos y valores nulos.
    """
    # 1. Limpiamos cualquier rastro de NaNs que haya sobrevivido
    retornos_limpios = retornos_diarios.dropna()
    
    if len(retornos_limpios) < 20:
        # Asumimos 4.0 (una distribución con colas pesadas moderadas) por seguridad
        return 4.0 
        
    try:
        # 3. Ajustamos la distribución de forma segura
        params = stats.t.fit(retornos_limpios, floc=0)
        return params[0]
    except Exception:
        # Si SciPy entra en pánico por matemáticas extremas, salvamos el proceso
        return 4.0

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

    p5  = np.percentile(escenarios, 5, axis=1)
    p25 = np.percentile(escenarios, 25, axis=1)  
    p50 = np.percentile(escenarios, 50, axis=1)
    p75 = np.percentile(escenarios, 75, axis=1) 
    p95 = np.percentile(escenarios, 95, axis=1)

    return escenarios, p5, p25, p50, p75, p95, benchmark_fijo, df_t
