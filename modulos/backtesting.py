import numpy as np
import pandas as pd

def calcular_backtest_walk_forward(
    retornos_diarios: pd.DataFrame,
    funcion_optimizador,
    tasa_rf: float,
    peso_min: float = 0.0,
    peso_max: float = 1.0,
    max_riesgo_total: float = 1.0,
    es_riesgo: np.ndarray = None,
    df_regimenes: pd.DataFrame = None,
    ventana_entrenamiento: int = 252,
    frecuencia_rebalanceo: int = 63,
    capital_inicial: float = 100_000,
    comision_broker: float = 0.0015,
    benchmark_ticker_override: str = None,   # ← NUEVO, opcional
) -> tuple:
    
    cols = retornos_diarios.columns.tolist()
    # ── NUEVO: permite override del benchmark desde la UI ─────────────────────
    if benchmark_ticker_override and benchmark_ticker_override in cols:
        benchmark_ticker = benchmark_ticker_override
    else:
        benchmark_ticker = 'SPY' if 'SPY' in cols else cols[0]
    retorno_bench_completo = retornos_diarios[benchmark_ticker]

    retornos_estrategia = []
    fechas_estrategia = []
    
    pesos_anteriores = None  
    
    total_dias = len(retornos_diarios)
    
    if total_dias <= ventana_entrenamiento:
        # Si no hay suficiente historia, usamos la mitad de los datos para entrenar 
        # y la otra mitad para probar, con un mínimo de 21 días (1 mes)
        ventana_entrenamiento = max(21, total_dias // 2)
        frecuencia_rebalanceo = max(21, ventana_entrenamiento // 2)

    for inicio_test in range(ventana_entrenamiento, total_dias, frecuencia_rebalanceo):
        fin_test = min(inicio_test + frecuencia_rebalanceo, total_dias)
        datos_train = retornos_diarios.iloc[inicio_test - ventana_entrenamiento : inicio_test]
        
        ret_anuales_train = datos_train.mean() * 252
        cov_train = datos_train.cov() * 252
        
        riesgo_periodo = max_riesgo_total
        
        if df_regimenes is not None:
            fecha_decision = retornos_diarios.index[inicio_test - 1]
            if fecha_decision in df_regimenes.index:
                estado_mercado = df_regimenes.loc[fecha_decision, 'Regimen']
                if estado_mercado == 1: 
                    riesgo_periodo = 0.0 
        
        pesos_actuales = funcion_optimizador(
            ret_anuales_train, cov_train, tasa_rf, 
            peso_min=peso_min, peso_max=peso_max, 
            max_riesgo_total=riesgo_periodo, 
            es_riesgo=es_riesgo
        )

        # ── ESCUDO INMEDIATO CONTRA FALLOS DEL OPTIMIZADOR ──
        if pesos_actuales is None:
            # Si la matemática colapsa en este trimestre histórico, usamos pesos equitativos (1/N) como salvavidas
            n_activos_bt = len(es_riesgo)
            pesos_actuales = np.ones(n_activos_bt) / n_activos_bt
        
        # ── 🚨 CÁLCULO DE FRICCIÓN Y COSTOS DE TRANSACCIÓN ──
        if pesos_anteriores is not None:
            # Turnover: Suma de los cambios absolutos dividida entre 2
            # (Si vendes 10% de A para comprar 10% de B, solo moviste el 10% del capital real)
            turnover = np.sum(np.abs(pesos_actuales - pesos_anteriores)) / 2.0
            costo_transaccion = turnover * comision_broker
        else:
            # Costo de comprar el portafolio por primera vez
            costo_transaccion = 1.0 * comision_broker
            
        pesos_anteriores = pesos_actuales.copy() # Guardamos para el próximo trimestre
        
        datos_test = retornos_diarios.iloc[inicio_test : fin_test]
        retorno_periodo = (datos_test @ pesos_actuales)
        
        # Le restamos la comisión al rendimiento del primer día de este trimestre
        retorno_periodo.iloc[0] -= costo_transaccion
        
        retornos_estrategia.extend(retorno_periodo.tolist())
        fechas_estrategia.extend(datos_test.index.tolist())

    retorno_port = pd.Series(retornos_estrategia, index=fechas_estrategia)
    retorno_bench = retorno_bench_completo.loc[fechas_estrategia]

    equity_port  = capital_inicial * (1 + retorno_port).cumprod()
    equity_bench = capital_inicial * (1 + retorno_bench).cumprod()

    df_equity = pd.DataFrame({
        'Portafolio GaLa (Dinámico)': equity_port,
        f'Benchmark ({benchmark_ticker})': equity_bench,
    })

    return df_equity, benchmark_ticker, retorno_port, retorno_bench


def calcular_metricas_backtest(
    retorno_port: pd.Series, retorno_bench: pd.Series, tasa_rf: float,
    equity_port: pd.Series, equity_bench: pd.Series,
) -> dict:
    """Métricas comparativas institucionales."""
    
    if len(equity_port) < 2:
        return {
            'cagr_port': 0.0, 'cagr_bench': 0.0, 'vol_port': 0.0, 'vol_bench': 0.0,
            'sharpe_port': 0.0, 'sharpe_bench': 0.0, 'sortino_port': 0.0, 'sortino_bench': 0.0,
            'mdd_port': 0.0, 'mdd_bench': 0.0, 'calmar_port': 0.0, 'calmar_bench': 0.0,
            'beta': 1.0, 'alpha': 0.0,
        }

    n_años = len(retorno_port) / 252

    cagr_port  = (equity_port.iloc[-1]  / equity_port.iloc[0])  ** (1/n_años) - 1
    cagr_bench = (equity_bench.iloc[-1] / equity_bench.iloc[0]) ** (1/n_años) - 1

    vol_port  = retorno_port.std()  * np.sqrt(252)
    vol_bench = retorno_bench.std() * np.sqrt(252)

    sharpe_port  = (cagr_port  - tasa_rf) / vol_port
    sharpe_bench = (cagr_bench - tasa_rf) / vol_bench

    ret_neg_port  = retorno_port[retorno_port < 0]
    ret_neg_bench = retorno_bench[retorno_bench < 0]
    
    sortino_port  = (cagr_port  - tasa_rf) / (np.sqrt(np.mean(ret_neg_port**2))  * np.sqrt(252)) if len(ret_neg_port) > 0 else np.nan
    sortino_bench = (cagr_bench - tasa_rf) / (np.sqrt(np.mean(ret_neg_bench**2)) * np.sqrt(252)) if len(ret_neg_bench) > 0 else np.nan

    def max_dd(equity):
        pico = equity.cummax()
        dd   = (equity - pico) / pico
        return dd.min()

    mdd_port  = max_dd(equity_port)
    mdd_bench = max_dd(equity_bench)

    calmar_port  = cagr_port  / abs(mdd_port)  if mdd_port  != 0 else np.nan
    calmar_bench = cagr_bench / abs(mdd_bench) if mdd_bench != 0 else np.nan

    cov_matrix = np.cov(retorno_port, retorno_bench)
    beta  = cov_matrix[0, 1] / cov_matrix[1, 1]
    alpha = cagr_port - (tasa_rf + beta * (cagr_bench - tasa_rf))

    return {
        'cagr_port': cagr_port, 'cagr_bench': cagr_bench,
        'vol_port': vol_port, 'vol_bench': vol_bench,
        'sharpe_port': sharpe_port, 'sharpe_bench': sharpe_bench,
        'sortino_port': sortino_port, 'sortino_bench': sortino_bench,
        'mdd_port': mdd_port, 'mdd_bench': mdd_bench,
        'calmar_port': calmar_port, 'calmar_bench': calmar_bench,
        'beta': beta, 'alpha': alpha,
    }


def calcular_retornos_anuales(retorno_port: pd.Series, retorno_bench: pd.Series) -> pd.DataFrame:
    """Retornos anuales comparativos para gráfica de barras."""
    df = pd.DataFrame({
        'Portafolio GaLa': retorno_port,
        'Benchmark':       retorno_bench,
    })
    anuales = df.resample('YE').apply(lambda x: (1 + x).prod() - 1) * 100
    anuales.index = anuales.index.year
    return anuales
