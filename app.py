import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from modulos.datos       import cargar_datos, calcular_retornos, obtener_tasa_referencia_banxico
from modulos.reporte     import generar_reporte
from modulos.markowitz   import simular_portafolios, optimizar_sharpe_slsqp
from modulos.montecarlo  import simular_capital
from modulos.screening   import UNIVERSOS, descargar_fundamentales_paralelo, filtrar_candidatos, clustering_activos
from modulos.backtesting import calcular_backtest_walk_forward, calcular_metricas_backtest, calcular_retornos_anuales
from modulos.riesgo      import calcular_var_cvar, calcular_drawdown, calcular_sortino, calcular_stress_test, calcular_correlacion_rolling
from modulos.regimenes   import entrenar_modelo_markov

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motor GaLa | Quant Dashboard",
    page_icon="",
    layout="wide"
)

st.title("Motor Cuantitativo GaLa")
st.markdown("*Sistema Institucional de Gestión de Capital y Análisis de Riesgo*")
st.markdown("---")

# ── Inicialización del estado de sesión ───────────────────────────────────────
if "optimizado" not in st.session_state:
    st.session_state.optimizado   = False
    st.session_state.pesos_opt    = None
    st.session_state.ret_opt      = None
    st.session_state.vol_opt      = None
    st.session_state.sharpe_opt   = None
    st.session_state.resultados   = None
    st.session_state.df_regimenes = None

# ── Tasa de referencia Banxico ─────────────────────────────────────────────────
with st.sidebar:
    with st.spinner("Consultando Banco de México..."):
        tasa_actual_banxico = obtener_tasa_referencia_banxico()
        tasa_rf = tasa_actual_banxico
    st.metric(label="Tasa de Referencia Banxico", value=f"{tasa_actual_banxico * 100:.2f}%")

margen_sugerido = float(round(tasa_actual_banxico * 100, 1))

# ── Panel lateral: Módulo 1 — Análisis Fundamental ────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("1. Análisis Fundamental")
usar_screening = st.sidebar.toggle("Activar selección algorítmica de activos", value=False)

if usar_screening:
    with st.sidebar.form("screening_form"):
        universo_sel = st.selectbox("Universo de análisis", list(UNIVERSOS.keys()))
        min_cap      = st.slider("Capitalización mínima (B USD)", 1.0, 100.0, 10.0, step=1.0)
        min_margin   = st.slider(
            "Margen de beneficio mínimo (%)", 0.0, 30.0, margen_sugerido, step=1.0,
            help=f"Referencia Banxico: {margen_sugerido}%"
        )
        max_pe       = st.slider("P/E máximo", 10.0, 100.0, 50.0, step=5.0)
        n_clusters   = st.slider("Grupos de diversificación (K-Means)", 2, 8, 4)
        ejecutar_scr = st.form_submit_button("Ejecutar análisis fundamental", width='stretch')
else:
    ejecutar_scr = False

# ── Panel lateral: Módulo 2 — Optimización ────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("2. Parámetros de Optimización")

if usar_screening and "tickers_screening" in st.session_state:
    tickers_default = st.session_state["tickers_screening"]
else:
    tickers_default = "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"

with st.sidebar.form("optim_form"):
    tickers_input = st.text_area("Activos a optimizar", value=tickers_default, height=70)
    fecha_inicio  = st.date_input("Fecha de inicio", value=pd.Timestamp("2020-01-01"))
    fecha_fin     = st.date_input("Fecha de cierre", value=pd.Timestamp("2026-05-08"))

    st.markdown("---")
    st.subheader("Restricciones de concentración")
    peso_max         = st.slider("Exposición máxima por activo (%)", 10, 100, 40) / 100
    peso_min         = st.slider("Exposición mínima por activo (%)", 0, 10, 2) / 100
    comision_broker  = st.number_input("Comisión operativa (%)", value=0.15, step=0.05) / 100

    st.markdown("---")
    st.subheader("Proyección de capital")
    capital_inicial       = st.number_input("Capital inicial (MXN)", min_value=0, value=100_000, step=10_000)
    frecuencia_aportacion = st.selectbox("Frecuencia de aportación", ["Mensual", "Trimestral", "Anual"], index=2)
    aportacion_mensual    = st.number_input("Aportación periódica (MXN)", min_value=0, value=100_000, step=10_000)
    horizonte_años        = st.slider("Horizonte de inversión (años)", min_value=1, max_value=40, value=10)
    num_sims              = st.slider("Simulaciones Monte Carlo", 500, 5000, 2000, step=500)

    ejecutar = st.form_submit_button("Ejecutar optimización", width='stretch')

# ── Funciones con caché ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=86400)
def cached_descargar_fundamentales(tickers):
    return descargar_fundamentales_paralelo(tickers, max_workers=10)

@st.cache_data(show_spinner=False, ttl=3600)
def obtener_datos(tickers_key: str, inicio: str, fin: str):
    tickers_list = [t.strip() for t in tickers_key.split(",")]
    datos = cargar_datos(tickers_list, inicio, fin)
    retornos_diarios, retornos_anuales, matriz_cov = calcular_retornos(datos)
    return datos, retornos_diarios, retornos_anuales, matriz_cov

@st.cache_data(show_spinner=False)
def cached_var_cvar(_retorno_port_diario, capital_riesgo):
    return calcular_var_cvar(_retorno_port_diario, capital_riesgo)

@st.cache_data(show_spinner=False)
def cached_drawdown(_retorno_port_diario):
    return calcular_drawdown(_retorno_port_diario)

@st.cache_data(show_spinner=False)
def cached_sortino(_retorno_port_diario, ret_opt, tasa_rf):
    return calcular_sortino(_retorno_port_diario, ret_opt, tasa_rf)

@st.cache_data(show_spinner=False)
def cached_stress_test(pesos_opt, tickers, capital_riesgo, _retornos_diarios):
    return calcular_stress_test(pesos_opt, tickers, capital_riesgo, _retornos_diarios)

@st.cache_data(show_spinner=False)
def cached_metricas_backtest(_retorno_port, _retorno_bench, tasa_rf, _equity_port, _equity_bench):
    return calcular_metricas_backtest(_retorno_port, _retorno_bench, tasa_rf, _equity_port, _equity_bench)

@st.cache_data(show_spinner=False)
def cached_retornos_anuales(_retorno_port, _retorno_bench):
    return calcular_retornos_anuales(_retorno_port, _retorno_bench)

# ── Fase 1: Análisis fundamental y clustering ──────────────────────────────────
df_mejores = None

if usar_screening and ejecutar_scr:
    st.header("Análisis Fundamental — Selección de Activos")
    seleccion = UNIVERSOS[universo_sel]
    tickers_universo = seleccion() if callable(seleccion) else seleccion

    with st.spinner(f"Procesando {len(tickers_universo)} instrumentos del universo seleccionado..."):
        df_fund = cached_descargar_fundamentales(tuple(tickers_universo))

        if df_fund.empty:
            st.error("No fue posible obtener datos de Yahoo Finance. Intente nuevamente en unos instantes.")
        else:
            df_filtrado = filtrar_candidatos(
                df_fund,
                min_market_cap=min_cap,
                min_profit_margin=min_margin,
                max_pe=max_pe
            )

            if len(df_filtrado) < 2:
                st.warning(
                    f"Solo {len(df_filtrado)} de {len(df_fund)} instrumentos superaron los filtros. "
                    "Considere flexibilizar los criterios de selección."
                )
            else:
                df_clusterizado, df_mejores = clustering_activos(df_filtrado, n_clusters)
                st.session_state["df_screening"] = df_mejores

                st.success(
                    f"Universo analizado: {len(df_fund)} instrumentos  |  "
                    f"Seleccionados tras filtro: {len(df_filtrado)}  |  "
                    f"Representantes por cluster: {len(df_mejores)}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Instrumentos que superaron el filtro fundamental**")
                    st.dataframe(
                        df_clusterizado.sort_values("Profit Margin %", ascending=False),
                        height=300,
                        width='stretch'
                    )
                with col2:
                    st.markdown("**Selección óptima por cluster (K-Means)**")
                    st.dataframe(
                        df_mejores[["Ticker", "Nombre", "Sector", "Cluster",
                                    "Market Cap (B)", "P/E Ratio", "Profit Margin %"]],
                        height=300,
                        width='stretch'
                    )

                tickers_sugeridos = ", ".join(df_mejores["Ticker"].tolist()) + ", TLT, GLD"
                st.session_state["tickers_screening"] = tickers_sugeridos
                st.info(
                    f"Cartera sugerida para optimización: **{tickers_sugeridos}**  "
                    "— Confirme los activos y ejecute la optimización desde el panel izquierdo."
                )

    st.stop()

# ── Freno de emergencia ────────────────────────────────────────────────────────
if not ejecutar and not st.session_state.optimizado:
    st.info(
        "Configure los parámetros en el panel izquierdo y ejecute la optimización para iniciar el análisis."
    )
    st.stop()

# ── Fase 2: Descarga de históricos ────────────────────────────────────────────
if ejecutar:
    st.session_state["tickers_procesar"] = tickers_input

tickers_finales = st.session_state.get("tickers_procesar", tickers_input)

try:
    with st.spinner("Descargando series históricas de precios..."):
        datos, retornos_diarios, retornos_anuales, matriz_cov = obtener_datos(
            tickers_finales, str(fecha_inicio), str(fecha_fin)
        )
        tickers = retornos_diarios.columns.tolist()
except Exception as e:
    st.error(f"Error al descargar históricos. Verifique la conexión y los tickers ingresados. Detalle: {e}")
    st.stop()

# ── Fase 3: Optimización y detección de regímenes ─────────────────────────────
if ejecutar:
    with st.spinner("Ejecutando optimización y análisis de regímenes de mercado..."):
        # Detección de regímenes (HMM)
        st.session_state.df_regimenes = entrenar_modelo_markov(datos)

        # Glide path actuarial
        REFUGIOS = {"TLT", "IEF", "SHY", "BND", "AGG", "BIL", "GLD", "IAU", "USDC-USD", "CASH"}
        es_riesgo = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in tickers])
        num_refugios = np.sum(es_riesgo == 0.0)
        peso_max_refugios = num_refugios * peso_max
        target_riesgo = min(1.0, max(0.20, horizonte_años / 15.0))
        factor_glide_path = max(target_riesgo, max(0.0, 1.0 - peso_max_refugios))

        # Simulación Monte Carlo de portafolios (frontera eficiente)
        resultados, pesos_guardados = simular_portafolios(
            retornos_anuales, matriz_cov, tasa_rf, num_portafolios=num_sims
        )

        # Optimización precisa con SLSQP
        pesos_opt = optimizar_sharpe_slsqp(
            retornos_anuales, matriz_cov, tasa_rf,
            peso_min=peso_min, peso_max=peso_max,
            max_riesgo_total=factor_glide_path,
            es_riesgo=es_riesgo
        )

        ret_opt    = float(np.sum(pesos_opt * retornos_anuales))
        vol_opt    = float(np.sqrt(np.dot(pesos_opt.T, np.dot(matriz_cov, pesos_opt))))
        sharpe_opt = float((ret_opt - tasa_rf) / vol_opt)

        st.session_state.optimizado  = True
        st.session_state.pesos_opt   = pesos_opt
        st.session_state.ret_opt     = ret_opt
        st.session_state.vol_opt     = vol_opt
        st.session_state.sharpe_opt  = sharpe_opt
        st.session_state.resultados  = resultados

# Recuperar variables del estado de sesión
res        = st.session_state.resultados
pesos_opt  = st.session_state.pesos_opt
ret_opt    = st.session_state.ret_opt
vol_opt    = st.session_state.vol_opt
sharpe_opt = st.session_state.sharpe_opt

# ── Sección 1: Precios históricos ──────────────────────────────────────────────
st.subheader("Precios de Cierre Históricos")

# El interruptor que salva la memoria RAM
if st.toggle("Mostrar gráfica de precios (Consume recursos visuales)"):
    with st.spinner("Renderizando histórico..."):
        st.line_chart(datos)
else:
    st.caption("Activa el interruptor para visualizar la evolución del precio de los activos.")

# ── Sección 2: Frontera eficiente de Markowitz ────────────────────────────────
st.markdown("---")
st.subheader("Frontera Eficiente — Markowitz")

c1, c2, c3 = st.columns(3)
c1.metric("Retorno Esperado Anual", f"{ret_opt*100:.2f}%")
c2.metric("Volatilidad Anual",      f"{vol_opt*100:.2f}%")
c3.metric("Ratio de Sharpe",        f"{sharpe_opt:.4f}")

fig_markowitz = go.Figure()
fig_markowitz.add_trace(go.Scatter(
    x=res[1] * 100, y=res[0] * 100, mode="markers",
    marker=dict(color=res[2], colorscale="Viridis", size=4, opacity=0.5,
                colorbar=dict(title="Sharpe")),
    name="Portafolios simulados",
    hovertemplate="Volatilidad: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra></extra>"
))
fig_markowitz.add_trace(go.Scatter(
    x=[vol_opt * 100], y=[ret_opt * 100], mode="markers",
    marker=dict(symbol="star", size=20, color="red"),
    name="Óptimo Max Sharpe",
    hovertemplate=f"Sharpe: {sharpe_opt:.4f}<extra></extra>"
))
fig_markowitz.update_layout(
    template="plotly_dark",
    xaxis_title="Volatilidad Anual (%)",
    yaxis_title="Retorno Anual (%)",
    height=480,
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig_markowitz, width='stretch', key="chart_markowitz")

st.subheader("Distribución Óptima del Capital")
df_pesos = pd.DataFrame({
    "Activo":   tickers,
    "Peso (%)": (pesos_opt * 100).round(2)
}).sort_values("Peso (%)", ascending=False)
st.dataframe(df_pesos, width='stretch')

# ── Sección 3: Backtesting Walk-Forward ───────────────────────────────────────
st.markdown("---")
st.subheader("Backtesting Dinámico — Walk-Forward")
st.caption(
    "Metodología institucional: los pesos se recalculan cada trimestre utilizando "
    "exclusivamente datos disponibles a la fecha de decisión, sin acceso al futuro. "
    "Los resultados son netos de comisiones operativas."
)

@st.cache_data(show_spinner=False)
def correr_motor_backtest(datos, rf, capital, p_min, p_max, max_riesgo,
                          es_riesgo_arr, _df_oraculo, comision):
    return calcular_backtest_walk_forward(
        retornos_diarios=datos,
        funcion_optimizador=optimizar_sharpe_slsqp,
        tasa_rf=rf,
        peso_min=p_min,
        peso_max=p_max,
        max_riesgo_total=max_riesgo,
        es_riesgo=es_riesgo_arr,
        df_regimenes=_df_oraculo,
        comision_broker=comision,
        capital_inicial=capital
    )

with st.spinner("Procesando backtesting walk-forward..."):
    REFUGIOS = {"TLT", "IEF", "SHY", "BND", "AGG", "BIL", "GLD", "IAU", "USDC-USD", "CASH"}
    es_riesgo_arr = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in tickers])
    num_refugios  = np.sum(es_riesgo_arr == 0.0)
    factor_glide  = max(
        min(1.0, max(0.20, horizonte_años / 15.0)),
        max(0.0, 1.0 - num_refugios * peso_max)
    )

    df_equity, benchmark_ticker, retorno_port, retorno_bench = correr_motor_backtest(
        retornos_diarios, tasa_rf, capital_inicial,
        peso_min, peso_max, factor_glide, es_riesgo_arr,
        st.session_state.df_regimenes,
        comision_broker
    )

metricas_bt = cached_metricas_backtest(
    retorno_port, retorno_bench, tasa_rf,
    df_equity["Portafolio GaLa (Dinámico)"],
    df_equity[f"Benchmark ({benchmark_ticker})"]
)

# Tabla comparativa — construcción correcta con columnas separadas por fila
st.markdown("**Análisis comparativo de rendimiento**")

comparativas = [
    ("CAGR",          f"{metricas_bt['cagr_port']*100:.2f}%",  f"{metricas_bt['cagr_bench']*100:.2f}%"),
    ("Volatilidad",   f"{metricas_bt['vol_port']*100:.2f}%",   f"{metricas_bt['vol_bench']*100:.2f}%"),
    ("Sharpe",        f"{metricas_bt['sharpe_port']:.4f}",      f"{metricas_bt['sharpe_bench']:.4f}"),
    ("Sortino",       f"{metricas_bt['sortino_port']:.4f}",     f"{metricas_bt['sortino_bench']:.4f}"),
    ("Max Drawdown",  f"{metricas_bt['mdd_port']*100:.2f}%",   f"{metricas_bt['mdd_bench']*100:.2f}%"),
    ("Calmar",        f"{metricas_bt['calmar_port']:.4f}",      f"{metricas_bt['calmar_bench']:.4f}"),
]

header1, header2, header3 = st.columns(3)
header1.markdown("**Métrica**")
header2.markdown("**Motor GaLa**")
header3.markdown(f"**{benchmark_ticker}**")
st.markdown("---")

for metrica, val_port, val_bench in comparativas:
    col1, col2, col3 = st.columns(3)
    col1.write(metrica)
    col2.write(val_port)
    col3.write(val_bench)

st.markdown("")
c1, c2 = st.columns(2)
c1.metric("Alpha (Jensen)",    f"{metricas_bt['alpha']*100:.2f}%",
          help="Retorno excedente respecto al modelo CAPM")
c2.metric("Beta vs Benchmark", f"{metricas_bt['beta']:.4f}",
          help="Sensibilidad del portafolio ante movimientos del benchmark")

# Curva de equity
fig_bt = go.Figure()
fig_bt.add_trace(go.Scatter(
    x=df_equity.index,
    y=df_equity["Portafolio GaLa (Dinámico)"],
    mode="lines",
    line=dict(width=2.5, color="#4488ff"),
    name="Motor GaLa (Dinámico)"
))
fig_bt.add_trace(go.Scatter(
    x=df_equity.index,
    y=df_equity[f"Benchmark ({benchmark_ticker})"],
    mode="lines",
    line=dict(width=1.5, color="rgba(200,200,200,0.6)", dash="dot"),
    name=benchmark_ticker
))
fig_bt.update_layout(
    template="plotly_dark",
    xaxis_title="Fecha",
    yaxis_title="Capital (USD)",
    height=420,
    legend=dict(x=0.01, y=0.99),
    hovermode="x unified"
)
st.plotly_chart(fig_bt, width='stretch', key="chart_bt")

# Retornos anuales
st.markdown("**Retornos anuales vs benchmark**")
anuales   = cached_retornos_anuales(retorno_port, retorno_bench)
fig_anuales = go.Figure()
fig_anuales.add_trace(go.Bar(
    x=anuales.index.astype(str),
    y=anuales["Portafolio GaLa"],
    name="Motor GaLa",
    marker_color="#4488ff"
))
fig_anuales.add_trace(go.Bar(
    x=anuales.index.astype(str),
    y=anuales["Benchmark"],
    name=benchmark_ticker,
    marker_color="rgba(200,200,200,0.5)"
))
fig_anuales.add_hline(y=0, line_color="white", line_width=0.5)
fig_anuales.update_layout(
    template="plotly_dark",
    barmode="group",
    xaxis_title="Año",
    yaxis_title="Retorno (%)",
    height=360,
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig_anuales, width='stretch', key="chart_anuales")

# ── Sección 4: Proyección Monte Carlo ─────────────────────────────────────────
st.markdown("---")
st.subheader("Proyección de Capital — Monte Carlo")

retorno_port_mc = retornos_diarios @ pesos_opt

escenarios, p5, p50, p95, benchmark_fijo, df_t = simular_capital(
    capital_inicial      = capital_inicial,
    aportacion_periodica = aportacion_mensual,
    rendimiento_anual    = ret_opt,
    volatilidad_anual    = vol_opt,
    meses                = horizonte_años * 12,
    frecuencia_aportacion= frecuencia_aportacion,
    tasa_benchmark       = tasa_actual_banxico,
    num_simulaciones     = 1000,
    retornos_diarios     = retorno_port_mc
)

st.caption(
    f"Modelo calibrado con distribución t de Student — "
    f"grados de libertad: {df_t:.2f} "
    f"({'cola pesada severa' if df_t < 5 else 'cola pesada moderada' if df_t < 10 else 'aproximación normal'})"
)

fig_mc = go.Figure()
for i in range(min(20, escenarios.shape[1])):
    fig_mc.add_trace(go.Scatter(
        y=escenarios[:, i], mode="lines",
        line=dict(width=1, color="rgba(0, 150, 255, 0.08)"),
        showlegend=False, hoverinfo="skip"
    ))

fig_mc.add_trace(go.Scatter(
    y=p50, mode="lines",
    line=dict(width=3, color="#17C37B"),
    name="Motor GaLa — Escenario base (P50)"
))
fig_mc.add_trace(go.Scatter(
    y=p95, mode="lines",
    line=dict(width=2, color="rgba(23,195,123,0.5)", dash="dot"),
    name="Escenario favorable (P95)"
))
fig_mc.add_trace(go.Scatter(
    y=p5, mode="lines",
    line=dict(width=2, color="#FF4B4B", dash="dot"),
    name="Escenario adverso (P5)"
))
fig_mc.add_trace(go.Scatter(
    y=benchmark_fijo, mode="lines",
    line=dict(width=3, color="gray", dash="dash"),
    name=f"Referencia tasa fija ({tasa_actual_banxico*100:.2f}%)"
))
fig_mc.update_layout(
    template="plotly_dark",
    xaxis_title="Meses",
    yaxis_title="Capital (MXN)",
    height=480,
    legend=dict(x=0.01, y=0.99)
)
st.plotly_chart(fig_mc, width='stretch', key="chart_mc")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Escenario adverso (P5)",     f"${p5[-1]:,.0f}")
c2.metric("Escenario base (P50)",       f"${p50[-1]:,.0f}")
c3.metric("Escenario favorable (P95)",  f"${p95[-1]:,.0f}")
c4.metric("Referencia tasa fija",       f"${benchmark_fijo[-1]:,.0f}",
          delta=f"${p50[-1] - benchmark_fijo[-1]:,.0f} diferencial vs base")

# ── Sección 5: Métricas de riesgo institucional ────────────────────────────────
st.markdown("---")
st.subheader("Análisis de Riesgo Institucional")

capital_riesgo = st.number_input(
    "Capital de referencia para cuantificación de pérdidas (USD)",
    value=200_000, step=10_000
)
st.caption("Las pérdidas monetarias se expresan en USD.")

retorno_port_diario = retornos_diarios @ pesos_opt

# VaR y CVaR
st.markdown("#### Value at Risk (VaR) y Expected Shortfall (CVaR)")
var_cvar = cached_var_cvar(retorno_port_diario, capital_riesgo)

c1, c2, c3, c4 = st.columns(4)
c1.metric("VaR 95% Histórico", f"{var_cvar['VaR_95_hist']*100:.2f}%",
          f"-${abs(var_cvar['VaR_95_hist'])*capital_riesgo:,.0f} USD")
c2.metric("VaR 99% Histórico", f"{var_cvar['VaR_99_hist']*100:.2f}%",
          f"-${abs(var_cvar['VaR_99_hist'])*capital_riesgo:,.0f} USD")
c3.metric("CVaR 95%",          f"{var_cvar['CVaR_95']*100:.2f}%",
          f"-${abs(var_cvar['CVaR_95'])*capital_riesgo:,.0f} USD")
c4.metric("CVaR 99%",          f"{var_cvar['CVaR_99']*100:.2f}%",
          f"-${abs(var_cvar['CVaR_99'])*capital_riesgo:,.0f} USD")

fig_var = go.Figure()
fig_var.add_trace(go.Histogram(
    x=retorno_port_diario * 100, nbinsx=80,
    marker_color="rgba(68,136,255,0.7)", name="Distribución de retornos diarios"
))
fig_var.add_vline(x=var_cvar["VaR_95_hist"]*100, line_color="red",    line_dash="dash",  annotation_text="VaR 95%")
fig_var.add_vline(x=var_cvar["CVaR_95"]*100,     line_color="orange", line_dash="dash",  annotation_text="CVaR 95%")
fig_var.add_vline(x=var_cvar["VaR_99_hist"]*100, line_color="magenta",line_dash="dot",   annotation_text="VaR 99%")
fig_var.update_layout(
    template="plotly_dark", height=380,
    xaxis_title="Retorno Diario (%)", yaxis_title="Frecuencia"
)
st.plotly_chart(fig_var, width='stretch', key="chart_var")

# Maximum Drawdown
st.markdown("#### Maximum Drawdown")
dd_serie, max_dd, inicio_dd, fin_dd, duracion_dd = cached_drawdown(retorno_port_diario)

c1, c2, c3 = st.columns(3)
c1.metric("Maximum Drawdown", f"{max_dd*100:.2f}%",
          f"-${abs(max_dd)*capital_riesgo:,.0f} USD")
c2.metric("Duración",         f"{duracion_dd} días ({duracion_dd//30} meses)")
c3.metric("Período",          f"{inicio_dd.strftime('%b %Y')} — {fin_dd.strftime('%b %Y')}")

fig_dd = go.Figure()
fig_dd.add_trace(go.Scatter(
    x=dd_serie.index, y=dd_serie * 100,
    fill="tozeroy", fillcolor="rgba(255,68,68,0.3)",
    line=dict(color="red", width=1), name="Drawdown"
))
fig_dd.add_hline(
    y=max_dd*100, line_color="gold", line_dash="dash",
    annotation_text=f"Max DD: {max_dd*100:.2f}%"
)
fig_dd.update_layout(
    template="plotly_dark", height=350,
    xaxis_title="Fecha", yaxis_title="Drawdown (%)"
)
st.plotly_chart(fig_dd, width='stretch', key="chart_dd")

# Sortino vs Sharpe
st.markdown("#### Ratio de Sortino vs Sharpe")
sortino, desv_down = cached_sortino(retorno_port_diario, ret_opt, tasa_rf)
c1, c2, c3 = st.columns(3)
c1.metric("Ratio de Sharpe",          f"{sharpe_opt:.4f}")
c2.metric("Ratio de Sortino",         f"{sortino:.4f}")
c3.metric("Desviación downside anual",f"{desv_down*100:.2f}%")

# Stress testing
st.markdown("#### Stress Testing — Escenarios Históricos")
df_stress = cached_stress_test(pesos_opt, tickers, capital_riesgo, retornos_diarios)

fig_stress = go.Figure(go.Bar(
    x=df_stress["Pérdida (%)"],
    y=df_stress["Escenario"],
    orientation="h",
    marker_color=[
        "red" if p < -15 else "orange" if p < -8 else "gold"
        for p in df_stress["Pérdida (%)"]
    ],
    text=[f"{p:.1f}%" for p in df_stress["Pérdida (%)"]],
    textposition="outside"
))
fig_stress.update_layout(
    template="plotly_dark", height=350,
    xaxis_title="Impacto en Capital (%)"
)
st.plotly_chart(fig_stress, width='stretch', key="chart_stress")
st.dataframe(df_stress, width='stretch')

# Correlación dinámica rolling
st.markdown("#### Correlación Dinámica Rolling — 60 días")
fig_corr    = None
pares_corr  = calcular_correlacion_rolling(retornos_diarios)

if pares_corr:
    fig_corr = go.Figure()
    colores_corr = ["gold", "rgba(68,136,255,0.9)"]
    for (nombre, serie), color in zip(pares_corr.items(), colores_corr):
        fig_corr.add_trace(go.Scatter(
            x=serie.index, y=serie, mode="lines",
            line=dict(width=1.5, color=color), name=nombre
        ))
    fig_corr.add_hline(y=0.6,  line_color="rgba(255,0,0,0.5)",  line_dash="dot",
                       annotation_text="Zona de riesgo de concentración")
    fig_corr.add_hline(y=0,    line_color="gray", line_dash="solid", line_width=0.5)
    fig_corr.add_hline(y=-0.6, line_color="rgba(0,255,0,0.5)", line_dash="dot",
                       annotation_text="Zona de cobertura efectiva")
    fig_corr.update_layout(
        template="plotly_dark", height=350,
        yaxis=dict(range=[-1.1, 1.1]),
        xaxis_title="Fecha", yaxis_title="Coeficiente de Pearson"
    )
    st.plotly_chart(fig_corr, width='stretch', key="chart_corr")
else:
    st.info(
        "Para visualizar la correlación dinámica, incluya los pares BTC-USD / SPY "
        f"o QQQ / TLT en el universo de análisis. "
        f"Tickers actuales: {retornos_diarios.columns.tolist()}"
    )

# ── Sección 6: Detección de regímenes de mercado (HMM) ────────────────────────
st.markdown("---")
st.subheader("Detección de Regímenes de Mercado — Modelo Oculto de Markov")
st.caption(
    "El modelo analiza la micro-volatilidad histórica para clasificar cada período "
    "en un régimen de mercado: normal o de tensión. Esta señal se incorpora al "
    "proceso de rebalanceo del backtesting walk-forward."
)

df_regimenes = st.session_state.get("df_regimenes", None)

if df_regimenes is not None:
    calma  = df_regimenes[df_regimenes["Regimen"] == 0]
    panico = df_regimenes[df_regimenes["Regimen"] == 1]

    fig_hmm = go.Figure()
    fig_hmm.add_trace(go.Scatter(
        x=calma.index, y=calma["Precio"], mode="markers",
        marker=dict(color="rgba(0, 255, 100, 0.6)", size=4),
        name="Régimen normal"
    ))
    fig_hmm.add_trace(go.Scatter(
        x=panico.index, y=panico["Precio"], mode="markers",
        marker=dict(color="rgba(255, 50, 50, 0.8)", size=6, symbol="x"),
        name="Régimen de tensión"
    ))
    fig_hmm.update_layout(
        template="plotly_dark", height=400,
        xaxis_title="Fecha", yaxis_title="Precio de referencia",
        legend=dict(x=0.01, y=0.99)
    )
    st.plotly_chart(fig_hmm, width='stretch', key="chart_hmm")

    pct_tension = (df_regimenes["Regimen"] == 1).mean() * 100
    c1, c2 = st.columns(2)
    c1.metric("Períodos en régimen normal",  f"{100 - pct_tension:.1f}%")
    c2.metric("Períodos en régimen de tensión", f"{pct_tension:.1f}%")
else:
    st.info("Ejecute la optimización para generar el análisis de regímenes.")

# ── Sección 7: Exportar reporte PDF ───────────────────────────────────────────
st.markdown("---")
st.subheader("Exportar Reporte Institucional")

if st.button("Generar reporte PDF", type="primary"):
    with st.spinner("Generando reporte..."):
        try:
            # df_mejores puede no existir si no se usó el screening
            screening_data = st.session_state.get("df_screening", None)

            pdf_bytes = generar_reporte(
                tickers=tickers, pesos_opt=pesos_opt,
                ret_opt=ret_opt, vol_opt=vol_opt,
                sharpe_opt=sharpe_opt, sortino=sortino,
                desv_down=desv_down, df_t=df_t,
                var_cvar=var_cvar, max_dd=max_dd,
                duracion_dd=duracion_dd, inicio_dd=inicio_dd,
                fin_dd=fin_dd, df_stress=df_stress,
                capital_riesgo=capital_riesgo,
                p5_final=p5[-1], p50_final=p50[-1], p95_final=p95[-1],
                horizonte_años=horizonte_años,
                capital_inicial=capital_inicial,
                aportacion_mensual=aportacion_mensual,
                metricas_bt=metricas_bt,
                benchmark_ticker=benchmark_ticker,
                df_screening=screening_data,
                fig_markowitz=fig_markowitz, fig_mc=fig_mc,
                fig_var=fig_var, fig_dd=fig_dd,
                fig_stress=fig_stress, fig_bt=fig_bt,
                fig_anuales=fig_anuales, fig_corr=fig_corr,
            )

            st.download_button(
                label     = "Descargar reporte PDF",
                data      = pdf_bytes,
                file_name = f"MotorGaLa_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime      = "application/pdf"
            )
            st.success("Reporte generado correctamente.")

        except Exception as e:
            st.error(f"Error al generar el reporte: {e}")
            st.exception(e)
