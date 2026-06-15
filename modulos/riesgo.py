import numpy as np
import pandas as pd
from scipy import stats

def calcular_var_cvar(retorno_portafolio_diario: pd.Series, capital: float):
    """VaR y CVaR histórico y paramétrico."""

    retornos_limpios = retorno_portafolio_diario.dropna()
    if len(retornos_limpios) < 5:
        return {
            'VaR_95_hist':  0.0,
            'VaR_99_hist':  0.0,
            'VaR_95_param': 0.0,
            'VaR_99_param': 0.0,
            'CVaR_95':      0.0,
            'CVaR_99':      0.0,
            'capital':      capital,
        }
    # ─────────────────────────────────────────────────────

    # Histórico
    VaR_95_hist = np.percentile(retornos_limpios, 5)
    VaR_99_hist = np.percentile(retornos_limpios, 1)

    # Paramétrico (asume normalidad)
    mu  = retornos_limpios.mean()
    sig = retornos_limpios.std()
    VaR_95_param = stats.norm.ppf(0.05, mu, sig)
    VaR_99_param = stats.norm.ppf(0.01, mu, sig)

    # CVaR (Expected Shortfall)
    CVaR_95 = retornos_limpios[retornos_limpios <= VaR_95_hist].mean()
    CVaR_99 = retornos_limpios[retornos_limpios <= VaR_99_hist].mean()

    return {
        'VaR_95_hist':  VaR_95_hist,
        'VaR_99_hist':  VaR_99_hist,
        'VaR_95_param': VaR_95_param,
        'VaR_99_param': VaR_99_param,
        'CVaR_95':      CVaR_95,
        'CVaR_99':      CVaR_99,
        'capital':      capital,
    }


def calcular_drawdown(retornos: pd.Series):
    """Maximum Drawdown + fechas + duración."""
    acumulado     = (1 + retornos).cumprod()
    pico_rodante  = acumulado.cummax()
    drawdown_serie = (acumulado - pico_rodante) / pico_rodante
    max_dd        = drawdown_serie.min()
    fin_dd        = drawdown_serie.idxmin()
    inicio_dd     = acumulado[:fin_dd].idxmax()
    duracion      = (fin_dd - inicio_dd).days
    return drawdown_serie, max_dd, inicio_dd, fin_dd, duracion


def calcular_sortino(
    retorno_portafolio_diario: pd.Series,
    rendimiento_anual: float,
    tasa_rf: float
):
    """
    Sortino Ratio con MAR = tasa libre de riesgo diaria.
    Fórmula estándar CFA/actuarial:
    Sortino = (Retorno Anual - MAR) / Desviación Downside Anualizada
    """
    mar_diario = tasa_rf / 252

    # Solo días donde el retorno cayó por debajo del MAR
    retornos_bajo_mar = retorno_portafolio_diario - mar_diario
    retornos_negativos = retornos_bajo_mar[retornos_bajo_mar < 0]

    # Desviación downside anualizada
    desviacion_down = np.sqrt(np.mean(retornos_negativos ** 2)) * np.sqrt(252)

    sortino = (rendimiento_anual - tasa_rf) / desviacion_down if desviacion_down != 0 else np.nan

    return sortino, desviacion_down


def calcular_stress_test(pesos, tickers, capital_riesgo, retornos_diarios, es_riesgo=None):
    """
    Evalúa el impacto de crisis históricas en el portafolio,
    inmunizando los activos de renta fija (es_riesgo = 0.0).
    """
    import pandas as pd
    import numpy as np

    # Si no se define es_riesgo, asumimos que todos los activos son de riesgo (1.0)
    if es_riesgo is None:
        es_riesgo = np.ones(len(tickers))

    escenarios = {
        "COVID Crash (Feb-Mar 2020)": ("2020-02-19", "2020-03-23"),
        "Bear Market 2022": ("2022-01-03", "2022-10-12"),
        "Inflación & Subida Tasas 2022": ("2022-08-16", "2022-09-30"),
        "Corrección COVID Rebote": ("2020-09-02", "2020-09-23")
    }

    resultados = []
    
    for nombre, (inicio, fin) in escenarios.items():
        try:
            # Filtramos los retornos en la ventana de la crisis
            ventana = retornos_diarios.loc[inicio:fin]
            if ventana.empty:
                continue
            
            # Calculamos la caída acumulada de cada activo en ese periodo
            caida_activos = (1 + ventana).prod() - 1
            
            # ── LA INMUNIZACIÓN ──
            # Multiplicamos la caída por el vector de riesgo. 
            # Si un activo es renta fija (0.0), su caída se vuelve 0%.
            caida_inmunizada = caida_activos * es_riesgo
            
            # Calculamos la pérdida ponderada del portafolio completo
            caida_portafolio = np.sum(pesos * caida_inmunizada)
            
            impacto_dinero = capital_riesgo * caida_portafolio
            
            resultados.append({
                "Escenario": nombre,
                "Pérdida (%)": caida_portafolio * 100,
                "Pérdida Estimada (USD)": impacto_dinero
            })
        except Exception:
            continue
            
    return pd.DataFrame(resultados) if resultados else pd.DataFrame()


def calcular_correlacion_rolling(retornos_diarios: pd.DataFrame, ventana: int = 60):
    """Correlación dinámica rolling entre pares clave con filtro de ruido (NaN)."""
    pares = {}
    cols  = retornos_diarios.columns.tolist()

    if 'BTC-USD' in cols and 'SPY' in cols:
        pares['BTC-USD vs SPY'] = retornos_diarios['BTC-USD'].rolling(ventana).corr(retornos_diarios['SPY']).dropna()
        
    if 'QQQ' in cols and 'TLT' in cols:
        pares['QQQ vs TLT']     = retornos_diarios['QQQ'].rolling(ventana).corr(retornos_diarios['TLT']).dropna()

    return pares
