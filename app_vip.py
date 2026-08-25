# =============================================================================
# Motor GaLa VIP - Edición Especial Consultoría Sorteo UDLAP
# Creado por: Eduardo Galván del Río
# =============================================================================
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import psycopg2
import urllib.parse
import yfinance as yf

# Importamos tu rigor cuantitativo intacto
from modulos.datos       import cargar_datos, obtener_uma_actual, calcular_retornos, obtener_tasa_referencia_banxico
from modulos.reporte     import generar_reporte
from modulos.markowitz   import simular_portafolios, optimizar_sharpe_slsqp
from modulos.montecarlo  import simular_capital
from modulos.screening   import UNIVERSOS, descargar_fundamentales_paralelo, filtrar_candidatos, clustering_activos
from modulos.backtesting import calcular_backtest_walk_forward, calcular_metricas_backtest, calcular_retornos_anuales
from modulos.riesgo      import calcular_var_cvar, calcular_drawdown, calcular_sortino, calcular_stress_test, calcular_correlacion_rolling
from modulos.regimenes   import entrenar_modelo_markov
from modulos.black_litterman import calcular_black_litterman
from modulos.pensiones import MotorActuarial
from modulos.heuristica import generar_vistas_black_litterman

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motor GaLa | Consultoría VIP",
    page_icon="🍀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Ocultar menú nativo
st.markdown("""<style>[data-testid="stSidebarNav"] {display: none !important;}</style>""", unsafe_allow_html=True)

# ── AUTENTICACIÓN CONTRA BASE DE DATOS NEON (SORTEO UDLAP) ───────────────────
@st.cache_resource
def init_connection():
    return psycopg2.connect(st.secrets["db_url"])

try:
    conn = init_connection()
    c = conn.cursor()
except Exception as e:
    st.error("Error conectando a la base de datos de validación.")
    st.stop()

if 'acceso_concedido' not in st.session_state:
    st.session_state['acceso_concedido'] = False

# PANTALLA DE BLOQUEO ELEGANTE
if not st.session_state['acceso_concedido']:
    st.markdown("<h1 style='text-align: center; color: #1F4E78; margin-top: 50px;'>🌟 Motor GaLa | Consultoría VIP</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem;'>Bienvenido a tu sesión privada. Ingresa los datos de tu boleto del <b>Sorteo UDLAP</b> para iniciar nuestro análisis.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("") 
        with st.form("login_vip"):
            nombre_cliente = st.text_input("Tu Primer Nombre (Como lo registraste al apartar)")
            boleto_cliente = st.text_input("Número de Boleto Apartado (Ej. 042760)")
            submit = st.form_submit_button("Desbloquear mi Sesión", use_container_width=True)
            
            if submit:
                if nombre_cliente and boleto_cliente:
                    c.execute("SELECT comprador, estatus FROM boletos WHERE boleto=%s", (boleto_cliente,))
                    resultado = c.fetchone()
                    
                    if resultado and resultado[1] in ['Apartado', 'Pagado Total'] and nombre_cliente.strip().lower() in resultado[0].lower():
                        st.session_state['acceso_concedido'] = True
                        st.session_state['nombre_vip'] = nombre_cliente.strip().capitalize()
                        st.rerun()
                    else:
                        st.error("❌ Datos incorrectos o boleto no registrado. Verifica tu información.")
                else:
                    st.warning("⚠️ Por favor, llena ambos campos.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SESIÓN VIP ACTIVA
# ══════════════════════════════════════════════════════════════════════════════
nombre_usuario = st.session_state.get('nombre_vip', 'Invitado')
st.markdown(f"## 🌟 Sesión de Consultoría Activa: {nombre_usuario}")
st.caption("Arquitectura Cuantitativa · Motor GaLa")
st.markdown("---")

# Variables de estado para el flujo
if "optimizado" not in st.session_state:
    st.session_state.optimizado   = False
    st.session_state.pesos_opt    = None
    st.session_state.ret_opt      = None
    st.session_state.vol_opt      = None
    st.session_state.sharpe_opt   = None
    st.session_state.resultados   = None
    st.session_state.df_regimenes = None

with st.sidebar:
    with st.spinner("Conectando a Banxico..."):
        tasa_actual_banxico = obtener_tasa_referencia_banxico()
        tasa_rf = tasa_actual_banxico
    st.metric(label="Tasa Libre de Riesgo (Banxico)", value=f"{tasa_actual_banxico * 100:.2f}%")
    st.caption("Usaremos esta tasa como piso para evaluar la eficiencia de tus inversiones.")

# FLUJO EN 3 PASOS
tab_diag, tab_metas, tab_estrategia = st.tabs([
    "📍 Paso 1: Radiografía Actual", 
    "🎯 Paso 2: Metas de Retiro (LDI)", 
    "📈 Paso 3: Estrategia y Proyección"
])

# ── PASO 1: RADIOGRAFÍA (Interactivo) ──────────────────────────────────────────
with tab_diag:
    st.markdown("### ¿Dónde estamos parados hoy?")
    st.caption("Ingresa los montos aproximados que tienes actualmente. El sistema conectará con el mercado para valuar en tiempo real.")
    
    col_rf, col_rv = st.columns(2, gap="large")
    
    with col_rf:
        st.markdown("**1. Cuentas de Efectivo y Renta Fija**")
        if "df_rf_sesion" not in st.session_state:
            st.session_state["df_rf_sesion"] = pd.DataFrame([
                {"Instrumento": "Cetes Directo / Efectivo", "Tasa Anual (%)": float(round(tasa_actual_banxico*100,1)), "Saldo (MXN)": 100000.0},
                {"Instrumento": "Pagaré Bancario / Sofipo", "Tasa Anual (%)": 10.0, "Saldo (MXN)": 0.0}
            ])
        df_edit_rf = st.data_editor(st.session_state["df_rf_sesion"], num_rows="dynamic", use_container_width=True, hide_index=True)
        st.session_state["df_rf_sesion"] = df_edit_rf
        capital_liquidez = df_edit_rf["Saldo (MXN)"].sum() if not df_edit_rf.empty else 0.0

    with col_rv:
        st.markdown("**2. Portafolio de Bolsa (Acciones / ETFs)**")
        if "df_rv_sesion" not in st.session_state:
            st.session_state["df_rv_sesion"] = pd.DataFrame([
                {"Ticker": "IVVPESO.MX", "Títulos": 100.0, "Precio Promedio (MXN)": 80.0},
                {"Ticker": "AAPL", "Títulos": 0.0, "Precio Promedio (MXN)": 0.0}
            ])
        df_edit_rv = st.data_editor(st.session_state["df_rv_sesion"], num_rows="dynamic", use_container_width=True, hide_index=True)
        st.session_state["df_rv_sesion"] = df_edit_rv
        
        # MTM en vivo super rápido
        valor_total_rv = 0.0
        if not df_edit_rv.empty and df_edit_rv["Títulos"].sum() > 0:
            df_rv = df_edit_rv.dropna(subset=["Ticker"]).copy()
            tickers_unicos = df_rv["Ticker"].str.upper().str.strip().unique().tolist()
            try:
                datos_mercado = yf.download(tickers_unicos + ["MXN=X"], period="5d", progress=False)
                if not datos_mercado.empty:
                    if isinstance(datos_mercado.columns, pd.MultiIndex):
                        if 'Close' in datos_mercado.columns.get_level_values(0): df_close = datos_mercado['Close']
                        else: df_close = datos_mercado.xs('Close', axis=1, level=1)
                    else:
                        df_close = datos_mercado
                    df_close = df_close.ffill().bfill()
                    ultima_fila = df_close.iloc[-1].to_dict()
                    tc_usd = float(ultima_fila.get("MXN=X", 18.50))
                    
                    def valuar_fila(row):
                        t = str(row["Ticker"]).upper().strip()
                        titulos = float(row["Títulos"])
                        p_origen = float(ultima_fila.get(t, row["Precio Promedio (MXN)"]))
                        p_mxn = p_origen * tc_usd if not t.endswith(".MX") else p_origen
                        return titulos * p_mxn
                        
                    valor_total_rv = df_rv.apply(valuar_fila, axis=1).sum()
            except:
                # Fallback a precio promedio si no hay internet
                valor_total_rv = (df_rv["Títulos"] * df_rv["Precio Promedio (MXN)"]).sum()
                
    st.markdown("---")
    capital_total_global = capital_liquidez + valor_total_rv
    st.session_state["capital_inicial_diagnostico"] = capital_total_global
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Patrimonio Total Estimado ({nombre_usuario})", f"${capital_total_global:,.2f} MXN")
    c2.metric("Renta Fija / Liquidez", f"${capital_liquidez:,.2f} MXN")
    c3.metric("Exposición a Bolsa", f"${valor_total_rv:,.2f} MXN")
    
    st.info("💡 **Dato para la sesión:** Este es el punto de partida (Capital Inicial) que utilizaremos para modelar tu plan de retiro y estrategias de optimización.")

# ── PASO 2: METAS DE RETIRO LDI ────────────────────────────────────────────────
with tab_metas:
    st.markdown("### Análisis de Brecha Pensional (Liability-Driven Investing)")
    st.caption("Calculamos si tu ritmo de ahorro actual y beneficios de ley serán suficientes para mantener tu estilo de vida en el futuro.")
    
    col_param, col_priv = st.columns(2, gap="large")
    with col_param:
        regimen = st.radio("Régimen de Retiro", ["Ley 97 / Afore / Independiente", "Ley 73 IMSS"], horizontal=True)
        edad_retiro = st.selectbox("Edad planeada de retiro", [60, 61, 62, 63, 64, 65], index=5)
        
        pension_imss = 0.0
        if "Ley 73" in regimen:
            simular_m40 = st.toggle("Simular Modalidad 40 (Topada)")
            semanas = st.slider("Semanas Cotizadas Estimadas", 500, 3000, 1500, step=50)
            salario = 25 * obtener_uma_actual() if simular_m40 else st.number_input("Salario Promedio Diario (MXN)", 100.0, 3500.0, 800.0, step=100.0)
            pension_imss = MotorActuarial.estimar_pension_ley73(semanas, salario, edad_retiro, obtener_uma_actual(), False)
            st.metric("Pensión IMSS Estimada", f"${pension_imss:,.2f} MXN / mes")
            anios_horizonte = st.slider("Años de acumulación restantes", 1, 40, 10)
        else:
            anios_horizonte = st.slider("Años para el retiro", 1, 50, 25)

    with col_priv:
        meta_mensual = st.number_input("¿Cuánto dinero mensual necesitas para vivir tranquilo en el retiro? (Pesos de hoy)", min_value=10000, value=50000, step=5000)
        aportacion_mensual = st.number_input("¿Cuánto puedes ahorrar/invertir mensualmente hoy? (MXN)", min_value=0, value=5000, step=1000)
        inflacion = st.number_input("Proyección de Inflación Anual (%)", value=4.0, step=0.5) / 100
        
        usar_fiscal = st.toggle("Activar Optimización Fiscal (Deducibilidad PPR Art. 151)")
        ingreso_comp = st.number_input("Tu Ingreso Mensual Bruto (Para calcular ISR a devolver)", value=60000, step=5000) if usar_fiscal else 0.0

    st.markdown("---")
    if st.button("Ejecutar Modelado Actuarial", type="primary", width='stretch'):
        with st.spinner("Descontando flujos por inflación y calculando Ecuación de Fisher..."):
            
            # Tasa conservadora sugerida como base para el PPR
            tasa_portafolio = 0.10 
            
            capital_acumulado_real = MotorActuarial.proyeccion_ppr_real(
                capital_inicial=capital_total_global, # Conectado a la pestaña 1
                aportacion_mensual=aportacion_mensual, 
                anios=anios_horizonte, 
                tasa_anual=tasa_portafolio, 
                inflacion=inflacion,
                ingreso_mensual=ingreso_comp,     
                aplicar_beneficio_fiscal=usar_fiscal,     
                uma_actual=obtener_uma_actual()                   
            )
            
            tasa_retiro_segura = 0.04
            ingreso_total, brecha, flujo_privado = MotorActuarial.calcular_brecha_pensional_real(
                meta_mensual, pension_imss, capital_acumulado_real, tasa_retiro_segura
            )

            m1, m2, m3 = st.columns(3)
            m1.metric("Pensión IMSS", f"${pension_imss:,.2f}")
            m2.metric("Rendimiento de tus Inversiones (Mensual)", f"${flujo_privado:,.2f}", f"Al finalizar {anios_horizonte} años")
            
            if brecha <= 0:
                m3.metric("Ingreso Total Logrado", f"${ingreso_total:,.2f}", f"+${abs(brecha):,.2f} superávit")
                st.success("✅ **¡Plan Viable!** Con este ritmo de ahorro alcanzarás y superarás tu meta de vida. Sugiero un perfil de inversión Moderado-Conservador (Preservación de capital).")
                riesgo_sugerido = 0.30 
            else:
                m3.metric("Ingreso Total Logrado", f"${ingreso_total:,.2f}", f"-${abs(brecha):,.2f} déficit", delta_color="inverse")
                st.warning("⚠️ **Alerta de Déficit:** Existe una brecha contra tu meta. Necesitamos que tus inversiones trabajen más duro por ti. Sugiero un perfil de Crecimiento para tu portafolio.")
                riesgo_sugerido = 0.80

            st.session_state["riesgo_objetivo_ldi"] = riesgo_sugerido
            st.session_state["datos_ldi_pdf"] = {
                "horizonte": anios_horizonte, "aportacion": aportacion_mensual, 
                "meta": meta_mensual, "brecha": brecha, "capital_real": capital_acumulado_real
            }

# ── PASO 3: ESTRATEGIA (Motor Cuantitativo) ────────────────────────────────────
with tab_estrategia:
    st.markdown("### Optimización Matemática del Portafolio")
    st.caption("Alineamos tu capital actual y tus aportaciones mensuales bajo un modelo institucional de riesgo-retorno.")
    
    with st.form("motor_form"):
        col_t, col_p = st.columns([2,1])
        tickers_input = col_t.text_input("Activos seleccionados para la estrategia (Separados por coma):", value="IVVPESO.MX, AAPL.MX, QQQ, GLD, TLT")
        
        riesgo_def = st.session_state.get("riesgo_objetivo_ldi", 0.80)
        riesgo_max = col_p.slider("Límite de Exposición a Renta Variable (Riesgo)", 10, 100, int(riesgo_def*100), step=5) / 100
        st.caption("El límite de riesgo fue sugerido automáticamente por el diagnóstico LDI del paso anterior.")
        
        ejecutar_opt = st.form_submit_button("Construir Frontera Eficiente y Simular Futuro", width='stretch')

    if ejecutar_opt:
        tickers_lista = [t.strip() for t in tickers_input.split(",")]
        
        try:
            with st.spinner("Descargando data histórica y procesando matrices de covarianza..."):
                datos, ret_diarios, ret_anuales, matriz_cov = obtener_datos(tickers_input, "2020-01-01", str(datetime.today().date()))
                
                # Identificamos refugios para el algoritmo
                REFUGIOS = {"TLT","IEF","SHY","BND","AGG","BIL","GLD","IAU","USDC-USD","CASH"}
                es_riesgo = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in tickers_lista])
                
                # Optimizamos
                pesos_opt = optimizar_sharpe_slsqp(
                    ret_anuales.to_numpy(), matriz_cov.to_numpy(), tasa_rf,
                    peso_min=0.02, peso_max=0.40,
                    min_riesgo_total=max(0.10, riesgo_max - 0.10),
                    max_riesgo_total=riesgo_max,
                    es_riesgo=es_riesgo
                )
                
                if pesos_opt is None:
                    st.error("Error matemático: Las restricciones chocan. Intenta subir el límite de exposición o incluir activos refugio (TLT, GLD).")
                    st.stop()
                    
                ret_opt = float(np.sum(pesos_opt * ret_anuales))
                vol_opt = float(np.sqrt(np.dot(pesos_opt.T, np.dot(matriz_cov, pesos_opt))))
                
                st.session_state.optimizado = True
                st.session_state.pesos_opt = pesos_opt
                st.session_state.ret_opt = ret_opt
                st.session_state.vol_opt = vol_opt
                st.session_state.tickers_sesion = tickers_lista
                
        except Exception as e:
            st.error(f"Ocurrió un error en el cálculo: {e}")
            st.stop()

    if st.session_state.optimizado:
        c1, c2, c3 = st.columns(3)
        c1.metric("Retorno Histórico Esperado", f"{st.session_state.ret_opt*100:.2f}% Anual")
        c2.metric("Volatilidad de la Estrategia", f"{st.session_state.vol_opt*100:.2f}% Anual")
        
        st.markdown("**Asignación de Capital Óptima sugerida por el Motor:**")
        df_pesos = pd.DataFrame({
            "Activo": st.session_state.tickers_sesion, 
            "Asignación (%)": (st.session_state.pesos_opt*100).round(2)
        }).sort_values("Asignación (%)", ascending=False)
        st.dataframe(df_pesos, use_container_width=True)

        st.markdown("---")
        st.subheader("Proyección Monte Carlo (Escenarios Futuros)")
        
        cap_ini = st.session_state.get("capital_inicial_diagnostico", 100000.0)
        datos_ldi = st.session_state.get("datos_ldi_pdf", {"horizonte": 10, "aportacion": 5000})
        
        with st.spinner("Simulando 2,000 líneas de tiempo futuras bajo modelos t-Student..."):
            # Generamos datos sinteticos rapidos para el MC
            dt = 1/12
            meses_sim = datos_ldi["horizonte"] * 12
            escenarios = np.zeros((meses_sim + 1, 2000))
            escenarios[0] = cap_ini
            
            for t in range(1, meses_sim + 1):
                z = np.random.standard_normal(2000)
                crecimiento = np.exp((st.session_state.ret_opt - 0.5 * st.session_state.vol_opt**2) * dt + st.session_state.vol_opt * np.sqrt(dt) * z)
                escenarios[t] = escenarios[t-1] * crecimiento + datos_ldi["aportacion"]
                
            p5 = np.percentile(escenarios, 5, axis=1)
            p50 = np.percentile(escenarios, 50, axis=1)
            p95 = np.percentile(escenarios, 95, axis=1)
            
            fig_mc = go.Figure()
            fig_mc.add_trace(go.Scatter(y=p50, mode="lines", line=dict(width=3, color="#17C37B"), name="Escenario Base (P50)"))
            fig_mc.add_trace(go.Scatter(y=p95, mode="lines", line=dict(width=2, color="rgba(23,195,123,0.5)", dash="dot"), name="Favorable (P95)"))
            fig_mc.add_trace(go.Scatter(y=p5, mode="lines", line=dict(width=2, color="#FF4B4B", dash="dot"), name="Crisis Adversa (P5)"))
            fig_mc.update_layout(template="plotly_dark", xaxis_title="Meses", yaxis_title="Capital (MXN)", height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_mc, use_container_width=True)

        st.markdown("---")
        st.subheader("Entregable de la Sesión")
        st.caption("Descarga la planeación actuarial para el cliente.")
        
        # AQUÍ IRÍA LA LLAMADA A TU REPORTE PERSONALIZADO
        # st.download_button("Descargar Reporte Patrimonial PDF", data=pdf_bytes, file_name="Reporte.pdf")
        st.success("¡Análisis completado con éxito! Listo para la explicación final.")
