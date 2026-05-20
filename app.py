import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
import secrets as secrets_lib
import yfinance as yf

from supabase import create_client, Client
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
    page_title="Motor GaLa Premium",
    page_icon="",
    layout="wide"
)

# ── Supabase ───────────────────────────────────────────────────────────────────
@st.cache_resource
def init_supabase() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

db = init_supabase()

# ── Utilidades de autenticación ────────────────────────────────────────────────
def hashear(texto: str) -> str:
    return hashlib.sha256(texto.encode()).hexdigest()

def tiene_cuenta_lite(email: str) -> bool:
    """Verifica si el email existe en la tabla de GaLa Lite."""
    try:
        r = db.table("usuarios").select("id").eq("email", email.lower()).execute()
        return bool(r.data)
    except Exception:
        return False

def registrar_premium(nombre: str, email: str, password: str) -> tuple[bool, str]:
    try:
        existe = db.table("usuarios_premium").select("id").eq("email", email.lower()).execute()
        if existe.data:
            return False, "Ya existe una cuenta Premium con ese correo."
        lite = tiene_cuenta_lite(email)
        db.table("usuarios_premium").insert({
            "nombre_display": nombre.strip(),
            "email":          email.strip().lower(),
            "password_hash":  hashear(password),
            "tiene_lite":     lite,
        }).execute()
        msg = "Cuenta creada. Se detectó acceso GaLa Lite — su descuento ha sido registrado." if lite \
              else "Cuenta creada correctamente."
        return True, msg
    except Exception as e:
        return False, f"Error al registrar: {e}"

def autenticar_premium(email: str, password: str) -> tuple[bool, dict]:
    try:
        r = db.table("usuarios_premium") \
            .select("id, nombre_display, email, tiene_lite") \
            .eq("email", email.strip().lower()) \
            .eq("password_hash", hashear(password)) \
            .execute()
        if r.data:
            return True, r.data[0]
        return False, {}
    except Exception:
        return False, {}

def generar_token_reset(email: str) -> tuple[bool, str]:
    """Genera un token de recuperación válido por 1 hora."""
    try:
        existe = db.table("usuarios_premium").select("id").eq("email", email.lower()).execute()
        if not existe.data:
            return False, "No existe una cuenta Premium con ese correo."
        token = secrets_lib.token_urlsafe(32)
        db.table("reset_tokens").insert({
            "email":     email.lower(),
            "token":     hashear(token),
            "expira_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }).execute()
        return True, token
    except Exception as e:
        return False, str(e)

def verificar_y_resetear(email: str, token: str, nueva_pass: str) -> tuple[bool, str]:
    try:
        r = db.table("reset_tokens") \
            .select("id, expira_at, usado") \
            .eq("email", email.lower()) \
            .eq("token", hashear(token)) \
            .eq("usado", False) \
            .execute()
        if not r.data:
            return False, "Token inválido o ya utilizado."
        expira = datetime.fromisoformat(r.data[0]["expira_at"].replace("Z", ""))
        if datetime.utcnow() > expira:
            return False, "El token ha expirado. Solicite uno nuevo."
        db.table("usuarios_premium").update({"password_hash": hashear(nueva_pass)}) \
            .eq("email", email.lower()).execute()
        db.table("reset_tokens").update({"usado": True}).eq("id", r.data[0]["id"]).execute()
        return True, "Contraseña actualizada correctamente."
    except Exception as e:
        return False, str(e)

def guardar_feedback(data: dict):
    try:
        db.table("feedback_premium").insert(data).execute()
        return True
    except Exception:
        return False

def guardar_post(data: dict):
    try:
        db.table("comunidad").insert(data).execute()
        return True
    except Exception:
        return False

def obtener_posts_aprobados():
    try:
        r = db.table("comunidad").select("*").eq("aprobado", True) \
            .order("created_at", desc=True).limit(20).execute()
        return r.data or []
    except Exception:
        return []

# ── Estado de sesión ───────────────────────────────────────────────────────────
defaults = {
    "usuario_premium": None,
    "optimizado":      False,
    "pesos_opt":       None,
    "ret_opt":         None,
    "vol_opt":         None,
    "sharpe_opt":      None,
    "resultados":      None,
    "df_regimenes":    None,
    "login_intentos":  0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# LANDING — AUTH
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state["usuario_premium"] is None:

    st.markdown("**Motor GaLa**")
    st.title("Sistema Institucional de Gestión de Capital")
    st.caption(
        "Optimización cuantitativa de portafolios sobre universos de hasta 500 activos. "
        "Markowitz · SLSQP · Monte Carlo t-Student · HMM · Glide Path actuarial."
    )
    st.markdown("---")

    col_info, col_auth = st.columns([1.3, 1], gap="large")

    with col_info:
        st.markdown("**Capacidades del sistema**")
        st.markdown("""
        - **Screening fundamental** — Filtrado automatizado sobre S&P 500 y NASDAQ 100 por Market Cap, P/E, Profit Margin y Deuda/Capital. Clustering K-Means para diversificación real entre sectores.
        - **Optimización SLSQP** — Maximización del Ratio de Sharpe bajo restricciones de concentración y Glide Path actuarial dinámico según horizonte de inversión.
        - **Riesgo institucional** — VaR, CVaR, Maximum Drawdown, Sortino, Stress Testing sobre crisis históricas y correlación dinámica rolling.
        - **Monte Carlo t-Student** — Simulaciones calibradas con fat tails (gl ≈ 4) para escenarios adversos realistas.
        - **Backtesting walk-forward** — Metodología sin look-ahead bias, neto de comisiones operativas.
        - **Modelos Ocultos de Markov** — Detección automática de regímenes de mercado integrada al proceso de rebalanceo.
        - **Reporte PDF institucional** — Documento de 6 páginas exportable con todas las métricas y gráficas.
        """)

        st.markdown("")
        st.markdown("**Descuento para usuarios GaLa Lite**")
        st.caption(
            "Si ya adquirió acceso a GaLa Lite (2 boletos Sorteo UDLAP), "
            "el costo se descuenta automáticamente al registrar su cuenta Premium con el mismo correo."
        )

    with col_auth:
        tab_login, tab_reg, tab_reset = st.tabs(["Iniciar sesión", "Crear cuenta", "Recuperar acceso"])

        with tab_login:
            st.caption("Ingrese sus credenciales para acceder al sistema.")
            with st.form("form_login_premium"):
                email_l    = st.text_input("Correo electrónico")
                pass_l     = st.text_input("Contraseña", type="password")
                login_btn  = st.form_submit_button("Iniciar sesión", use_container_width=True)

            if login_btn:
                if st.session_state["login_intentos"] >= 5:
                    st.error("Demasiados intentos fallidos. Espere unos minutos o recupere su acceso.")
                elif not email_l or not pass_l:
                    st.warning("Complete todos los campos.")
                else:
                    ok, usuario = autenticar_premium(email_l, pass_l)
                    if ok:
                        st.session_state["usuario_premium"]  = usuario
                        st.session_state["login_intentos"]   = 0
                        st.rerun()
                    else:
                        st.session_state["login_intentos"] += 1
                        restantes = 5 - st.session_state["login_intentos"]
                        st.error(f"Credenciales incorrectas. Intentos restantes: {restantes}.")

        with tab_reg:
            st.caption("Cree su cuenta para acceder al sistema Premium.")
            with st.form("form_registro_premium"):
                nombre_r  = st.text_input("¿Cómo quiere que le llamemos?",
                                          placeholder="Nombre, apodo o alias")
                email_r   = st.text_input("Correo electrónico")
                pass_r    = st.text_input("Contraseña", type="password")
                pass_r2   = st.text_input("Confirmar contraseña", type="password")
                reg_btn   = st.form_submit_button("Crear cuenta", use_container_width=True)

            if reg_btn:
                if not nombre_r or not email_r or not pass_r:
                    st.warning("Complete todos los campos.")
                elif pass_r != pass_r2:
                    st.error("Las contraseñas no coinciden.")
                elif len(pass_r) < 8:
                    st.warning("La contraseña debe tener al menos 8 caracteres.")
                else:
                    ok, msg = registrar_premium(nombre_r, email_r, pass_r)
                    if ok:
                        st.success(msg + " Inicie sesión para continuar.")
                    else:
                        st.error(msg)

        with tab_reset:
            st.caption(
                "Ingrese su correo. Se generará un token de recuperación que deberá "
                "compartir con la dirección del sistema para validar su identidad."
            )
            st.markdown("**Paso 1 — Solicitar token**")
            with st.form("form_solicitar_token"):
                email_rst = st.text_input("Correo electrónico registrado")
                sol_btn   = st.form_submit_button("Generar token", use_container_width=True)

            if sol_btn and email_rst:
                ok, resultado = generar_token_reset(email_rst)
                if ok:
                    st.success("Token generado.")
                    st.code(resultado, language=None)
                    st.caption(
                        f"Comparta este token con {st.secrets.get('ADMIN_EMAIL','la dirección del sistema')} "
                        "para verificar su identidad. Válido por 1 hora."
                    )
                else:
                    st.error(resultado)

            st.markdown("**Paso 2 — Restablecer contraseña**")
            with st.form("form_reset_pass"):
                email_r2    = st.text_input("Correo electrónico")
                token_r     = st.text_input("Token recibido")
                nueva_pass  = st.text_input("Nueva contraseña", type="password")
                nueva_pass2 = st.text_input("Confirmar nueva contraseña", type="password")
                reset_btn   = st.form_submit_button("Restablecer contraseña", use_container_width=True)

            if reset_btn:
                if nueva_pass != nueva_pass2:
                    st.error("Las contraseñas no coinciden.")
                elif len(nueva_pass) < 8:
                    st.warning("La contraseña debe tener al menos 8 caracteres.")
                else:
                    ok, msg = verificar_y_resetear(email_r2, token_r, nueva_pass)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# USUARIO AUTENTICADO
# ══════════════════════════════════════════════════════════════════════════════
usuario        = st.session_state["usuario_premium"]
nombre_display = usuario["nombre_display"]
tiene_lite     = usuario.get("tiene_lite", False)

# ── Encabezado ─────────────────────────────────────────────────────────────────
col_enc, col_salir = st.columns([4, 1])
with col_enc:
    st.markdown("**Motor GaLa Premium**")
    st.title(f"Bienvenido, {nombre_display}")
    st.markdown("*Sistema Institucional de Gestión de Capital y Análisis de Riesgo*")
    if tiene_lite:
        st.caption("Acceso GaLa Lite detectado — descuento aplicado a su cuenta.")
with col_salir:
    st.markdown("<div style='margin-top:3rem;'></div>", unsafe_allow_html=True)
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["usuario_premium"] = None
        st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# NAVEGACIÓN POR TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_motor, tab_noticias, tab_glosario, tab_comunidad, tab_feedback = st.tabs([
    "Motor Cuantitativo",
    "Noticias del Mercado",
    "Glosario Técnico",
    "Comunidad",
    "Sugerencias",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MOTOR CUANTITATIVO (código original intacto)
# ══════════════════════════════════════════════════════════════════════════════
with tab_motor:

    # ── Tasa de referencia Banxico ─────────────────────────────────────────────
    with st.sidebar:
        with st.spinner("Consultando Banco de México..."):
            tasa_actual_banxico = obtener_tasa_referencia_banxico()
            tasa_rf = tasa_actual_banxico
        st.metric(label="Tasa de Referencia Banxico", value=f"{tasa_actual_banxico * 100:.2f}%")

    margen_sugerido = float(round(tasa_actual_banxico * 100, 1))

    # ── Sidebar: Módulo 1 — Análisis Fundamental ──────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("1. Análisis Fundamental")
    usar_screening = st.sidebar.toggle("Activar selección algorítmica de activos", value=False)

    if usar_screening:
        with st.sidebar.form("screening_form"):
            universo_sel = st.selectbox("Universo de análisis", list(UNIVERSOS.keys()))
            min_cap      = st.slider("Capitalización mínima (B USD)", 1.0, 100.0, 10.0, step=1.0)
            min_margin   = st.slider("Margen de beneficio mínimo (%)", 0.0, 30.0, margen_sugerido, step=1.0,
                                     help=f"Referencia Banxico: {margen_sugerido}%")
            max_pe       = st.slider("P/E máximo", 10.0, 100.0, 50.0, step=5.0)
            min_roe_scr  = st.slider("ROE mínimo (%)", 0.0, 50.0, 10.0, step=1.0,
                                     help="Return on Equity mínimo aceptable")
            max_deuda_scr = st.slider("Deuda/Capital máximo (%)", 0, 500, 150, step=10,
                                      help="Ejemplo: 150 = deuda equivalente a 1.5x el capital propio")
            n_clusters   = st.slider("Grupos de diversificación (K-Means)", 2, 8, 4)
            ejecutar_scr = st.form_submit_button("Ejecutar análisis fundamental", use_container_width=True)
    else:
        ejecutar_scr = False

    # ── Sidebar: Módulo 2 — Optimización ──────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("2. Parámetros de Optimización")

    if usar_screening and "tickers_screening" in st.session_state:
        tickers_default = st.session_state["tickers_screening"]
    else:
        tickers_default = "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"

    with st.sidebar.form("optim_form"):
        tickers_input         = st.text_area("Activos a optimizar", value=tickers_default, height=70)
        fecha_inicio          = st.date_input("Fecha de inicio", value=pd.Timestamp("2020-01-01"))
        fecha_fin             = st.date_input("Fecha de cierre", value=pd.Timestamp("2026-05-08"))
        st.markdown("---")
        st.subheader("Restricciones de concentración")
        peso_max              = st.slider("Exposición máxima por activo (%)", 10, 100, 40) / 100
        peso_min              = st.slider("Exposición mínima por activo (%)", 0, 10, 2) / 100
        comision_broker       = st.number_input("Comisión operativa (%)", value=0.15, step=0.05) / 100
        st.markdown("---")
        st.subheader("Proyección de capital")
        capital_inicial       = st.number_input("Capital inicial (MXN)", min_value=0, value=100_000, step=10_000)
        frecuencia_aportacion = st.selectbox("Frecuencia de aportación", ["Mensual", "Trimestral", "Anual"], index=2)
        aportacion_mensual    = st.number_input("Aportación periódica (MXN)", min_value=0, value=100_000, step=10_000)
        horizonte_años        = st.slider("Horizonte de inversión (años)", min_value=1, max_value=40, value=10)
        num_sims              = st.slider("Simulaciones Monte Carlo", 500, 5000, 2000, step=500)

        st.markdown("---")
        st.subheader("Benchmark comparativo")
        PERFILES_BENCHMARK = {
            "Agresivo (S&P 500 — SPY)":           "SPY",
            "Agresivo Tecnológico (Nasdaq — QQQ)": "QQQ",
            "Moderado (Global 60/40 — AOR)":       "AOR",
            "Conservador (Bonos Globales — AGG)":  "AGG",
        }
        benchmark_seleccion = st.selectbox(
            "Perfil del benchmark",
            list(PERFILES_BENCHMARK.keys()),
            help="El benchmark se descarga junto con los activos para que las dimensiones cuadren."
        )
        ejecutar              = st.form_submit_button("Ejecutar optimización", use_container_width=True)

    # ── Funciones con caché ────────────────────────────────────────────────────
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
    def cached_var_cvar(_ret, cap):
        return calcular_var_cvar(_ret, cap)

    @st.cache_data(show_spinner=False)
    def cached_drawdown(_ret):
        return calcular_drawdown(_ret)

    @st.cache_data(show_spinner=False)
    def cached_sortino(_ret, r, rf):
        return calcular_sortino(_ret, r, rf)

    @st.cache_data(show_spinner=False)
    def cached_stress_test(pesos, tickers, cap, _ret):
        return calcular_stress_test(pesos, tickers, cap, _ret)

    @st.cache_data(show_spinner=False)
    def cached_metricas_bt(_rp, _rb, rf, _ep, _eb):
        return calcular_metricas_backtest(_rp, _rb, rf, _ep, _eb)

    @st.cache_data(show_spinner=False)
    def cached_retornos_anuales(_rp, _rb):
        return calcular_retornos_anuales(_rp, _rb)

    # ── Screening ──────────────────────────────────────────────────────────────
    df_mejores = None

    if usar_screening and ejecutar_scr:
        st.header("Análisis Fundamental — Selección de Activos")
        seleccion        = UNIVERSOS[universo_sel]
        tickers_universo = seleccion() if callable(seleccion) else seleccion

        with st.spinner(f"Procesando {len(tickers_universo)} instrumentos..."):
            df_fund = cached_descargar_fundamentales(tuple(tickers_universo))
            if df_fund.empty:
                st.error("No fue posible obtener datos de Yahoo Finance.")
            else:
                df_filtrado = filtrar_candidatos(
                    df_fund,
                    min_market_cap=min_cap,
                    min_profit_margin=min_margin,
                    max_pe=max_pe,
                    max_deuda=float(max_deuda_scr),  # yfinance devuelve debtToEquity en %, ej. 150 = 1.5x
                    min_roe=min_roe_scr,
                )
                if len(df_filtrado) < 2:
                    st.warning(f"Solo {len(df_filtrado)} instrumentos superaron los filtros.")
                else:
                    df_clusterizado, df_mejores = clustering_activos(df_filtrado, n_clusters)
                    st.session_state["df_screening"] = df_mejores
                    st.success(
                        f"Universo: {len(df_fund)}  |  Tras filtro: {len(df_filtrado)}  "
                        f"|  Representantes: {len(df_mejores)}"
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Instrumentos que superaron el filtro**")
                        st.dataframe(df_clusterizado.sort_values("Profit Margin %", ascending=False),
                                     height=300, use_container_width=True)
                    with c2:
                        st.markdown("**Selección óptima por cluster**")
                        st.dataframe(df_mejores[["Ticker","Nombre","Sector","Cluster",
                                                  "Market Cap (B)","P/E Ratio","Profit Margin %"]],
                                     height=300, use_container_width=True)
                    tickers_sugeridos = ", ".join(df_mejores["Ticker"].tolist()) + ", TLT, GLD"
                    st.session_state["tickers_screening"] = tickers_sugeridos
                    st.info(f"Cartera sugerida: **{tickers_sugeridos}**")
        st.stop()

    # ── Freno de emergencia ────────────────────────────────────────────────────
    if not ejecutar and not st.session_state.optimizado:
        st.info("Configure los parámetros en el panel izquierdo y ejecute la optimización.")
        st.stop()

    # ── Descarga de históricos ─────────────────────────────────────────────────
    # Guardamos benchmark_elegido en session_state para que persista entre reruns
    benchmark_elegido = PERFILES_BENCHMARK[benchmark_seleccion]
    if ejecutar:
        st.session_state["tickers_procesar"]  = tickers_input
        st.session_state["benchmark_elegido"] = benchmark_elegido

    tickers_finales   = st.session_state.get("tickers_procesar", tickers_input)
    benchmark_elegido = st.session_state.get("benchmark_elegido", benchmark_elegido)

    # Construir lista de descarga: activos del usuario + benchmark (sin duplicados)
    tickers_lista     = [t.strip() for t in tickers_finales.split(",")]
    tickers_descarga  = tickers_lista + (
        [benchmark_elegido] if benchmark_elegido not in tickers_lista else []
    )
    tickers_descarga_key = ", ".join(tickers_descarga)  # clave para el caché

    try:
        with st.spinner("Descargando series históricas de precios..."):
            datos_full, retornos_full, _, _ = obtener_datos(
                tickers_descarga_key, str(fecha_inicio), str(fecha_fin)
            )
            # Separar benchmark del universo de optimización
            tickers           = [t for t in retornos_full.columns if t != benchmark_elegido]
            datos             = datos_full[tickers]
            retornos_diarios  = retornos_full[tickers]
            retornos_para_bt  = retornos_full          # incluye benchmark para backtesting
            _, retornos_anuales, matriz_cov = calcular_retornos(datos)
    except Exception as e:
        st.error(f"Error al descargar históricos: {e}")
        st.stop()

    # ── Optimización ──────────────────────────────────────────────────────────
    if ejecutar:
        with st.spinner("Ejecutando optimización y análisis de regímenes..."):
            st.session_state.df_regimenes = entrenar_modelo_markov(datos)
            REFUGIOS = {"TLT","IEF","SHY","BND","AGG","BIL","GLD","IAU","USDC-USD","CASH"}
            es_riesgo = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in tickers])
            num_refugios = np.sum(es_riesgo == 0.0)
            target_riesgo = min(1.0, max(0.20, horizonte_años / 15.0))
            factor_glide  = max(target_riesgo, max(0.0, 1.0 - num_refugios * peso_max))

            resultados, pesos_guardados = simular_portafolios(
                retornos_anuales, matriz_cov, tasa_rf, num_portafolios=num_sims)

            pesos_opt = optimizar_sharpe_slsqp(
                retornos_anuales, matriz_cov, tasa_rf,
                peso_min=peso_min, peso_max=peso_max,
                max_riesgo_total=factor_glide, es_riesgo=es_riesgo)

            ret_opt    = float(np.sum(pesos_opt * retornos_anuales))
            vol_opt    = float(np.sqrt(np.dot(pesos_opt.T, np.dot(matriz_cov, pesos_opt))))
            sharpe_opt = float((ret_opt - tasa_rf) / vol_opt)

            st.session_state.optimizado  = True
            st.session_state.pesos_opt   = pesos_opt
            st.session_state.ret_opt     = ret_opt
            st.session_state.vol_opt     = vol_opt
            st.session_state.sharpe_opt  = sharpe_opt
            st.session_state.resultados  = resultados

    res        = st.session_state.resultados
    pesos_opt  = st.session_state.pesos_opt
    ret_opt    = st.session_state.ret_opt
    vol_opt    = st.session_state.vol_opt
    sharpe_opt = st.session_state.sharpe_opt

    # ── Precios históricos ─────────────────────────────────────────────────────
    st.subheader("Precios de Cierre Históricos")
    if st.toggle("Mostrar gráfica de precios"):
        st.line_chart(datos)
    else:
        st.caption("Active el interruptor para visualizar la evolución histórica de precios.")

    # ── Frontera eficiente ─────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Frontera Eficiente — Markowitz")
    c1, c2, c3 = st.columns(3)
    c1.metric("Retorno Esperado Anual", f"{ret_opt*100:.2f}%")
    c2.metric("Volatilidad Anual",      f"{vol_opt*100:.2f}%")
    c3.metric("Ratio de Sharpe",        f"{sharpe_opt:.4f}")

    fig_markowitz = go.Figure()
    fig_markowitz.add_trace(go.Scatter(
        x=res[1]*100, y=res[0]*100, mode="markers",
        marker=dict(color=res[2], colorscale="Viridis", size=4, opacity=0.5,
                    colorbar=dict(title="Sharpe")),
        name="Portafolios simulados",
        hovertemplate="Volatilidad: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra></extra>"
    ))
    fig_markowitz.add_trace(go.Scatter(
        x=[vol_opt*100], y=[ret_opt*100], mode="markers",
        marker=dict(symbol="star", size=20, color="red"),
        name="Óptimo Max Sharpe",
        hovertemplate=f"Sharpe: {sharpe_opt:.4f}<extra></extra>"
    ))
    fig_markowitz.update_layout(template="plotly_dark", xaxis_title="Volatilidad Anual (%)",
        yaxis_title="Retorno Anual (%)", height=480, legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig_markowitz, use_container_width=True, key="chart_markowitz")

    st.subheader("Distribución Óptima del Capital")
    df_pesos = pd.DataFrame({"Activo": tickers, "Peso (%)": (pesos_opt*100).round(2)}) \
        .sort_values("Peso (%)", ascending=False)
    st.dataframe(df_pesos, use_container_width=True)
    # ── Asistente de Rebalanceo ───────────────────────────────────────────────
    st.subheader("Asistente de Rebalanceo Automático")
    st.caption(
        "Instrucciones exactas para asignar el capital inicial según los pesos óptimos. "
        "Asume que el capital está actualmente en efectivo o en liquidez total."
    )

    capital_rebalanceo = st.number_input(
        "Capital disponible para asignar (MXN)",
        min_value=0, value=int(capital_inicial), step=10_000,
        key="capital_rebalanceo",
        help="Por defecto usa el capital inicial configurado. Puede ajustarlo aquí."
    )

    df_rebalanceo = pd.DataFrame({
        "Activo":            tickers,
        "Peso Óptimo (%)":  (pesos_opt * 100).round(2),
        "Monto Objetivo (MXN)": (pesos_opt * capital_rebalanceo).round(0).astype(int),
    }).sort_values("Peso Óptimo (%)", ascending=False).reset_index(drop=True)

    df_rebalanceo["Instrucción en Mercado"] = df_rebalanceo["Monto Objetivo (MXN)"].apply(
        lambda m: f"Invertir ${m:,}"
    )

    # Resaltado visual: mayor peso → instrucción más relevante
    st.dataframe(
        df_rebalanceo[["Activo", "Peso Óptimo (%)", "Monto Objetivo (MXN)", "Instrucción en Mercado"]],
        use_container_width=True,
        column_config={
            "Monto Objetivo (MXN)": st.column_config.NumberColumn(format="$%d"),
            "Peso Óptimo (%)":      st.column_config.ProgressColumn(
                min_value=0, max_value=100, format="%.2f%%"
            ),
        }
    )

    total_asignado = df_rebalanceo["Monto Objetivo (MXN)"].sum()
    diferencia     = capital_rebalanceo - total_asignado
    c1, c2, c3 = st.columns(3)
    c1.metric("Capital disponible",  f"${capital_rebalanceo:,}")
    c2.metric("Total a asignar",     f"${total_asignado:,}")
    c3.metric("Diferencia (redondeo)", f"${diferencia:,}",
              help="Diferencia por redondeo. Asignar al activo de mayor peso.")

    # ── Backtesting Walk-Forward ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Backtesting Dinámico — Walk-Forward")
    st.caption("Pesos recalculados trimestralmente con datos históricos exclusivamente. Neto de comisiones.")

    @st.cache_data(show_spinner=False)
    def correr_backtest(datos, rf, cap, pmin, pmax, max_r, _es_r, _df_reg, comision, bench_override):
        return calcular_backtest_walk_forward(
            retornos_diarios=datos, funcion_optimizador=optimizar_sharpe_slsqp,
            tasa_rf=rf, peso_min=pmin, peso_max=pmax, max_riesgo_total=max_r,
            es_riesgo=_es_r, df_regimenes=_df_reg, comision_broker=comision,
            capital_inicial=cap, benchmark_ticker_override=bench_override)

   # ── INICIO DEL BLOQUE A REEMPLAZAR ──
    with st.spinner("Procesando backtesting..."):
        REFUGIOS = {"TLT","IEF","SHY","BND","AGG","BIL","GLD","IAU","USDC-USD","CASH"}
        
        # 1. Filtramos la matriz para evitar columnas duplicadas o fantasmas
        columnas_validas = [c for c in list(tickers) + [benchmark_elegido] if c in retornos_para_bt.columns]
        retornos_para_bt = retornos_para_bt[columnas_validas]
        
        # 2. EL SECRETO: El arreglo de riesgo debe tener EXACTAMENTE el mismo tamaño
        # que las columnas que entran al backtesting para que Numpy no colapse.
        es_riesgo_arr = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in retornos_para_bt.columns])

        factor_glide = max(min(1.0, max(0.20, horizonte_años/15.0)),
                           max(0.0, 1.0 - np.sum(es_riesgo_arr==0.0)*peso_max))
        
        df_equity, benchmark_ticker, retorno_port, retorno_bench = correr_backtest(
            retornos_para_bt, tasa_rf, capital_inicial, peso_min, peso_max,
            factor_glide, es_riesgo_arr, st.session_state.df_regimenes,
            comision_broker, benchmark_elegido)
    # ── FIN DEL BLOQUE A REEMPLAZAR ──
            
        # Extraemos solo las columnas que existen, borrando "fantasmas"
        columnas_existentes = [c for c in columnas_validas if c in retornos_para_bt.columns]
        retornos_para_bt = retornos_para_bt[columnas_existentes]
        
        # 2. Generamos el arreglo de riesgo ESTRICTAMENTE para las columnas que se van a optimizar
        # (Es decir, la matriz pura sin el benchmark)
        activos_optimizador = [c for c in retornos_para_bt.columns if c != benchmark_elegido]
        es_riesgo_arr = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in activos_optimizador])
        # ────────────────────────────────────────────────────────────

        factor_glide  = max(min(1.0, max(0.20, horizonte_años/15.0)),
                            max(0.0, 1.0 - np.sum(es_riesgo_arr==0.0)*peso_max))
        
        df_equity, benchmark_ticker, retorno_port, retorno_bench = correr_backtest(
            retornos_para_bt, tasa_rf, capital_inicial, peso_min, peso_max,
            factor_glide, es_riesgo_arr, st.session_state.df_regimenes,
            comision_broker, benchmark_elegido)

    metricas_bt = cached_metricas_bt(
        retorno_port, retorno_bench, tasa_rf,
        df_equity["Portafolio GaLa (Dinámico)"],
        df_equity[f"Benchmark ({benchmark_ticker})"])

    st.markdown("**Análisis comparativo de rendimiento**")
    comparativas = [
        ("CAGR",         f"{metricas_bt['cagr_port']*100:.2f}%",  f"{metricas_bt['cagr_bench']*100:.2f}%"),
        ("Volatilidad",  f"{metricas_bt['vol_port']*100:.2f}%",   f"{metricas_bt['vol_bench']*100:.2f}%"),
        ("Sharpe",       f"{metricas_bt['sharpe_port']:.4f}",      f"{metricas_bt['sharpe_bench']:.4f}"),
        ("Sortino",      f"{metricas_bt['sortino_port']:.4f}",     f"{metricas_bt['sortino_bench']:.4f}"),
        ("Max Drawdown", f"{metricas_bt['mdd_port']*100:.2f}%",   f"{metricas_bt['mdd_bench']*100:.2f}%"),
        ("Calmar",       f"{metricas_bt['calmar_port']:.4f}",      f"{metricas_bt['calmar_bench']:.4f}"),
    ]
    h1, h2, h3 = st.columns(3)
    h1.markdown("**Métrica**"); h2.markdown("**Motor GaLa**"); h3.markdown(f"**{benchmark_ticker}**")
    st.markdown("---")
    for m, vp, vb in comparativas:
        c1, c2, c3 = st.columns(3)
        c1.write(m); c2.write(vp); c3.write(vb)
    st.markdown("")
    c1, c2 = st.columns(2)
    c1.metric("Alpha (Jensen)",    f"{metricas_bt['alpha']*100:.2f}%")
    c2.metric("Beta vs Benchmark", f"{metricas_bt['beta']:.4f}")

    fig_bt = go.Figure()
    fig_bt.add_trace(go.Scatter(x=df_equity.index, y=df_equity["Portafolio GaLa (Dinámico)"],
        mode="lines", line=dict(width=2.5, color="#4488ff"), name="Motor GaLa"))
    fig_bt.add_trace(go.Scatter(x=df_equity.index,
        y=df_equity[f"Benchmark ({benchmark_ticker})"],
        mode="lines", line=dict(width=1.5, color="rgba(200,200,200,0.6)", dash="dot"),
        name=benchmark_ticker))
    fig_bt.update_layout(template="plotly_dark", xaxis_title="Fecha", yaxis_title="Capital (USD)",
        height=420, legend=dict(x=0.01, y=0.99), hovermode="x unified")
    st.plotly_chart(fig_bt, use_container_width=True, key="chart_bt")

    anuales   = cached_retornos_anuales(retorno_port, retorno_bench)
    fig_anuales = go.Figure()
    fig_anuales.add_trace(go.Bar(x=anuales.index.astype(str), y=anuales["Portafolio GaLa"],
        name="Motor GaLa", marker_color="#4488ff"))
    fig_anuales.add_trace(go.Bar(x=anuales.index.astype(str), y=anuales["Benchmark"],
        name=benchmark_ticker, marker_color="rgba(200,200,200,0.5)"))
    fig_anuales.add_hline(y=0, line_color="white", line_width=0.5)
    fig_anuales.update_layout(template="plotly_dark", barmode="group",
        xaxis_title="Año", yaxis_title="Retorno (%)", height=360, legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig_anuales, use_container_width=True, key="chart_anuales")

    # ── Monte Carlo ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Proyección de Capital — Monte Carlo")
    retorno_port_mc = retornos_diarios @ pesos_opt
    escenarios, p5, p50, p95, benchmark_fijo, df_t = simular_capital(
        capital_inicial=capital_inicial, aportacion_periodica=aportacion_mensual,
        rendimiento_anual=ret_opt, volatilidad_anual=vol_opt,
        meses=horizonte_años*12, frecuencia_aportacion=frecuencia_aportacion,
        tasa_benchmark=tasa_actual_banxico, num_simulaciones=num_sims,
        retornos_diarios=retorno_port_mc)

    st.caption(f"t-Student gl={df_t:.2f} — "
               f"{'cola pesada severa' if df_t < 5 else 'cola pesada moderada' if df_t < 10 else 'aproximación normal'}")

    fig_mc = go.Figure()
    for i in range(min(20, escenarios.shape[1])):
        fig_mc.add_trace(go.Scatter(y=escenarios[:,i], mode="lines",
            line=dict(width=1, color="rgba(0,150,255,0.08)"), showlegend=False, hoverinfo="skip"))
    fig_mc.add_trace(go.Scatter(y=p50, mode="lines", line=dict(width=3, color="#17C37B"),
        name="Base (P50)"))
    fig_mc.add_trace(go.Scatter(y=p95, mode="lines",
        line=dict(width=2, color="rgba(23,195,123,0.5)", dash="dot"), name="Favorable (P95)"))
    fig_mc.add_trace(go.Scatter(y=p5, mode="lines",
        line=dict(width=2, color="#FF4B4B", dash="dot"), name="Adverso (P5)"))
    fig_mc.add_trace(go.Scatter(y=benchmark_fijo, mode="lines",
        line=dict(width=3, color="gray", dash="dash"),
        name=f"Tasa fija ({tasa_actual_banxico*100:.2f}%)"))
    fig_mc.update_layout(template="plotly_dark", xaxis_title="Meses", yaxis_title="Capital (MXN)",
        height=480, legend=dict(x=0.01, y=0.99))
    st.plotly_chart(fig_mc, use_container_width=True, key="chart_mc")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Adverso (P5)",    f"${p5[-1]:,.0f}")
    c2.metric("Base (P50)",      f"${p50[-1]:,.0f}")
    c3.metric("Favorable (P95)", f"${p95[-1]:,.0f}")
    c4.metric("Tasa fija",       f"${benchmark_fijo[-1]:,.0f}",
              delta=f"${p50[-1]-benchmark_fijo[-1]:,.0f} diferencial")
    # ── Tabla de hitos en el tiempo ───────────────────────────────────────────
    st.markdown("**Matriz de capitalización por horizonte temporal**")
    st.caption(
        "Comparativa del escenario base (P50) vs tasa fija en hitos clave. "
        "Ilustra cómo el interés compuesto amplifica la ventaja a largo plazo."
    )

    n_meses_total = horizonte_años * 12
    hitos_meses   = [m for m in [12, 36, 60, n_meses_total] if m <= n_meses_total]
    hitos_labels  = {12: "1 año", 36: "3 años", 60: "5 años", n_meses_total: f"{horizonte_años} años (fin)"}
    # Eliminar duplicados si horizonte < 5 años
    hitos_meses   = list(dict.fromkeys(hitos_meses))

    filas_hitos = []
    for m in hitos_meses:
        idx = min(m, len(p50) - 1)
        ventaja = p50[idx] - benchmark_fijo[idx]
        filas_hitos.append({
            "Horizonte":            hitos_labels.get(m, f"Mes {m}"),
            "Adverso P5 (MXN)":    int(p5[idx]),
            "Base P50 (MXN)":      int(p50[idx]),
            "Favorable P95 (MXN)": int(p95[idx]),
            "Tasa fija (MXN)":     int(benchmark_fijo[idx]),
            "Ventaja P50 vs Fija": int(ventaja),
        })

    df_hitos = pd.DataFrame(filas_hitos)
    st.dataframe(
        df_hitos,
        use_container_width=True,
        column_config={
            "Adverso P5 (MXN)":    st.column_config.NumberColumn(format="$%d"),
            "Base P50 (MXN)":      st.column_config.NumberColumn(format="$%d"),
            "Favorable P95 (MXN)": st.column_config.NumberColumn(format="$%d"),
            "Tasa fija (MXN)":     st.column_config.NumberColumn(format="$%d"),
            "Ventaja P50 vs Fija": st.column_config.NumberColumn(format="$%d"),
        },
        hide_index=True,
    )
    st.caption(
        "La columna 'Ventaja P50 vs Fija' muestra cuánto capital adicional genera el motor "
        "respecto a dejar el dinero en un instrumento de tasa fija al mismo horizonte."
    )

    # ── Riesgo institucional ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Análisis de Riesgo Institucional")
    capital_riesgo      = st.number_input("Capital de referencia (USD)", value=200_000, step=10_000)
    retorno_port_diario = retornos_diarios @ pesos_opt

    st.markdown("#### Value at Risk y Expected Shortfall")
    var_cvar = cached_var_cvar(retorno_port_diario, capital_riesgo)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("VaR 95% Histórico", f"{var_cvar['VaR_95_hist']*100:.2f}%",
              f"-${abs(var_cvar['VaR_95_hist'])*capital_riesgo:,.0f} USD")
    c2.metric("VaR 99% Histórico", f"{var_cvar['VaR_99_hist']*100:.2f}%",
              f"-${abs(var_cvar['VaR_99_hist'])*capital_riesgo:,.0f} USD")
    c3.metric("CVaR 95%",          f"{var_cvar['CVaR_95']*100:.2f}%",
              f"-${abs(var_cvar['CVaR_95'])*capital_riesgo:,.0f} USD")
    c4.metric("CVaR 99%",          f"{var_cvar['CVaR_99']*100:.2f}%",
              f"-${abs(var_cvar['CVaR_99'])*capital_riesgo:,.0f} USD")

    fig_var = go.Figure()
    fig_var.add_trace(go.Histogram(x=retorno_port_diario*100, nbinsx=80,
        marker_color="rgba(68,136,255,0.7)", name="Retornos diarios"))
    fig_var.add_vline(x=var_cvar["VaR_95_hist"]*100, line_color="red",
        line_dash="dash", annotation_text="VaR 95%")
    fig_var.add_vline(x=var_cvar["CVaR_95"]*100,     line_color="orange",
        line_dash="dash", annotation_text="CVaR 95%")
    fig_var.add_vline(x=var_cvar["VaR_99_hist"]*100, line_color="magenta",
        line_dash="dot",  annotation_text="VaR 99%")
    fig_var.update_layout(template="plotly_dark", height=380,
        xaxis_title="Retorno Diario (%)", yaxis_title="Frecuencia")
    st.plotly_chart(fig_var, use_container_width=True, key="chart_var")

    st.markdown("#### Maximum Drawdown")
    dd_serie, max_dd, inicio_dd, fin_dd, duracion_dd = cached_drawdown(retorno_port_diario)
    c1,c2,c3 = st.columns(3)
    c1.metric("Maximum Drawdown", f"{max_dd*100:.2f}%",
              f"-${abs(max_dd)*capital_riesgo:,.0f} USD")
    c2.metric("Duración",         f"{duracion_dd} días ({duracion_dd//30} meses)")
    c3.metric("Período",          f"{inicio_dd.strftime('%b %Y')} — {fin_dd.strftime('%b %Y')}")

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=dd_serie.index, y=dd_serie*100,
        fill="tozeroy", fillcolor="rgba(255,68,68,0.3)",
        line=dict(color="red", width=1), name="Drawdown"))
    fig_dd.add_hline(y=max_dd*100, line_color="gold", line_dash="dash",
        annotation_text=f"Max DD: {max_dd*100:.2f}%")
    fig_dd.update_layout(template="plotly_dark", height=350,
        xaxis_title="Fecha", yaxis_title="Drawdown (%)")
    st.plotly_chart(fig_dd, use_container_width=True, key="chart_dd")

    st.markdown("#### Sortino vs Sharpe")
    sortino, desv_down = cached_sortino(retorno_port_diario, ret_opt, tasa_rf)
    c1,c2,c3 = st.columns(3)
    c1.metric("Sharpe",               f"{sharpe_opt:.4f}")
    c2.metric("Sortino",              f"{sortino:.4f}")
    c3.metric("Desviación downside",  f"{desv_down*100:.2f}%")

    st.markdown("#### Stress Testing — Escenarios Históricos")
    df_stress = cached_stress_test(pesos_opt, tickers, capital_riesgo, retornos_diarios)
    fig_stress = go.Figure(go.Bar(
        x=df_stress["Pérdida (%)"], y=df_stress["Escenario"], orientation="h",
        marker_color=["red" if p < -15 else "orange" if p < -8 else "gold"
                      for p in df_stress["Pérdida (%)"]],
        text=[f"{p:.1f}%" for p in df_stress["Pérdida (%)"]],
        textposition="outside"))
    fig_stress.update_layout(template="plotly_dark", height=350, xaxis_title="Impacto en Capital (%)")
    st.plotly_chart(fig_stress, use_container_width=True, key="chart_stress")
    st.dataframe(df_stress, use_container_width=True)

    st.markdown("#### Correlación Dinámica Rolling — 60 días")
    fig_corr   = None
    pares_corr = calcular_correlacion_rolling(retornos_diarios)
    if pares_corr:
        fig_corr = go.Figure()
        for (nombre, serie), color in zip(pares_corr.items(), ["gold", "rgba(68,136,255,0.9)"]):
            fig_corr.add_trace(go.Scatter(x=serie.index, y=serie, mode="lines",
                line=dict(width=1.5, color=color), name=nombre))
        fig_corr.add_hline(y=0.6,  line_color="rgba(255,0,0,0.5)",  line_dash="dot",
            annotation_text="Zona de riesgo")
        fig_corr.add_hline(y=0,    line_color="gray", line_dash="solid", line_width=0.5)
        fig_corr.add_hline(y=-0.6, line_color="rgba(0,255,0,0.5)", line_dash="dot",
            annotation_text="Zona de cobertura")
        fig_corr.update_layout(template="plotly_dark", height=350,
            yaxis=dict(range=[-1.1, 1.1]),
            xaxis_title="Fecha", yaxis_title="Coeficiente de Pearson")
        st.plotly_chart(fig_corr, use_container_width=True, key="chart_corr")
    else:
        st.info(f"Incluya BTC-USD/SPY o QQQ/TLT para ver correlación dinámica. "
                f"Tickers actuales: {retornos_diarios.columns.tolist()}")

    # ── Regímenes HMM ──────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Detección de Regímenes de Mercado — HMM")
    df_regimenes = st.session_state.get("df_regimenes", None)
    if df_regimenes is not None:
        calma  = df_regimenes[df_regimenes["Regimen"] == 0]
        panico = df_regimenes[df_regimenes["Regimen"] == 1]
        fig_hmm = go.Figure()
        fig_hmm.add_trace(go.Scatter(x=calma.index, y=calma["Precio"], mode="markers",
            marker=dict(color="rgba(0,255,100,0.6)", size=4), name="Régimen normal"))
        fig_hmm.add_trace(go.Scatter(x=panico.index, y=panico["Precio"], mode="markers",
            marker=dict(color="rgba(255,50,50,0.8)", size=6, symbol="x"), name="Régimen de tensión"))
        fig_hmm.update_layout(template="plotly_dark", height=400,
            xaxis_title="Fecha", yaxis_title="Precio", legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_hmm, use_container_width=True, key="chart_hmm")
        pct = (df_regimenes["Regimen"] == 1).mean() * 100
        c1, c2 = st.columns(2)
        c1.metric("Régimen normal",   f"{100-pct:.1f}%")
        c2.metric("Régimen tensión",  f"{pct:.1f}%")
    else:
        st.info("Ejecute la optimización para generar el análisis de regímenes.")

    # ── Reporte PDF ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Exportar Reporte Institucional")
    if st.button("Generar reporte PDF", type="primary"):
        with st.spinner("Generando reporte..."):
            try:
                pdf_bytes = generar_reporte(
                    tickers=tickers, pesos_opt=pesos_opt, ret_opt=ret_opt, vol_opt=vol_opt,
                    sharpe_opt=sharpe_opt, sortino=sortino, desv_down=desv_down, df_t=df_t,
                    var_cvar=var_cvar, max_dd=max_dd, duracion_dd=duracion_dd,
                    inicio_dd=inicio_dd, fin_dd=fin_dd, df_stress=df_stress,
                    capital_riesgo=capital_riesgo, p5_final=p5[-1], p50_final=p50[-1],
                    p95_final=p95[-1], horizonte_años=horizonte_años,
                    capital_inicial=capital_inicial, aportacion_mensual=aportacion_mensual,
                    num_sims=num_sims,
                    metricas_bt=metricas_bt, benchmark_ticker=benchmark_ticker,
                    df_screening=st.session_state.get("df_screening", None),
                    fig_markowitz=fig_markowitz, fig_mc=fig_mc, fig_var=fig_var,
                    fig_dd=fig_dd, fig_stress=fig_stress, fig_bt=fig_bt,
                    fig_anuales=fig_anuales, fig_corr=fig_corr,
                )
                st.download_button(
                    label="Descargar reporte PDF", data=pdf_bytes,
                    file_name=f"MotorGaLa_{nombre_display}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf")
                st.success("Reporte generado correctamente.")
            except Exception as e:
                st.error(f"Error al generar el reporte: {e}")
                st.exception(e)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — NOTICIAS DEL MERCADO
# ══════════════════════════════════════════════════════════════════════════════
with tab_noticias:
    st.subheader("Noticias del Mercado Financiero")
    st.caption("Titulares recientes de finanzas, inversión, startups y fintech vía Yahoo Finance.")

    TICKERS_NOTICIAS = {
        "Mercados globales":  "^GSPC",
        "Tecnología":         "QQQ",
        "Fintech & Crypto":   "BTC-USD",
        "Mercado mexicano":   "^MXX",
    }

    categoria_sel = st.selectbox("Categoría", list(TICKERS_NOTICIAS.keys()))

    @st.cache_data(show_spinner=False, ttl=1800)
    def obtener_noticias(ticker: str) -> list:
        try:
            return yf.Ticker(ticker).news or []
        except Exception:
            return []

    with st.spinner("Cargando noticias..."):
        noticias = obtener_noticias(TICKERS_NOTICIAS[categoria_sel])

    if not noticias:
        st.info("No hay noticias disponibles en este momento. Intente en unos minutos.")
    else:
        for n in noticias[:12]:
            titulo    = n.get("title", "Sin título")
            publisher = n.get("publisher", "—")
            link      = n.get("link", "#")
            ts        = n.get("providerPublishTime", None)
            fecha     = datetime.fromtimestamp(ts).strftime("%d %b %Y  %H:%M") if ts else "—"

            with st.container():
                col_txt, col_btn = st.columns([4, 1])
                with col_txt:
                    st.markdown(f"**{titulo}**")
                    st.caption(f"{publisher}  ·  {fecha}")
                with col_btn:
                    st.link_button("Leer", link, use_container_width=True)
                st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GLOSARIO TÉCNICO
# ══════════════════════════════════════════════════════════════════════════════
with tab_glosario:
    st.subheader("Glosario de Términos Técnicos")
    st.caption(
        "Referencia rápida de los conceptos utilizados en el motor. "
        "Comprenderlos convierte el uso de la herramienta en formación financiera aplicada."
    )

    terminos = {
        "Ratio de Sharpe": (
            "Mide el rendimiento excedente por unidad de riesgo total. "
            "Fórmula: (Retorno - Tasa libre de riesgo) / Volatilidad. "
            "Un Sharpe > 1 se considera sólido; > 2, excepcional."
        ),
        "Ratio de Sortino": (
            "Variante del Sharpe que solo penaliza la volatilidad negativa (downside). "
            "Más relevante que el Sharpe cuando la distribución de retornos es asimétrica. "
            "Fórmula: (Retorno - MAR) / Desviación Downside."
        ),
        "Value at Risk (VaR)": (
            "Pérdida máxima esperada en un período dado con un nivel de confianza específico. "
            "VaR 95%: en el 95% de los días, la pérdida no superará este valor. "
            "Limitación: no dice nada sobre qué ocurre en el 5% restante."
        ),
        "CVaR / Expected Shortfall": (
            "Complemento del VaR. Mide la pérdida promedio en los escenarios que sí superan el VaR. "
            "Más conservador y preferido por reguladores (Basilea III). "
            "Responde la pregunta: si las cosas salen mal, ¿cuánto se pierde en promedio?"
        ),
        "Maximum Drawdown": (
            "Caída máxima desde un pico hasta el valle más profundo antes de recuperarse. "
            "Mide el peor escenario histórico que un inversionista hubiera experimentado. "
            "Fundamental para evaluar la resistencia psicológica y financiera al riesgo."
        ),
        "Calmar Ratio": (
            "CAGR dividido entre el Maximum Drawdown en valor absoluto. "
            "Evalúa el rendimiento en relación a la peor caída histórica. "
            "Útil para comparar estrategias con distintos perfiles de riesgo."
        ),
        "Alpha (Jensen)": (
            "Retorno excedente generado por el portafolio respecto a lo que predice el modelo CAPM. "
            "Alpha positivo indica que el gestor agrega valor más allá del mercado. "
            "Fórmula: Retorno del portafolio - (Rf + Beta × (Rm - Rf))."
        ),
        "Beta": (
            "Sensibilidad del portafolio ante movimientos del benchmark. "
            "Beta = 1: mueve igual que el mercado. Beta < 1: menos volátil. Beta > 1: más volátil. "
            "Beta negativo: se mueve en dirección opuesta al mercado."
        ),
        "Optimización SLSQP": (
            "Sequential Least Squares Quadratic Programming. "
            "Algoritmo de optimización numérica que encuentra los pesos que maximizan el Sharpe "
            "respetando restricciones de concentración y Glide Path. "
            "Más preciso que la búsqueda aleatoria de Monte Carlo."
        ),
        "Frontera Eficiente (Markowitz)": (
            "Conjunto de portafolios que maximizan el retorno para cada nivel de riesgo dado. "
            "Desarrollada por Harry Markowitz (Nobel de Economía 1990). "
            "El portafolio óptimo está en la frontera; cualquier otro es subóptimo."
        ),
        "Glide Path Actuarial": (
            "Reducción gradual de la exposición a riesgo conforme se acerca el horizonte de liquidación. "
            "Concepto tomado de los fondos de ciclo de vida (target-date funds). "
            "En el motor: la exposición máxima a renta variable disminuye con los años."
        ),
        "Modelo Oculto de Markov (HMM)": (
            "Modelo estadístico que clasifica cada período en estados 'ocultos' del mercado "
            "(régimen normal vs régimen de tensión) basándose en retornos y volatilidad. "
            "En el backtesting, activa cobertura automática cuando detecta régimen de pánico."
        ),
        "Monte Carlo (t-Student)": (
            "Simulación de miles de trayectorias posibles del capital usando números aleatorios. "
            "La distribución t-Student captura fat tails: eventos extremos más frecuentes que en la normal. "
            "Los grados de libertad (gl) se calibran con datos históricos reales del portafolio."
        ),
        "Fat Tails": (
            "Colas pesadas de una distribución estadística. "
            "Indican que los eventos extremos (crashes, rallies) ocurren con mayor frecuencia "
            "de lo que predice una distribución normal. "
            "Por eso el motor usa t-Student en lugar de distribución gaussiana."
        ),
        "Backtesting Walk-Forward": (
            "Metodología de prueba histórica sin look-ahead bias. "
            "Los pesos se recalculan periódicamente usando solo datos disponibles hasta ese momento. "
            "Estándar institucional: evita el error de optimizar con información del futuro."
        ),
        "K-Means Clustering": (
            "Algoritmo de machine learning no supervisado que agrupa activos por similitud de perfil fundamental. "
            "En el motor: garantiza que el portafolio incluya representantes de distintos clusters, "
            "evitando concentración sectorial disfrazada de diversificación."
        ),
        "CAGR": (
            "Compound Annual Growth Rate — Tasa de Crecimiento Anual Compuesta. "
            "Mide el rendimiento anualizado de una inversión considerando el efecto del interés compuesto. "
            "Fórmula: (Valor final / Valor inicial)^(1/años) - 1."
        ),
    }

    busqueda = st.text_input("Buscar término", placeholder="Ej. Sharpe, VaR, Markowitz...")

    terminos_filtrados = {
        k: v for k, v in terminos.items()
        if busqueda.lower() in k.lower() or busqueda.lower() in v.lower()
    } if busqueda else terminos

    for termino, definicion in terminos_filtrados.items():
        with st.expander(termino):
            st.write(definicion)

    if not terminos_filtrados:
        st.info("No se encontraron términos que coincidan con la búsqueda.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — COMUNIDAD
# ══════════════════════════════════════════════════════════════════════════════
with tab_comunidad:
    st.subheader("Comunidad GaLa Premium")
    st.caption(
        "Espacio para compartir análisis, perspectivas e ideas sobre inversión y finanzas. "
        "Los posts son revisados antes de publicarse para garantizar un entorno de valor y respeto."
    )

    with st.expander("Normas de participación", expanded=False):
        st.markdown("""
        - El contenido debe ser relevante para finanzas, inversión, gestión de capital o mercados.
        - Se prohíben recomendaciones específicas de compra o venta de activos.
        - No se permiten publicaciones de carácter promocional, político o irrespetuoso.
        - Los posts son moderados antes de aparecer públicamente.
        - El equipo de Motor GaLa se reserva el derecho de rechazar cualquier publicación.
        """)

    st.markdown("**Publicar en la comunidad**")
    with st.form("form_comunidad"):
        titulo_post   = st.text_input("Título", placeholder="Ej. Análisis del sector energético mexicano Q2 2026")
        categoria_post = st.selectbox("Categoría",
            ["Análisis de mercado", "Estrategia de inversión", "Macro y economía",
             "Fintech y tecnología", "Gestión de riesgo", "Pregunta a la comunidad"])
        contenido_post = st.text_area("Contenido",
            placeholder="Comparta su análisis, perspectiva o pregunta...",
            height=150)
        post_btn = st.form_submit_button("Enviar para revisión", use_container_width=True)

    if post_btn:
        if not titulo_post.strip() or not contenido_post.strip():
            st.warning("Complete el título y el contenido antes de enviar.")
        elif len(contenido_post.strip()) < 50:
            st.warning("El contenido debe tener al menos 50 caracteres.")
        else:
            ok = guardar_post({
                "id_usuario":     usuario["id"],
                "nombre_display": nombre_display,
                "titulo":         titulo_post.strip(),
                "contenido":      contenido_post.strip(),
                "categoria":      categoria_post,
                "aprobado":       False,
            })
            if ok:
                st.success("Post enviado para revisión. Aparecerá en la comunidad una vez aprobado.")
            else:
                st.error("No fue posible enviar el post. Intente nuevamente.")

    st.markdown("---")
    st.markdown("**Posts de la comunidad**")

    posts = obtener_posts_aprobados()
    if not posts:
        st.info("Aún no hay publicaciones aprobadas. Sea el primero en contribuir.")
    else:
        for post in posts:
            with st.container():
                col_meta, col_cat = st.columns([3, 1])
                with col_meta:
                    st.markdown(f"**{post['titulo']}**")
                    fecha = datetime.fromisoformat(
                        post["created_at"].replace("Z","")).strftime("%d %b %Y")
                    st.caption(f"{post.get('nombre_display','Anónimo')}  ·  {fecha}")
                with col_cat:
                    st.caption(post.get("categoria", "General"))
                st.write(post["contenido"])
                st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — SUGERENCIAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_feedback:
    st.subheader("Comentarios y Sugerencias")
    st.caption("Su retroalimentación contribuye directamente al desarrollo del sistema.")

    with st.form("form_feedback_premium"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            contacto_fb = st.text_input("Correo de contacto (opcional)")
        with col_f2:
            tipo_fb = st.selectbox("Tipo de comentario", [
                "Sugerencia de mejora", "Reporte de error",
                "Solicitud de funcionalidad", "Otro"
            ])
        valoracion = st.select_slider("Valoración general del sistema",
            options=["1 — Deficiente","2 — Regular","3 — Aceptable","4 — Bueno","5 — Excelente"],
            value="4 — Bueno")
        comentario_fb = st.text_area("Comentario",
            placeholder="Describa su experiencia, sugerencia o área de mejora...",
            height=120)
        enviado = st.form_submit_button("Enviar comentario", use_container_width=True)

    if enviado:
        if comentario_fb.strip():
            ok = guardar_feedback({
                "id_usuario":     usuario["id"],
                "nombre_display": nombre_display,
                "contacto":       contacto_fb,
                "tipo":           tipo_fb,
                "valoracion":     valoracion,
                "comentario":     comentario_fb.strip(),
            })
            if ok:
                st.success("Comentario registrado. Gracias por contribuir al desarrollo del sistema.")
            else:
                st.warning("No fue posible guardar el comentario. Intente nuevamente.")
        else:
            st.warning("Incluya un comentario antes de enviar.")

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(f"**{nombre_display}**")
st.sidebar.caption(usuario["email"])
if tiene_lite:
    st.sidebar.caption("Acceso GaLa Lite — descuento aplicado")
st.sidebar.markdown("---")
st.sidebar.caption(
    "Motor GaLa Premium · Sistema Institucional de Gestión de Capital. "
    "Los resultados son producto de modelos matemáticos y no constituyen asesoría de inversión."
)
