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
    page_icon="logo_gala-removebg-preview.png",
    layout="wide",
    initial_sidebar_state="expanded"  
)

# ── CSS Institucional ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=DM+Mono:wght@300;400;500&display=swap');

#MainMenu, footer, header { visibility: hidden; }

html, body, [class*="css"] {
    font-family: 'EB Garamond', Georgia, serif;
}

.stApp {
    background-color: #0C0F14;
}

/* ── Tipografía ─────────────────────────────────────────────────────── */
h1, h2, h3 {
    font-family: 'EB Garamond', Georgia, serif !important;
    font-weight: 500 !important;
    color: #E8EDF5 !important;
    letter-spacing: 0.01em !important;
}

p, div, label, span {
    font-family: 'EB Garamond', Georgia, serif;
    color: #B0BACA;
}

/* ── Sidebar ────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #0A0D12 !important;
    border-right: 0.5px solid rgba(68,136,255,0.1) !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: #5A6780 !important;
    font-weight: 400 !important;
}

/* ── Tabs ───────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 0.5px solid rgba(68,136,255,0.15);
    gap: 1.5rem;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 400 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #3A4A5E !important;
    background: transparent !important;
    border: none !important;
    padding: 0.7rem 0.5rem !important;
}

.stTabs [aria-selected="true"] {
    color: #4488FF !important;
    border-bottom: 1px solid #4488FF !important;
}

/* ── Inputs ─────────────────────────────────────────────────────────── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div {
    background-color: #0F1420 !important;
    border: 0.5px solid rgba(68,136,255,0.18) !important;
    border-radius: 4px !important;
    color: #E8EDF5 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}

[data-testid="stNumberInput"] input:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(68,136,255,0.5) !important;
    box-shadow: 0 0 0 1px rgba(68,136,255,0.12) !important;
}

/* ── Slider ─────────────────────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div {
    background: linear-gradient(90deg, #4488FF, #4488FF) !important;
}

/* ── Métricas ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0F1420 0%, #111827 100%);
    border: 0.5px solid rgba(68,136,255,0.15);
    border-radius: 6px;
    padding: 1.1rem 1.4rem;
}
[data-testid="stMetricLabel"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: #5A6780 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 1.35rem !important;
    color: #E8EDF5 !important;
    letter-spacing: -0.02em !important;
}

/* ── Botones ────────────────────────────────────────────────────────── */
.stButton > button,
.stFormSubmitButton > button {
    background: transparent !important;
    border: 0.5px solid rgba(68,136,255,0.35) !important;
    color: #4488FF !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.55rem 1.25rem !important;
    border-radius: 3px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    background: rgba(68,136,255,0.07) !important;
    border-color: #4488FF !important;
}
[data-testid="baseButton-primary"] {
    background: #4488FF !important;
    color: #0C0F14 !important;
    border: none !important;
    font-weight: 500 !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #5594FF !important;
}

/* ── File uploader ──────────────────────────────────────────────────── */
[data-testid="stFileUploadDropzone"] {
    background-color: rgba(68,136,255,0.02) !important;
    border: 0.5px dashed rgba(68,136,255,0.25) !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploadDropzone"]:hover {
    background-color: rgba(68,136,255,0.05) !important;
    border-color: rgba(68,136,255,0.5) !important;
}

/* ── Dataframe ──────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(68,136,255,0.12) !important;
    border-radius: 6px !important;
}

/* ── Divisores ──────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 0.5px solid rgba(68,136,255,0.12) !important;
    margin: 2rem 0 !important;
}

/* ── Alertas ────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 4px !important;
    border-left-width: 2px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
}

/* ── Toggle ─────────────────────────────────────────────────────────── */
[data-testid="stToggle"] label {
    font-family: 'EB Garamond', Georgia, serif !important;
    font-size: 15px !important;
    color: #B0BACA !important;
}

/* ── Expander ───────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 0.5px solid rgba(68,136,255,0.12) !important;
    border-radius: 4px !important;
    background: rgba(15,20,32,0.4) !important;
}
</style>
""", unsafe_allow_html=True)

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

def guardar_feedback(data: dict) -> tuple[bool, str]:
    try:
        db.table("feedback_premium").insert(data).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

def guardar_post(data: dict) -> tuple[bool, str]:
    try:
        db.table("comunidad").insert(data).execute()
        return True, ""
    except Exception as e:
        return False, str(e)

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

    st.markdown("""
    <div style='padding: 3rem 0 1.5rem; text-align: left;'>
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.25em;
            text-transform: uppercase;
            color: #4488FF;
            margin-bottom: 1rem;
        '>Motor GaLa · Sistema Premium</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: clamp(28px, 4vw, 42px);
            font-weight: 400;
            color: #E8EDF5;
            letter-spacing: 0.01em;
            line-height: 1.2;
            margin-bottom: 0.75rem;
        '>Sistema Institucional de Gestión de Capital</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 17px;
            font-style: italic;
            color: #5A6780;
        '>Optimización cuantitativa de portafolios sobre universos de hasta 500 activos.
        Markowitz · SLSQP · Monte Carlo t-Student · HMM · Glide Path actuarial.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 2.5rem;'></div>",
        unsafe_allow_html=True
    )

    col_info, col_auth = st.columns([1.3, 1], gap="large")

    with col_info:
        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #5A6780;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 0.5px solid rgba(68,136,255,0.12);
        '>Capacidades del sistema</div>
        """, unsafe_allow_html=True)

        capacidades = [
            ("Screening fundamental",
             "Filtrado automatizado sobre S&P 500 y NASDAQ 100 por Market Cap, P/E, Profit Margin y Deuda/Capital. Clustering K-Means para diversificación real entre sectores."),
            ("Optimización SLSQP",
             "Maximización del Ratio de Sharpe bajo restricciones de concentración y Glide Path actuarial dinámico según horizonte de inversión."),
            ("Riesgo institucional",
             "VaR, CVaR, Maximum Drawdown, Sortino, Stress Testing sobre crisis históricas y correlación dinámica rolling."),
            ("Monte Carlo t-Student",
             "Simulaciones calibradas con fat tails (gl ≈ 4) para escenarios adversos realistas."),
            ("Backtesting walk-forward",
             "Metodología sin look-ahead bias, neto de comisiones operativas."),
            ("Modelos Ocultos de Markov",
             "Detección automática de regímenes de mercado integrada al proceso de rebalanceo."),
            ("Reporte PDF institucional",
             "Documento de 6 páginas exportable con todas las métricas y gráficas."),
        ]

        for titulo, desc in capacidades:
            st.markdown(f"""
            <div style='margin-bottom: 0.9rem;'>
                <div style='
                    font-family: "EB Garamond", Georgia, serif;
                    font-size: 16px;
                    color: #E8EDF5;
                    font-weight: 500;
                    margin-bottom: 0.15rem;
                '>{titulo}</div>
                <div style='
                    font-family: "EB Garamond", Georgia, serif;
                    font-size: 14px;
                    font-style: italic;
                    color: #5A6780;
                    line-height: 1.5;
                '>{desc}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style='
            margin-top: 1.5rem;
            padding: 1rem 1.25rem;
            background: rgba(68,136,255,0.03);
            border: 0.5px solid rgba(68,136,255,0.15);
            border-left: 2px solid rgba(68,136,255,0.4);
            border-radius: 4px;
        '>
            <div style='
                font-family: "DM Mono", monospace;
                font-size: 10px;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #4488FF;
                margin-bottom: 0.4rem;
            '>Descuento GaLa Lite</div>
            <div style='
                font-family: "EB Garamond", Georgia, serif;
                font-size: 14px;
                font-style: italic;
                color: #5A6780;
                line-height: 1.55;
            '>
                Si ya adquirió acceso a GaLa Lite (2 boletos Sorteo UDLAP),
                el costo se descuenta automáticamente al registrar su cuenta Premium con el mismo correo.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_auth:
        tab_login, tab_reg, tab_reset = st.tabs(["Iniciar sesión", "Crear cuenta", "Recuperar acceso"])

        with tab_login:
            st.caption("Ingrese sus credenciales para acceder al sistema.")
            with st.form("form_login_premium"):
                email_l   = st.text_input("Correo electrónico")
                pass_l    = st.text_input("Contraseña", type="password")
                login_btn = st.form_submit_button("Iniciar sesión", use_container_width=True)

            if login_btn:
                if st.session_state["login_intentos"] >= 5:
                    st.error("Demasiados intentos fallidos. Espere unos minutos o recupere su acceso.")
                elif not email_l or not pass_l:
                    st.warning("Complete todos los campos.")
                else:
                    ok, usuario = autenticar_premium(email_l, pass_l)
                    if ok:
                        st.session_state["usuario_premium"] = usuario
                        st.session_state["login_intentos"]  = 0
                        st.rerun()
                    else:
                        st.session_state["login_intentos"] += 1
                        restantes = 5 - st.session_state["login_intentos"]
                        st.error(f"Credenciales incorrectas. Intentos restantes: {restantes}.")

        with tab_reg:
            st.caption("Cree su cuenta para acceder al sistema Premium.")
            with st.form("form_registro_premium"):
                nombre_r = st.text_input("¿Cómo quiere que le llamemos?", placeholder="Nombre, apodo o alias")
                email_r  = st.text_input("Correo electrónico")
                pass_r   = st.text_input("Contraseña", type="password")
                pass_r2  = st.text_input("Confirmar contraseña", type="password")
                reg_btn  = st.form_submit_button("Crear cuenta", use_container_width=True)

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
            st.markdown("""
            <div style='
                font-family: "DM Mono", monospace;
                font-size: 10px;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #5A6780;
                margin-bottom: 0.5rem;
            '>Paso 1 — Solicitar token</div>
            """, unsafe_allow_html=True)
            with st.form("form_solicitar_token"):
                email_rst = st.text_input("Correo electrónico registrado")
                sol_btn   = st.form_submit_button("Generar token", use_container_width=True)

            if sol_btn and email_rst:
                ok, resultado = generar_token_reset(email_rst)
                if ok:
                    st.success("Token generado.")
                    st.code(resultado, language=None)
                    st.caption(
                        f"Comparta este token con {st.secrets.get('ADMIN_EMAIL', 'la dirección del sistema')} "
                        "para verificar su identidad. Válido por 1 hora."
                    )
                else:
                    st.error(resultado)

            st.markdown("""
            <div style='
                font-family: "DM Mono", monospace;
                font-size: 10px;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #5A6780;
                margin: 1.25rem 0 0.5rem;
            '>Paso 2 — Restablecer contraseña</div>
            """, unsafe_allow_html=True)
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
es_admin       = (usuario["email"] == "gal259148@gmail.com")

# ── Encabezado ─────────────────────────────────────────────────────────────────
col_enc, col_salir = st.columns([4, 1])
with col_enc:
    st.markdown(f"""
    <div style='padding: 1.5rem 0 0.5rem;'>
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #4488FF;
            margin-bottom: 0.5rem;
        '>Motor GaLa Premium</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: clamp(22px, 3vw, 32px);
            font-weight: 400;
            color: #E8EDF5;
            letter-spacing: 0.01em;
            line-height: 1.2;
        '>Bienvenido, {nombre_display}</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 15px;
            font-style: italic;
            color: #5A6780;
            margin-top: 0.25rem;
        '>Sistema Institucional de Gestión de Capital y Análisis de Riesgo{"&ensp;·&ensp;<span style='color:#17C37B;font-style:normal;'>Acceso GaLa Lite — descuento aplicado</span>" if tiene_lite else ""}</div>
    </div>
    """, unsafe_allow_html=True)

with col_salir:
    st.markdown("""
    <div style='
        display: flex;
        justify-content: flex-end;
        align-items: center;
        padding-top: 2rem;
        gap: 12px;
    '>
        <div style='
            display: flex;
            align-items: center;
            gap: 7px;
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #17C37B;
        '>
            <span style='
                width: 6px; height: 6px;
                background: #17C37B;
                border-radius: 50%;
                display: inline-block;
                box-shadow: 0 0 6px rgba(23,195,123,0.5);
            '></span>
            Sesión activa
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["usuario_premium"] = None
        st.rerun()

st.markdown(
    "<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 0;'></div>",
    unsafe_allow_html=True
)

# ── Helper: encabezado de sección ──────────────────────────────────────────────
def _header(eyebrow: str, titulo: str, color: str = "#5A6780"):
    st.markdown(f"""
    <div style='margin: 2rem 0 1.5rem;'>
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: {color};
            margin-bottom: 0.4rem;
        '>{eyebrow}</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 24px;
            color: #E8EDF5;
            font-weight: 400;
        '>{titulo}</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# NAVEGACIÓN POR TABS
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR GLOBAL (CONTROLES)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    with st.spinner("Consultando Banco de México..."):
        tasa_actual_banxico = obtener_tasa_referencia_banxico()
        tasa_rf = tasa_actual_banxico
    st.metric(label="Tasa de Referencia Banxico", value=f"{tasa_actual_banxico * 100:.2f}%")

    margen_sugerido = float(round(tasa_actual_banxico * 100, 1))

    # Sidebar: Módulo 1
    st.markdown("---")
    st.subheader("1. Análisis Fundamental")
    usar_screening = st.toggle("Activar selección algorítmica de activos", value=False)

    if usar_screening:
        with st.form("screening_form"):
            universo_sel  = st.selectbox("Universo de análisis", list(UNIVERSOS.keys()))
            min_cap       = st.slider("Capitalización mínima (B USD)", 1.0, 100.0, 10.0, step=1.0)
            min_margin    = st.slider("Margen de beneficio mínimo (%)", 0.0, 30.0, margen_sugerido, step=1.0,
                                      help=f"Referencia Banxico: {margen_sugerido}%")
            max_pe        = st.slider("P/E máximo", 10.0, 100.0, 50.0, step=5.0)
            min_roe_scr   = st.slider("ROE mínimo (%)", 0.0, 50.0, 10.0, step=1.0)
            max_deuda_scr = st.slider("Deuda/Capital máximo (%)", 0, 500, 150, step=10)
            n_clusters    = st.slider("Grupos de diversificación (K-Means)", 2, 8, 4)
            incluir_refugios = st.checkbox("Incluir activos de refugio (TLT, GLD)", value=True)
            ejecutar_scr  = st.form_submit_button("Ejecutar análisis fundamental", use_container_width=True)
    else:
        ejecutar_scr = False

    # Sidebar: Módulo 2
    st.markdown("---")
    st.subheader("2. Parámetros de Optimización")

    tickers_default = st.session_state.get("tickers_screening", "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX") if usar_screening else "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"

    with st.form("optim_form"):
        tickers_input         = st.text_area("Activos a optimizar", value=tickers_default, height=70, key="widget_tickers")
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
            "Agresivo (S&P 500 — SPY)":            "SPY",
            "Agresivo Tecnológico (Nasdaq — QQQ)": "QQQ",
            "Moderado (Global 60/40 — AOR)":       "AOR",
            "Conservador (Bonos Globales — AGG)":  "AGG",
        }
        benchmark_seleccion = st.selectbox("Perfil del benchmark", list(PERFILES_BENCHMARK.keys()))
        ejecutar = st.form_submit_button("Ejecutar optimización", use_container_width=True)

    # Sidebar: Info del usuario
    st.markdown("---")
    st.markdown(f"**{nombre_display}**")
    st.caption(usuario["email"])
    if tiene_lite:
        st.caption("Acceso GaLa Lite — descuento aplicado")
    st.markdown("---")
    st.caption("Motor GaLa Premium · Sistema Institucional")

# ══════════════════════════════════════════════════════════════════════════════
# NAVEGACIÓN POR TABS Y CACHÉ DE FUNCIONES
# ══════════════════════════════════════════════════════════════════════════════

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
def cached_var_cvar(_ret, cap):      return calcular_var_cvar(_ret, cap)
@st.cache_data(show_spinner=False)
def cached_drawdown(_ret):           return calcular_drawdown(_ret)
@st.cache_data(show_spinner=False)
def cached_sortino(_ret, r, rf):     return calcular_sortino(_ret, r, rf)
@st.cache_data(show_spinner=False)
def cached_stress_test(pesos, tickers, cap, _ret): return calcular_stress_test(pesos, tickers, cap, _ret)
@st.cache_data(show_spinner=False)
def cached_metricas_bt(_rp, _rb, rf, _ep, _eb): return calcular_metricas_backtest(_rp, _rb, rf, _ep, _eb)
@st.cache_data(show_spinner=False)
def cached_retornos_anuales(_rp, _rb): return calcular_retornos_anuales(_rp, _rb)

tabs_nombres = ["Motor Cuantitativo", "Noticias del Mercado", "Glosario Técnico", "Comunidad", "Sugerencias"]
if es_admin: tabs_nombres.append("Administración")

tabs_objetos  = st.tabs(tabs_nombres)
tab_motor     = tabs_objetos[0]
tab_noticias  = tabs_objetos[1]
tab_glosario  = tabs_objetos[2]
tab_comunidad = tabs_objetos[3]
tab_feedback  = tabs_objetos[4]
tab_admin     = tabs_objetos[5] if es_admin else None

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MOTOR CUANTITATIVO (CONTENIDO)
# ══════════════════════════════════════════════════════════════════════════════
with tab_motor:
    if usar_screening and ejecutar_scr:
        _header("Análisis Fundamental", "Selección de Activos")
        seleccion        = UNIVERSOS[universo_sel]
        tickers_universo = seleccion() if callable(seleccion) else seleccion

        with st.spinner(f"Procesando {len(tickers_universo)} instrumentos..."):
            df_fund = cached_descargar_fundamentales(tuple(tickers_universo))
            if df_fund.empty:
                st.error("No fue posible obtener datos de Yahoo Finance.")
            else:
                df_filtrado = filtrar_candidatos(
                    df_fund, min_market_cap=min_cap, min_profit_margin=min_margin,
                    max_pe=max_pe, max_deuda=float(max_deuda_scr), min_roe=min_roe_scr
                )
                if len(df_filtrado) < 2:
                    st.warning(f"Solo {len(df_filtrado)} instrumentos superaron los filtros.")
                else:
                    df_clusterizado, df_mejores = clustering_activos(df_filtrado, n_clusters)
                    st.session_state["df_screening"] = df_mejores

                    tickers_sugeridos = ", ".join(df_mejores["Ticker"].tolist()) + (", TLT, GLD" if incluir_refugios else "")
                    st.session_state["tickers_screening"] = tickers_sugeridos
                    st.session_state["widget_tickers"]    = tickers_sugeridos

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
                    st.info(f"Cartera sugerida: **{tickers_sugeridos}**")

    # Sidebar: Módulo 2
    st.sidebar.markdown("---")
    st.sidebar.subheader("2. Parámetros de Optimización")

    tickers_default = st.session_state["tickers_screening"] \
        if usar_screening and "tickers_screening" in st.session_state \
        else "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"

    with st.sidebar.form("optim_form"):
        tickers_input         = st.text_area("Activos a optimizar", value=tickers_default, height=70, key="widget_tickers")
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
        benchmark_seleccion = st.selectbox("Perfil del benchmark", list(PERFILES_BENCHMARK.keys()),
            help="El benchmark se descarga junto con los activos para que las dimensiones cuadren.")
        ejecutar = st.form_submit_button("Ejecutar optimización", use_container_width=True)

    if not ejecutar and not st.session_state.optimizado:
        st.markdown("""
        <div style='
            margin: 3rem 0;
            padding: 1.5rem 2rem;
            border: 0.5px solid rgba(68,136,255,0.15);
            border-left: 2px solid rgba(68,136,255,0.3);
            border-radius: 4px;
            background: rgba(68,136,255,0.02);
            font-family: "EB Garamond", Georgia, serif;
            font-size: 16px;
            font-style: italic;
            color: #5A6780;
        '>Configure los parámetros en el panel izquierdo y ejecute la optimización para iniciar el análisis.</div>
        """, unsafe_allow_html=True)
    else:
        benchmark_elegido = PERFILES_BENCHMARK[benchmark_seleccion]
        if ejecutar:
            st.session_state["tickers_procesar"]  = tickers_input
            st.session_state["benchmark_elegido"] = benchmark_elegido

        tickers_finales   = st.session_state.get("tickers_procesar", tickers_input)
        benchmark_elegido = st.session_state.get("benchmark_elegido", benchmark_elegido)

        tickers_lista        = [t.strip() for t in tickers_finales.split(",")]
        tickers_descarga     = tickers_lista + ([benchmark_elegido] if benchmark_elegido not in tickers_lista else [])
        tickers_descarga_key = ", ".join(tickers_descarga)

        try:
            with st.spinner("Descargando series históricas de precios..."):
                datos_full, retornos_full, _, _ = obtener_datos(tickers_descarga_key, str(fecha_inicio), str(fecha_fin))
                tickers          = [t for t in retornos_full.columns if t != benchmark_elegido]
                datos            = datos_full[tickers]
                retornos_diarios = retornos_full[tickers]
                retornos_para_bt = retornos_full
                _, retornos_anuales, matriz_cov = calcular_retornos(datos)
        except Exception as e:
            st.error(f"Error al descargar históricos: {e}")
            st.stop()

        if ejecutar:
            with st.spinner("Ejecutando optimización y análisis de regímenes..."):
                st.session_state.df_regimenes = entrenar_modelo_markov(datos)
                REFUGIOS      = {"TLT","IEF","SHY","BND","AGG","BIL","GLD","IAU","USDC-USD","CASH"}
                es_riesgo     = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in tickers])
                num_refugios  = np.sum(es_riesgo == 0.0)
                target_riesgo = min(1.0, max(0.20, horizonte_años / 15.0))
                factor_glide  = max(target_riesgo, max(0.0, 1.0 - num_refugios * peso_max))

                resultados, pesos_guardados = simular_portafolios(retornos_anuales, matriz_cov, tasa_rf, num_portafolios=num_sims)
                pesos_opt = optimizar_sharpe_slsqp(retornos_anuales, matriz_cov, tasa_rf,
                    peso_min=peso_min, peso_max=peso_max, max_riesgo_total=factor_glide, es_riesgo=es_riesgo)

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

        # Precios históricos
        _header("Datos históricos", "Precios de Cierre")
        if st.toggle("Mostrar gráfica de precios"):
            st.line_chart(datos)
        else:
            st.caption("Active el interruptor para visualizar la evolución histórica de precios.")

        # Frontera eficiente
        st.markdown("---")
        _header("Markowitz", "Frontera Eficiente")
        c1, c2, c3 = st.columns(3)
        c1.metric("Retorno Esperado Anual", f"{ret_opt*100:.2f}%")
        c2.metric("Volatilidad Anual",      f"{vol_opt*100:.2f}%")
        c3.metric("Ratio de Sharpe",        f"{sharpe_opt:.4f}")

        fig_markowitz = go.Figure()
        fig_markowitz.add_trace(go.Scatter(x=res[1]*100, y=res[0]*100, mode="markers",
            marker=dict(color=res[2], colorscale="Viridis", size=4, opacity=0.5,
                        colorbar=dict(title="Sharpe")),
            name="Portafolios simulados",
            hovertemplate="Volatilidad: %{x:.2f}%<br>Retorno: %{y:.2f}%<extra></extra>"))
        fig_markowitz.add_trace(go.Scatter(x=[vol_opt*100], y=[ret_opt*100], mode="markers",
            marker=dict(symbol="star", size=20, color="red"), name="Óptimo Max Sharpe",
            hovertemplate=f"Sharpe: {sharpe_opt:.4f}<extra></extra>"))
        fig_markowitz.update_layout(template="plotly_dark", xaxis_title="Volatilidad Anual (%)",
            yaxis_title="Retorno Anual (%)", height=480, legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_markowitz, use_container_width=True, key="chart_markowitz")

        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace; font-size: 10px;
            letter-spacing: 0.12em; text-transform: uppercase;
            color: #5A6780; margin: 1.5rem 0 0.75rem;
        '>Distribución óptima del capital</div>
        """, unsafe_allow_html=True)
        df_pesos = pd.DataFrame({"Activo": tickers, "Peso (%)": (pesos_opt*100).round(2)}) \
            .sort_values("Peso (%)", ascending=False)
        st.dataframe(df_pesos, use_container_width=True)

        # Rebalanceo
        st.markdown("---")
        _header("Asistente de rebalanceo", "Instrucciones de Asignación")
        st.caption("Instrucciones exactas para asignar el capital según los pesos óptimos. Asume capital en liquidez total.")

        capital_rebalanceo = st.number_input("Capital disponible para asignar (MXN)",
            min_value=0, value=int(capital_inicial), step=10_000, key="capital_rebalanceo",
            help="Por defecto usa el capital inicial configurado.")

        df_rebalanceo = pd.DataFrame({
            "Activo":               tickers,
            "Peso Óptimo (%)":     (pesos_opt * 100).round(2),
            "Monto Objetivo (MXN)":(pesos_opt * capital_rebalanceo).round(0).astype(int),
        }).sort_values("Peso Óptimo (%)", ascending=False).reset_index(drop=True)
        df_rebalanceo["Instrucción en Mercado"] = df_rebalanceo["Monto Objetivo (MXN)"].apply(lambda m: f"Invertir ${m:,}")

        st.dataframe(df_rebalanceo[["Activo","Peso Óptimo (%)","Monto Objetivo (MXN)","Instrucción en Mercado"]],
            use_container_width=True,
            column_config={
                "Monto Objetivo (MXN)": st.column_config.NumberColumn(format="$%d"),
                "Peso Óptimo (%)":      st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.2f%%"),
            })

        total_asignado = df_rebalanceo["Monto Objetivo (MXN)"].sum()
        diferencia     = capital_rebalanceo - total_asignado
        c1, c2, c3 = st.columns(3)
        c1.metric("Capital disponible",    f"${capital_rebalanceo:,}")
        c2.metric("Total a asignar",       f"${total_asignado:,}")
        c3.metric("Diferencia (redondeo)", f"${diferencia:,}",
                  help="Diferencia por redondeo. Asignar al activo de mayor peso.")

        # Backtesting
        st.markdown("---")
        _header("Walk-forward sin look-ahead bias", "Backtesting Dinámico")
        st.caption("Pesos recalculados trimestralmente con datos exclusivamente históricos. Resultados netos de comisiones operativas.")

        @st.cache_data(show_spinner=False)
        def correr_backtest(datos, rf, cap, pmin, pmax, max_r, _es_r, _df_reg, comision, bench_override):
            return calcular_backtest_walk_forward(
                retornos_diarios=datos, funcion_optimizador=optimizar_sharpe_slsqp,
                tasa_rf=rf, peso_min=pmin, peso_max=pmax, max_riesgo_total=max_r,
                es_riesgo=_es_r, df_regimenes=_df_reg, comision_broker=comision,
                capital_inicial=cap, benchmark_ticker_override=bench_override)

        with st.spinner("Procesando backtesting..."):
            REFUGIOS      = {"TLT","IEF","SHY","BND","AGG","BIL","GLD","IAU","USDC-USD","CASH"}
            columnas_validas  = [c for c in list(tickers) + [benchmark_elegido] if c in retornos_para_bt.columns]
            retornos_para_bt  = retornos_para_bt[columnas_validas]
            es_riesgo_arr     = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in retornos_para_bt.columns])
            factor_glide      = max(min(1.0, max(0.20, horizonte_años/15.0)),
                                   max(0.0, 1.0 - np.sum(es_riesgo_arr==0.0)*peso_max))
            df_equity, benchmark_ticker, retorno_port, retorno_bench = correr_backtest(
                retornos_para_bt, tasa_rf, capital_inicial, peso_min, peso_max,
                factor_glide, es_riesgo_arr, st.session_state.df_regimenes,
                comision_broker, benchmark_elegido)

        metricas_bt = cached_metricas_bt(retorno_port, retorno_bench, tasa_rf,
            df_equity["Portafolio GaLa (Dinámico)"], df_equity[f"Benchmark ({benchmark_ticker})"])

        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace; font-size: 10px;
            letter-spacing: 0.12em; text-transform: uppercase;
            color: #5A6780; margin-bottom: 0.75rem;
        '>Análisis comparativo de rendimiento</div>
        """, unsafe_allow_html=True)
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
        st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)
        for m, vp, vb in comparativas:
            c1, c2, c3 = st.columns(3)
            c1.write(m); c2.write(vp); c3.write(vb)
        st.markdown("")
        c1, c2 = st.columns(2)
        c1.metric("Alpha (Jensen)",    f"{metricas_bt['alpha']*100:.2f}%",
                  help="Retorno excedente respecto al modelo CAPM")
        c2.metric("Beta vs Benchmark", f"{metricas_bt['beta']:.4f}",
                  help="Sensibilidad del portafolio ante movimientos del benchmark")

        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(x=df_equity.index, y=df_equity["Portafolio GaLa (Dinámico)"],
            mode="lines", line=dict(width=2.5, color="#4488ff"), name="Motor GaLa"))
        fig_bt.add_trace(go.Scatter(x=df_equity.index, y=df_equity[f"Benchmark ({benchmark_ticker})"],
            mode="lines", line=dict(width=1.5, color="rgba(200,200,200,0.6)", dash="dot"), name=benchmark_ticker))
        fig_bt.update_layout(template="plotly_dark", xaxis_title="Fecha", yaxis_title="Capital (USD)",
            height=420, legend=dict(x=0.01, y=0.99), hovermode="x unified")
        st.plotly_chart(fig_bt, use_container_width=True, key="chart_bt")

        anuales = cached_retornos_anuales(retorno_port, retorno_bench)
        fig_anuales = go.Figure()
        fig_anuales.add_trace(go.Bar(x=anuales.index.astype(str), y=anuales["Portafolio GaLa"],
            name="Motor GaLa", marker_color="#4488ff"))
        fig_anuales.add_trace(go.Bar(x=anuales.index.astype(str), y=anuales["Benchmark"],
            name=benchmark_ticker, marker_color="rgba(200,200,200,0.5)"))
        fig_anuales.add_hline(y=0, line_color="white", line_width=0.5)
        fig_anuales.update_layout(template="plotly_dark", barmode="group",
            xaxis_title="Año", yaxis_title="Retorno (%)", height=360, legend=dict(x=0.01, y=0.99))
        st.plotly_chart(fig_anuales, use_container_width=True, key="chart_anuales")

        # Monte Carlo
        st.markdown("---")
        _header("Distribución t-Student · Fat tails calibrados", "Proyección de Capital — Monte Carlo")
        retorno_port_mc = retornos_diarios @ pesos_opt
        escenarios, p5, p25, p50, p75, p95, benchmark_fijo, df_t = simular_capital(
            capital_inicial=capital_inicial, aportacion_periodica=aportacion_mensual,
            rendimiento_anual=ret_opt, volatilidad_anual=vol_opt,
            meses=horizonte_años*12, frecuencia_aportacion=frecuencia_aportacion,
            tasa_benchmark=tasa_actual_banxico, num_simulaciones=num_sims,
            retornos_diarios=retorno_port_mc)

        st.caption(
            f"Modelo calibrado con distribución t-Student — grados de libertad: {df_t:.2f} "
            f"({'cola pesada severa' if df_t < 5 else 'cola pesada moderada' if df_t < 10 else 'aproximación normal'})"
        )

        fig_mc = go.Figure()
        for i in range(min(20, escenarios.shape[1])):
            fig_mc.add_trace(go.Scatter(y=escenarios[:,i], mode="lines",
                line=dict(width=1, color="rgba(0,150,255,0.07)"), showlegend=False, hoverinfo="skip"))
        fig_mc.add_trace(go.Scatter(y=p75, mode="lines",
            line=dict(width=1.5, color="rgba(23,195,123,0.4)", dash="dash"), name="Moderado favorable (P75)"))
        fig_mc.add_trace(go.Scatter(y=p25, mode="lines",
            line=dict(width=1.5, color="rgba(255,75,75,0.4)", dash="dash"), name="Moderado adverso (P25)"))
        fig_mc.add_trace(go.Scatter(y=p50, mode="lines",
            line=dict(width=3, color="#17C37B"), name="Base (P50)"))
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

        # Matriz de hitos
        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace; font-size: 10px;
            letter-spacing: 0.12em; text-transform: uppercase;
            color: #5A6780; margin: 1.5rem 0 0.5rem;
        '>Matriz de capitalización por horizonte temporal</div>
        """, unsafe_allow_html=True)
        st.caption("Comparativa del escenario base (P50) vs tasa fija en hitos clave.")

        n_meses_total = horizonte_años * 12
        hitos_meses   = list(dict.fromkeys([m for m in [12, 36, 60, n_meses_total] if m <= n_meses_total]))
        hitos_labels  = {12: "1 año", 36: "3 años", 60: "5 años", n_meses_total: f"{horizonte_años} años (fin)"}

        filas_hitos = []
        for m in hitos_meses:
            idx = min(m, len(p50) - 1)
            filas_hitos.append({
                "Horizonte":           hitos_labels.get(m, f"Mes {m}"),
                "Adverso P5 (MXN)":   int(p5[idx]),
                "Base P50 (MXN)":     int(p50[idx]),
                "Favorable P95 (MXN)":int(p95[idx]),
                "Tasa fija (MXN)":    int(benchmark_fijo[idx]),
                "Ventaja P50 vs Fija":int(p50[idx] - benchmark_fijo[idx]),
            })
        st.dataframe(pd.DataFrame(filas_hitos), use_container_width=True, hide_index=True,
            column_config={
                "Adverso P5 (MXN)":   st.column_config.NumberColumn(format="$%d"),
                "Base P50 (MXN)":     st.column_config.NumberColumn(format="$%d"),
                "Favorable P95 (MXN)":st.column_config.NumberColumn(format="$%d"),
                "Tasa fija (MXN)":    st.column_config.NumberColumn(format="$%d"),
                "Ventaja P50 vs Fija":st.column_config.NumberColumn(format="$%d"),
            })

        # Riesgo institucional
        st.markdown("---")
        _header("Análisis de Riesgo Institucional", "VaR · CVaR · Drawdown · Stress Test")
        capital_riesgo      = st.number_input("Capital de referencia (USD)", value=200_000, step=10_000)
        retorno_port_diario = retornos_diarios @ pesos_opt

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin:1.5rem 0 .75rem;'>Value at Risk y Expected Shortfall</div>""", unsafe_allow_html=True)
        var_cvar = cached_var_cvar(retorno_port_diario, capital_riesgo)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("VaR 95% Histórico", f"{var_cvar['VaR_95_hist']*100:.2f}%", f"-${abs(var_cvar['VaR_95_hist'])*capital_riesgo:,.0f} USD")
        c2.metric("VaR 99% Histórico", f"{var_cvar['VaR_99_hist']*100:.2f}%", f"-${abs(var_cvar['VaR_99_hist'])*capital_riesgo:,.0f} USD")
        c3.metric("CVaR 95%",          f"{var_cvar['CVaR_95']*100:.2f}%",     f"-${abs(var_cvar['CVaR_95'])*capital_riesgo:,.0f} USD")
        c4.metric("CVaR 99%",          f"{var_cvar['CVaR_99']*100:.2f}%",     f"-${abs(var_cvar['CVaR_99'])*capital_riesgo:,.0f} USD")

        fig_var = go.Figure()
        fig_var.add_trace(go.Histogram(x=retorno_port_diario*100, nbinsx=80,
            marker_color="rgba(68,136,255,0.7)", name="Retornos diarios"))
        fig_var.add_vline(x=var_cvar["VaR_95_hist"]*100, line_color="red",    line_dash="dash",  annotation_text="VaR 95%")
        fig_var.add_vline(x=var_cvar["CVaR_95"]*100,     line_color="orange", line_dash="dash",  annotation_text="CVaR 95%")
        fig_var.add_vline(x=var_cvar["VaR_99_hist"]*100, line_color="magenta",line_dash="dot",   annotation_text="VaR 99%")
        fig_var.update_layout(template="plotly_dark", height=380, xaxis_title="Retorno Diario (%)", yaxis_title="Frecuencia")
        st.plotly_chart(fig_var, use_container_width=True, key="chart_var")

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin:1.5rem 0 .75rem;'>Maximum Drawdown</div>""", unsafe_allow_html=True)
        dd_serie, max_dd, inicio_dd, fin_dd, duracion_dd = cached_drawdown(retorno_port_diario)
        c1,c2,c3 = st.columns(3)
        c1.metric("Maximum Drawdown", f"{max_dd*100:.2f}%", f"-${abs(max_dd)*capital_riesgo:,.0f} USD")
        c2.metric("Duración",         f"{duracion_dd} días ({duracion_dd//30} meses)")
        c3.metric("Período",          f"{inicio_dd.strftime('%b %Y')} — {fin_dd.strftime('%b %Y')}")

        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=dd_serie.index, y=dd_serie*100,
            fill="tozeroy", fillcolor="rgba(255,68,68,0.3)", line=dict(color="red", width=1), name="Drawdown"))
        fig_dd.add_hline(y=max_dd*100, line_color="gold", line_dash="dash", annotation_text=f"Max DD: {max_dd*100:.2f}%")
        fig_dd.update_layout(template="plotly_dark", height=350, xaxis_title="Fecha", yaxis_title="Drawdown (%)")
        st.plotly_chart(fig_dd, use_container_width=True, key="chart_dd")

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin:1.5rem 0 .75rem;'>Sortino vs Sharpe</div>""", unsafe_allow_html=True)
        sortino, desv_down = cached_sortino(retorno_port_diario, ret_opt, tasa_rf)
        c1,c2,c3 = st.columns(3)
        c1.metric("Ratio de Sharpe",          f"{sharpe_opt:.4f}")
        c2.metric("Ratio de Sortino",         f"{sortino:.4f}")
        c3.metric("Desviación downside anual",f"{desv_down*100:.2f}%")

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin:1.5rem 0 .75rem;'>Stress Testing — Escenarios Históricos</div>""", unsafe_allow_html=True)
        df_stress = cached_stress_test(pesos_opt, tickers, capital_riesgo, retornos_diarios)
        fig_stress = go.Figure(go.Bar(
            x=df_stress["Pérdida (%)"], y=df_stress["Escenario"], orientation="h",
            marker_color=["red" if p < -15 else "orange" if p < -8 else "gold" for p in df_stress["Pérdida (%)"]],
            text=[f"{p:.1f}%" for p in df_stress["Pérdida (%)"]],
            textposition="outside"))
        fig_stress.update_layout(template="plotly_dark", height=350, xaxis_title="Impacto en Capital (%)")
        st.plotly_chart(fig_stress, use_container_width=True, key="chart_stress")
        st.dataframe(df_stress, use_container_width=True)

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin:1.5rem 0 .75rem;'>Correlación Dinámica Rolling — 60 días</div>""", unsafe_allow_html=True)
        fig_corr   = None
        pares_corr = calcular_correlacion_rolling(retornos_diarios)
        if pares_corr:
            fig_corr = go.Figure()
            for (nombre, serie), color in zip(pares_corr.items(), ["gold", "rgba(68,136,255,0.9)"]):
                fig_corr.add_trace(go.Scatter(x=serie.index, y=serie, mode="lines",
                    line=dict(width=1.5, color=color), name=nombre))
            fig_corr.add_hline(y=0.6,  line_color="rgba(255,0,0,0.5)",  line_dash="dot",  annotation_text="Zona de riesgo")
            fig_corr.add_hline(y=0,    line_color="gray", line_dash="solid", line_width=0.5)
            fig_corr.add_hline(y=-0.6, line_color="rgba(0,255,0,0.5)", line_dash="dot",  annotation_text="Zona de cobertura")
            fig_corr.update_layout(template="plotly_dark", height=350,
                yaxis=dict(range=[-1.1, 1.1]), xaxis_title="Fecha", yaxis_title="Coeficiente de Pearson")
            st.plotly_chart(fig_corr, use_container_width=True, key="chart_corr")
        else:
            st.info(f"Incluya BTC-USD/SPY o QQQ/TLT para ver correlación dinámica. Tickers actuales: {retornos_diarios.columns.tolist()}")

        # Regímenes HMM
        st.markdown("---")
        _header("Modelo Oculto de Markov", "Detección de Regímenes de Mercado")
        st.caption("El modelo clasifica cada período en régimen normal o de tensión, integrando esta señal al proceso de rebalanceo.")
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
            c2.metric("Régimen de tensión",f"{pct:.1f}%")
        else:
            st.info("Ejecute la optimización para generar el análisis de regímenes.")

        # Reporte PDF
        st.markdown("---")
        _header("Exportar", "Reporte Institucional")
        col_btn_pdf, col_esp = st.columns([1, 3])
        with col_btn_pdf:
            if st.button("Generar reporte PDF", type="primary", use_container_width=True):
                with st.spinner("Generando reporte..."):
                    try:
                        pdf_bytes = generar_reporte(
                            tickers=tickers, pesos_opt=pesos_opt, ret_opt=ret_opt, vol_opt=vol_opt,
                            sharpe_opt=sharpe_opt, sortino=sortino, desv_down=desv_down, df_t=df_t,
                            var_cvar=var_cvar, max_dd=max_dd, duracion_dd=duracion_dd,
                            inicio_dd=inicio_dd, fin_dd=fin_dd, df_stress=df_stress,
                            capital_riesgo=capital_riesgo,
                            p5_final=p5[-1], p25_final=p25[-1], p50_final=p50[-1],
                            p75_final=p75[-1], p95_final=p95[-1], horizonte_años=horizonte_años,
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
    _header("Titulares en tiempo real", "Noticias del Mercado Financiero")
    st.caption("Enfocados en los activos de su portafolio y contexto macroeconómico.")

    opciones_noticias = {
        "Mercados Globales (S&P 500)": "^GSPC",
        "Tecnología (Nasdaq)":         "QQQ",
        "Fintech & Crypto":            "BTC-USD",
        "Mercado Mexicano":            "^MXX",
    }

    tickers_usuario = []
    if "tickers_procesar" in st.session_state and st.session_state["tickers_procesar"]:
        crudos = st.session_state["tickers_procesar"].split(",")
        tickers_usuario = [t.strip().upper() for t in crudos if t.strip() and t.strip().upper() not in ["CASH"]]

    if tickers_usuario:
        opciones_noticias = {"Mi Portafolio (Resumen)": "PORTAFOLIO"} | opciones_noticias
        for t in tickers_usuario:
            opciones_noticias[f"Activo específico: {t}"] = t

    categoria_sel   = st.selectbox("Enfoque de las noticias", list(opciones_noticias.keys()))
    ticker_objetivo = opciones_noticias[categoria_sel]

    @st.cache_data(show_spinner=False, ttl=1200)
    def obtener_noticias(ticker_query: str, lista_portafolio: list) -> list:
        noticias_agregadas = []
        try:
            if ticker_query == "PORTAFOLIO":
                top_tickers = lista_portafolio[:5]
                for t in top_tickers:
                    try:
                        data = yf.Ticker(t).news
                        if isinstance(data, list):
                            for n in data:
                                if isinstance(n, dict):
                                    n['origen_ticker'] = t
                            noticias_agregadas.extend([n for n in data if isinstance(n, dict)])
                    except Exception:
                        continue
                noticias_agregadas.sort(key=lambda item: item.get("providerPublishTime", 0), reverse=True)
                return noticias_agregadas
            else:
                data = yf.Ticker(ticker_query).news
                if isinstance(data, list):
                    for n in data:
                        if isinstance(n, dict):
                            n['origen_ticker'] = ticker_query if ticker_query not in ["^GSPC","QQQ","BTC-USD","^MXX"] else ""
                    return [n for n in data if isinstance(n, dict)]
                return []
        except Exception:
            return noticias_agregadas

    with st.spinner("Sincronizando con terminales de noticias..."):
        noticias = obtener_noticias(ticker_objetivo, tickers_usuario)

    if not noticias:
        st.info("No hay noticias recientes disponibles para esta selección.")
    else:
        for n in noticias[:15]:
            try:
                titulo = n.get("title") or n.get("headline")
                if not titulo and "content" in n and isinstance(n["content"], dict):
                    titulo = n["content"].get("title")
                titulo = titulo or "Actualización de mercado"

                publisher = n.get("publisher") or n.get("source")
                if not publisher and "content" in n and isinstance(n["content"], dict):
                    provider = n["content"].get("provider", {})
                    if isinstance(provider, dict):
                        publisher = provider.get("displayName")
                publisher = publisher or "Yahoo Finance"

                link_crudo = n.get("link") or n.get("url")
                if not link_crudo and "content" in n and isinstance(n["content"], dict):
                    click_url = n["content"].get("clickThroughUrl", {})
                    if isinstance(click_url, dict):
                        link_crudo = click_url.get("url")

                origen = n.get("origen_ticker", "")
                if isinstance(link_crudo, str) and link_crudo.startswith("http"):
                    url_destino = link_crudo
                elif isinstance(link_crudo, str) and link_crudo.startswith("/"):
                    url_destino = f"https://finance.yahoo.com{link_crudo}"
                else:
                    ticker_url  = origen if origen else (ticker_objetivo if ticker_objetivo != "PORTAFOLIO" else "SPY")
                    ticker_url  = str(ticker_url).replace("^", "%5E")
                    url_destino = f"https://finance.yahoo.com/quote/{ticker_url}/news"

                ts = n.get("providerPublishTime")
                try:
                    fecha = datetime.fromtimestamp(int(ts)).strftime("%d %b %Y  %H:%M") if ts else "Reciente"
                except Exception:
                    fecha = "Reciente"

                with st.container():
                    col_txt, col_btn = st.columns([5, 1])
                    with col_txt:
                        etiqueta = f"**[{origen}]** " if origen else ""
                        st.markdown(f"{etiqueta}**{titulo}**")
                        st.caption(f"{publisher}  ·  {fecha}")
                    with col_btn:
                        st.link_button("Leer", url_destino, use_container_width=True)
                st.markdown("---")
            except Exception:
                continue

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GLOSARIO TÉCNICO
# ══════════════════════════════════════════════════════════════════════════════
with tab_glosario:
    _header("Referencia cuantitativa", "Glosario Técnico")
    st.caption("Comprenderlos convierte el uso de la herramienta en formación financiera aplicada.")

    terminos = {
        "Ratio de Sharpe": "Mide el rendimiento excedente por unidad de riesgo total. Fórmula: (Retorno - Tasa libre de riesgo) / Volatilidad. Un Sharpe > 1 se considera sólido; > 2, excepcional.",
        "Ratio de Sortino": "Variante del Sharpe que solo penaliza la volatilidad negativa (downside). Más relevante cuando la distribución de retornos es asimétrica. Fórmula: (Retorno - MAR) / Desviación Downside.",
        "Value at Risk (VaR)": "Pérdida máxima esperada en un período dado con un nivel de confianza específico. VaR 95%: en el 95% de los días, la pérdida no superará este valor. Limitación: no dice nada sobre qué ocurre en el 5% restante.",
        "CVaR / Expected Shortfall": "Complemento del VaR. Mide la pérdida promedio en los escenarios que sí superan el VaR. Más conservador y preferido por reguladores (Basilea III). Si las cosas salen mal, ¿cuánto se pierde en promedio?",
        "Maximum Drawdown": "Caída máxima desde un pico hasta el valle más profundo antes de recuperarse. Mide el peor escenario histórico experimentado. Fundamental para evaluar la resistencia financiera al riesgo.",
        "Calmar Ratio": "CAGR dividido entre el Maximum Drawdown en valor absoluto. Evalúa el rendimiento en relación a la peor caída histórica. Útil para comparar estrategias con distintos perfiles de riesgo.",
        "Alpha (Jensen)": "Retorno excedente generado por el portafolio respecto a lo que predice el modelo CAPM. Alpha positivo indica que el gestor agrega valor más allá del mercado. Fórmula: Retorno del portafolio - (Rf + Beta × (Rm - Rf)).",
        "Beta": "Sensibilidad del portafolio ante movimientos del benchmark. Beta = 1: mueve igual que el mercado. Beta < 1: menos volátil. Beta > 1: más volátil. Beta negativo: dirección opuesta al mercado.",
        "Optimización SLSQP": "Sequential Least Squares Quadratic Programming. Algoritmo numérico que encuentra los pesos que maximizan el Sharpe respetando restricciones de concentración y Glide Path. Más preciso que la búsqueda aleatoria de Monte Carlo.",
        "Frontera Eficiente (Markowitz)": "Conjunto de portafolios que maximizan el retorno para cada nivel de riesgo dado. Desarrollada por Harry Markowitz (Nobel de Economía 1990). El portafolio óptimo está en la frontera; cualquier otro es subóptimo.",
        "Glide Path Actuarial": "Reducción gradual de la exposición a riesgo conforme se acerca el horizonte de liquidación. Concepto tomado de los fondos de ciclo de vida (target-date funds). En el motor: la exposición máxima a renta variable disminuye con los años.",
        "Modelo Oculto de Markov (HMM)": "Modelo estadístico que clasifica cada período en estados ocultos del mercado (régimen normal vs régimen de tensión). En el backtesting, activa cobertura automática cuando detecta régimen de pánico.",
        "Monte Carlo (t-Student)": "Simulación de miles de trayectorias posibles del capital usando números aleatorios. La distribución t-Student captura fat tails: eventos extremos más frecuentes que en la normal. Los grados de libertad se calibran con datos históricos reales.",
        "Fat Tails": "Colas pesadas de una distribución estadística. Indican que los eventos extremos ocurren con mayor frecuencia de lo que predice una distribución normal. Por eso el motor usa t-Student en lugar de distribución gaussiana.",
        "Backtesting Walk-Forward": "Metodología de prueba histórica sin look-ahead bias. Los pesos se recalculan periódicamente usando solo datos disponibles hasta ese momento. Estándar institucional: evita el error de optimizar con información del futuro.",
        "K-Means Clustering": "Algoritmo de machine learning no supervisado que agrupa activos por similitud de perfil fundamental. En el motor: garantiza representantes de distintos clusters, evitando concentración sectorial disfrazada de diversificación.",
        "CAGR": "Compound Annual Growth Rate — Tasa de Crecimiento Anual Compuesta. Mide el rendimiento anualizado considerando el efecto del interés compuesto. Fórmula: (Valor final / Valor inicial)^(1/años) - 1.",
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
    _header("Espacio de intercambio", "Comunidad GaLa Premium")
    st.caption("Los posts son revisados antes de publicarse para garantizar un entorno de valor y respeto.")

    with st.expander("Normas de participación", expanded=False):
        st.markdown("""
        - El contenido debe ser relevante para finanzas, inversión, gestión de capital o mercados.
        - Se prohíben recomendaciones específicas de compra o venta de activos.
        - No se permiten publicaciones de carácter promocional, político o irrespetuoso.
        - Los posts son moderados antes de aparecer públicamente.
        - El equipo de Motor GaLa se reserva el derecho de rechazar cualquier publicación.
        """)

    st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin:1.5rem 0 .75rem;'>Nueva publicación</div>""", unsafe_allow_html=True)
    with st.form("form_comunidad"):
        titulo_post    = st.text_input("Título", placeholder="Ej. Análisis del sector energético mexicano Q2 2026")
        categoria_post = st.selectbox("Categoría", ["Análisis de mercado","Estrategia de inversión",
            "Macro y economía","Fintech y tecnología","Gestión de riesgo","Pregunta a la comunidad"])
        contenido_post = st.text_area("Contenido",
            placeholder="Comparta su análisis, perspectiva o pregunta...", height=150)
        post_btn = st.form_submit_button("Enviar para revisión", use_container_width=True)

    if post_btn:
        if not titulo_post.strip() or not contenido_post.strip():
            st.warning("Complete el título y el contenido antes de enviar.")
        elif len(contenido_post.strip()) < 50:
            st.warning("El contenido debe tener al menos 50 caracteres.")
        else:
            ok, error_db = guardar_post({
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
                st.error(f"Error al guardar el post. Detalle: {error_db}")

    st.markdown("---")
    st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin-bottom:.75rem;'>Publicaciones recientes</div>""", unsafe_allow_html=True)

    try:
        posts = obtener_posts_aprobados()
    except Exception:
        posts = []
        st.error("Error de conexión con el servidor de la comunidad.")

    if not posts:
        st.info("Aún no hay publicaciones aprobadas. Sea el primero en contribuir.")
    else:
        for post in posts:
            with st.container():
                col_meta, col_cat = st.columns([3, 1])
                with col_meta:
                    st.markdown(f"**{post['titulo']}**")
                    fecha = datetime.fromisoformat(post["created_at"].replace("Z","")).strftime("%d %b %Y")
                    st.caption(f"{post.get('nombre_display','Anónimo')}  ·  {fecha}")
                with col_cat:
                    st.caption(post.get("categoria", "General"))
                st.write(post["contenido"])
                st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — SUGERENCIAS
# ══════════════════════════════════════════════════════════════════════════════
with tab_feedback:
    _header("Desarrollo continuo", "Comentarios y Sugerencias")
    st.caption("Su retroalimentación contribuye directamente al desarrollo del sistema.")

    with st.form("form_feedback_premium"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            contacto_fb = st.text_input("Correo de contacto (opcional)")
        with col_f2:
            tipo_fb = st.selectbox("Tipo de comentario",
                ["Sugerencia de mejora","Reporte de error","Solicitud de funcionalidad","Otro"])
        valoracion = st.select_slider("Valoración general del sistema",
            options=["1 — Deficiente","2 — Regular","3 — Aceptable","4 — Bueno","5 — Excelente"],
            value="4 — Bueno")
        comentario_fb = st.text_area("Comentario",
            placeholder="Describa su experiencia, sugerencia o área de mejora...", height=120)
        enviado = st.form_submit_button("Enviar comentario", use_container_width=True)

    if enviado:
        if comentario_fb.strip():
            ok, error_db = guardar_feedback({
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
                st.error(f"Error al registrar el comentario. Detalle: {error_db}")
        else:
            st.warning("Incluya un comentario antes de enviar.")

# ── Sidebar: info del usuario ──────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(f"**{nombre_display}**")
st.sidebar.caption(usuario["email"])
if tiene_lite:
    st.sidebar.caption("Acceso GaLa Lite — descuento aplicado")
st.sidebar.markdown("---")
st.sidebar.caption(
    "Motor GaLa Premium · Sistema de Gestión de Capital. "
    "Los resultados son producto de modelos matemáticos y no constituyen asesoría de inversión."
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — ADMINISTRACIÓN (OCULTO)
# ══════════════════════════════════════════════════════════════════════════════
if es_admin and tab_admin:
    with tab_admin:
        _header("Acceso restringido", "Centro de Administración")

        sub_mod, sub_feed, sub_users, sub_leads = st.tabs([
            "Moderación",
            "Buzón de Sugerencias",
            "Métricas de Usuarios",
            "Leads Institucionales",
        ])

        with sub_mod:
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin-bottom:.75rem;'>Publicaciones pendientes de revisión</div>""", unsafe_allow_html=True)
            try:
                r_pendientes = db.table("comunidad").select("*").eq("aprobado", False).order("created_at", desc=False).execute()
                posts_pendientes = r_pendientes.data or []
            except Exception as e:
                posts_pendientes = []
                st.error(f"Error de conexión: {e}")

            if not posts_pendientes:
                st.success("Bandeja limpia. No hay publicaciones pendientes.")
            else:
                for p in posts_pendientes:
                    fecha_post = datetime.fromisoformat(p["created_at"].replace("Z","")).strftime("%d %b %H:%M")
                    with st.expander(f"{p['titulo']}  ·  {p['nombre_display']}  ·  {fecha_post}"):
                        st.caption(f"Categoría: {p.get('categoria', 'General')}")
                        st.write(p["contenido"])
                        c1, c2 = st.columns([1, 4])
                        with c1:
                            if st.button("Aprobar", key=f"ap_{p['id']}", type="primary"):
                                db.table("comunidad").update({"aprobado": True}).eq("id", p["id"]).execute()
                                st.rerun()
                        with c2:
                            if st.button("Eliminar", key=f"re_{p['id']}"):
                                db.table("comunidad").delete().eq("id", p["id"]).execute()
                                st.rerun()

        with sub_feed:
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin-bottom:.75rem;'>Retroalimentación directa de los usuarios</div>""", unsafe_allow_html=True)
            try:
                r_feed  = db.table("feedback_premium").select("*").order("created_at", desc=True).limit(20).execute()
                feedbacks = r_feed.data or []
            except Exception:
                feedbacks = []

            if not feedbacks:
                st.info("Aún no hay comentarios en la base de datos.")
            else:
                for f in feedbacks:
                    val = f.get("valoracion", "N/A")
                    with st.container():
                        st.markdown(f"**{f.get('tipo', 'Comentario')}** — {f['nombre_display']}")
                        st.caption(f"Contacto: {f.get('contacto', 'Anónimo')}  ·  Valoración: {val}")
                        st.info(f["comentario"])
                        st.markdown("---")

        with sub_users:
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin-bottom:.75rem;'>Base de datos de adopción</div>""", unsafe_allow_html=True)
            try:
                r_users = db.table("usuarios_premium").select("id, nombre_display, email, tiene_lite, created_at").execute()
                usuarios_totales = r_users.data or []
            except Exception:
                usuarios_totales = []

            if usuarios_totales:
                df_users         = pd.DataFrame(usuarios_totales)
                total_registrados = len(df_users)
                total_lite        = df_users["tiene_lite"].sum() if "tiene_lite" in df_users else 0
                c1, c2, c3 = st.columns(3)
                c1.metric("Usuarios totales",         total_registrados)
                c2.metric("Conversiones GaLa Lite",   total_lite)
                c3.metric("Tasa de conversión Lite",
                          f"{(total_lite/total_registrados)*100:.1f}%" if total_registrados > 0 else "0%")
                st.dataframe(df_users[["nombre_display","email","tiene_lite"]], use_container_width=True)
            else:
                st.info("No se pudieron cargar los datos de usuarios.")

        with sub_leads:
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#5A6780;margin-bottom:.75rem;'>Embudo de ventas — Prospectos corporativos</div>""", unsafe_allow_html=True)
            try:
                r_leads = db.table("leads_b2b").select("*").order("id", desc=True).execute()
                leads   = r_leads.data or []
            except Exception as e:
                leads = []
                st.error(f"Error al conectar con la base de datos B2B: {e}")

            if not leads:
                st.info("La bandeja de prospectos corporativos está vacía.")
            else:
                pendientes = sum(1 for l in leads if not l.get("contactado"))
                if pendientes > 0:
                    st.markdown(f"""
                    <div style='
                        padding: 0.75rem 1.25rem;
                        border: 0.5px solid rgba(212,160,23,0.25);
                        border-left: 2px solid rgba(212,160,23,0.5);
                        border-radius: 4px;
                        background: rgba(212,160,23,0.03);
                        font-family: "DM Mono", monospace;
                        font-size: 11px;
                        color: #d4a017;
                        margin-bottom: 1rem;
                    '>{pendientes} prospecto{"s" if pendientes > 1 else ""} pendiente{"s" if pendientes > 1 else ""} de contactar.</div>
                    """, unsafe_allow_html=True)
                else:
                    st.success("Todos los prospectos han sido contactados.")

                def _estado_lead(contactado: bool) -> str:
                    if contactado:
                        return "<span style='display:inline-flex;align-items:center;gap:5px;font-family:\"DM Mono\",monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#17C37B;'><span style='width:5px;height:5px;background:#17C37B;border-radius:50%;'></span>Contactado</span>"
                    return "<span style='display:inline-flex;align-items:center;gap:5px;font-family:\"DM Mono\",monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#5A6780;'><span style='width:5px;height:5px;background:#5A6780;border-radius:50%;'></span>Pendiente</span>"

                for l in leads:
                    with st.expander(f"{l['empresa']} — {l['nombre']}", expanded=not l.get("contactado")):
                        col_info_l, col_accion = st.columns([3, 1])
                        with col_info_l:
                            st.markdown(_estado_lead(l.get("contactado", False)), unsafe_allow_html=True)
                            st.markdown(f"**Cargo:** {l.get('cargo', 'N/A')}")
                            st.markdown(f"**Email:** `{l.get('email', 'N/A')}`")
                            st.markdown(f"**Área de interés:** {l.get('interes', 'N/A')}")
                        with col_accion:
                            if not l.get("contactado"):
                                if st.button("Registrar contacto", key=f"lead_{l['id']}", type="primary", use_container_width=True):
                                    try:
                                        db.table("leads_b2b").update({"contactado": True}).eq("id", l["id"]).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")
