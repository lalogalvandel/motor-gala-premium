import numpy as np
import pandas as pd
from scipy import stats

def calcular_var_cvar(retorno_portafolio_diario: pd.Series, capital: float):
    """VaR y CVaR histórico y paramétrico."""

    # Histórico
    VaR_95_hist = np.percentile(retorno_portafolio_diario, 5)
    VaR_99_hist = np.percentile(retorno_portafolio_diario, 1)

    # Paramétrico (asume normalidad)
    mu  = retorno_portafolio_diario.mean()
    sig = retorno_portafolio_diario.std()
    VaR_95_param = stats.norm.ppf(0.05, mu, sig)
    VaR_99_param = stats.norm.ppf(0.01, mu, sig)

    # CVaR (Expected Shortfall)
    CVaR_95 = retorno_portafolio_diario[retorno_portafolio_diario <= VaR_95_hist].mean()
    CVaR_99 = retorno_portafolio_diario[retorno_portafolio_diario <= VaR_99_hist].mean()

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


def calcular_stress_test(
    pesos_optimos: np.ndarray,
    tickers: list,
    capital: float,
    retornos_diarios: pd.DataFrame
) -> pd.DataFrame:
    """
    Stress test con períodos históricos reales.
    Calcula el retorno real del portafolio en cada ventana de crisis.
    """
    periodos = {
        'COVID Crash (Feb–Mar 2020)':   ('2020-02-19', '2020-03-23'),
        'Bear Market 2022':             ('2022-01-03', '2022-10-12'),
        'Crisis Financiera 2008':       ('2008-09-01', '2009-03-09'),
        'Inflación & Subida Tasas 2022':('2022-03-01', '2022-06-30'),
        'Corrección COVID Rebote':      ('2020-09-02', '2020-09-23'),
    }

    resultados = []
    for escenario, (fecha_ini, fecha_fin) in periodos.items():
        try:
            # Filtra solo los tickers disponibles en retornos_diarios
            tickers_disp = [t for t in tickers if t in retornos_diarios.columns]
            pesos_disp   = np.array([
                pesos_optimos[tickers.index(t)] for t in tickers_disp
            ])
            pesos_disp  /= pesos_disp.sum()  # renormaliza

            ventana = retornos_diarios[tickers_disp].loc[fecha_ini:fecha_fin]

            if ventana.empty:
                continue

            retorno_periodo = (
                (1 + ventana @ pesos_disp).prod() - 1
            )

            resultados.append({
                'Escenario':     escenario,
                'Pérdida (%)':   round(retorno_periodo * 100, 2),
                'Pérdida (USD)': round(retorno_periodo * capital, 0)
            })
        except Exception:
            continue

    return pd.DataFrame(resultados)


def calcular_correlacion_rolling(retornos_diarios: pd.DataFrame, ventana: int = 60):
    """Correlación dinámica rolling entre pares clave con filtro de ruido (NaN)."""
    pares = {}
    cols  = retornos_diarios.columns.tolist()

    if 'BTC-USD' in cols and 'SPY' in cols:
        pares['BTC-USD vs SPY'] = retornos_diarios['BTC-USD'].rolling(ventana).corr(retornos_diarios['SPY']).dropna()
        
    if 'QQQ' in cols and 'TLT' in cols:
        pares['QQQ vs TLT']     = retornos_diarios['QQQ'].rolling(ventana).corr(retornos_diarios['TLT']).dropna()

    return pares