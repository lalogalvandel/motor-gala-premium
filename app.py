import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib
import bcrypt
import secrets as secrets_lib
import yfinance as yf

from supabase import create_client, Client
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

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Motor GaLa Premium",
    page_icon="logo_gala-removebg-preview.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        /* Ocultar el menú de navegación multipágina nativo de Streamlit */
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)
# ── CSS Institucional ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ... (todo el CSS se mantiene exactamente igual) ... */
/* Tip: Para un modo claro elegante, configura .streamlit/config.toml con:
   [theme]
   base="light"
   primaryColor="#4488FF"
   backgroundColor="#F8F9FA"
   secondaryBackgroundColor="#FFFFFF"
   textColor="#1E232E"
*/
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
    """Devuelve el hash bcrypt de una contraseña (incluye salt)."""
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt()).decode()

def verificar_hash(texto: str, hash_almacenado: str) -> bool:
    """
    Verifica una contraseña contra su hash almacenado.
    Soporta bcrypt (prefijo $2b$/$2a$) y SHA-256 legacy para migración.
    """
    if hash_almacenado.startswith("$2"):
        return bcrypt.checkpw(texto.encode(), hash_almacenado.encode())
    return hashlib.sha256(texto.encode()).hexdigest() == hash_almacenado

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
        
        # ── GENERACIÓN DE BÓVEDA ÚNICA PARA EL NUEVO USUARIO ──
        nuevo_id_corp = f"corp_{secrets_lib.token_hex(6)}"
        
        db.table("usuarios_premium").insert({
            "nombre_display": nombre.strip(),
            "email":          email.strip().lower(),
            "password_hash":  hashear(password),
            "tiene_lite":     lite,
            "id_corp":        nuevo_id_corp  # <── SELLO ÚNICO, IMPOSIBLE DE CRUZAR
        }).execute()
        
        msg = "Cuenta creada. Se detectó acceso GaLa Lite — su descuento ha sido registrado." if lite else "Cuenta creada correctamente."
        return True, msg
    except Exception as e:
        return False, f"Error al registrar: {e}"

def autenticar_premium(email: str, password: str) -> tuple[bool, dict]:
    try:
        r = db.table("usuarios_premium") \
            .select("id, nombre_display, email, tiene_lite, id_corp, configuracion_ui, password_hash") \
            .eq("email", email.strip().lower()) \
            .execute()
        if not r.data:
            return False, {}
        usuario = r.data[0]
        
        if not verificar_hash(password, usuario["password_hash"]):
            return False, {}
        
        # Migración automática a bcrypt
        try:
            if not usuario["password_hash"].startswith("$2"):
                nuevo_hash = hashear(password)
                db.table("usuarios_premium").update({"password_hash": nuevo_hash}).eq("id", usuario["id"]).execute()
        except Exception:
            pass
        
        del usuario["password_hash"]
        return True, usuario
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
        db.table("usuarios_premium").update({"password_hash": hashear(nueva_pass)}).eq("email", email.lower()).execute()
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
        r = db.table("comunidad").select("*").eq("aprobado", True).order("created_at", desc=True).limit(20).execute()
        return r.data or []
    except Exception:
        return []

# ── Utilidades CRM (Gestión de Clientes) ───────────────────────────────────────
def obtener_clientes(id_corp: str) -> list:
    try:
        r = db.table("clientes_asesor").select("*").eq("id_corp", id_corp).order("nombre_cliente").execute()
        return r.data or []
    except Exception:
        return []

def guardar_cliente(datos: dict, id_corp: str) -> tuple[bool, str]:
    try:
        datos["id_corp"] = id_corp
        if "id" in datos and datos["id"]:
            cliente_id = datos.pop("id")
            db.table("clientes_asesor").update(datos).eq("id", cliente_id).execute()
        else:
            db.table("clientes_asesor").insert(datos).execute()
        return True, "Expediente guardado exitosamente en la base de datos corporativa."
    except Exception as e:
        return False, f"Error al guardar: {e}"

# ── Utilidades Tesorería (Wallet) ──────────────────────────────────────────────
def obtener_cuentas_wallet(id_corp: str) -> list:
    try:
        r = db.table("wallet_cuentas").select("id, institucion, tasa_anual, saldo").eq("id_corp", id_corp).order("institucion").execute()
        return r.data or []
    except Exception:
        return []

def agregar_cuenta_wallet(id_asesor: str, id_corp: str, institucion: str, tasa_anual: float, saldo: float) -> tuple[bool, str]:
    try:
        db.table("wallet_cuentas").insert({
            "id_asesor": id_asesor,
            "id_corp": id_corp,
            "institucion": institucion.strip(),
            "tasa_anual": tasa_anual,
            "saldo": saldo
        }).execute()
        return True, "Cuenta aperturada exitosamente."
    except Exception as e:
        return False, f"Error al crear la cuenta: {e}"

from datetime import datetime, timezone

def registrar_transaccion_wallet(id_cuenta: int, saldo_actual: float, tipo: str, antiqued_monto: float, concepto: str) -> tuple[bool, str]:
    try:
        fecha_ahora = datetime.now(timezone.utc).isoformat()
        monto_absoluto = abs(float(antiqued_monto))
        db.table("wallet_movimientos").insert({
            "id_cuenta": int(id_cuenta),
            "tipo": str(tipo),
            "monto": float(antiqued_monto), 
            "concepto": str(concepto).strip(),
            "created_at": fecha_ahora  
        }).execute()
        
        nuevo_saldo = float(saldo_actual)
        if tipo == "INGRESO":
            nuevo_saldo += monto_absoluto
        elif tipo == "GASTO":
            nuevo_saldo -= monto_absoluto
        elif tipo == "AJUSTE MTM":
            nuevo_saldo += float(antiqued_monto) 
            
        db.table("wallet_cuentas").update({"saldo": nuevo_saldo}).eq("id", int(id_cuenta)).execute()
        return True, "Transacción liquidada y saldo actualizado."
    except Exception as e:
        return False, f"Error en la transacción: {e}"

def obtener_historial_movimientos(ids_cuentas: list) -> list:
    if not ids_cuentas:
        return []
    try:
        r = db.table("wallet_movimientos").select("*").in_("id_cuenta", ids_cuentas).order("created_at").limit(10000).execute()
        return r.data or []
    except Exception as e:
        return []

def eliminar_cuenta_wallet(id_cuenta: int) -> tuple[bool, str]:
    try:
        db.table("wallet_cuentas").delete().eq("id", int(id_cuenta)).execute()
        return True, "Cuenta eliminada permanentemente del sistema."
    except Exception as e:
        return False, f"Error al eliminar (asegúrese de transferir los fondos primero): {e}"

# ── NUEVO: GUARDADO DE MEMORIA EN SEGUNDO PLANO ──
def guardar_memoria_ui_premium(peso_max, horizonte, sims):
    try:
        usuario_actual = st.session_state.get("usuario_premium", {})
        if not usuario_actual: return
        nueva_config = {
            "peso_maximo": peso_max,
            "horizonte": horizonte,
            "simulaciones": sims
        }
        db.table("usuarios_premium").update({"configuracion_ui": nueva_config}).eq("id", usuario_actual["id"]).execute()
        # Actualizamos la memoria RAM actual para que no se borre si recargas sin salir de la sesión
        st.session_state["usuario_premium"]["configuracion_ui"] = nueva_config
    except Exception:
        pass

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
    "cliente_activo_id": None,
    "semanas_cotizadas": 1800,
    "salario_promedio": 2000.0,
    "meta_mensual": 30000.0,
    "capital_acumulado": 2000000.0,
    "simular_m40": False,
    "tickers_procesar": "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX",
    "peso_maximo": 40,
    "vistas_bl": [],
    "usar_bl": False,
    "limite_riesgo_manual": 80,
    "modo_privacidad": False, 
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Función de limpieza de estados dependientes del cliente ─────────────────
def limpiar_estados_cliente():
    """Elimina todas las claves de session_state relacionadas con análisis y cliente actual."""
    claves_a_limpiar = [
        "optimizado", "pesos_opt", "ret_opt", "vol_opt", "sharpe_opt",
        "resultados", "df_regimenes", "df_screening", "vistas_bl",
        "usar_bl", "riesgo_objetivo_ldi", "perfil_ldi_nombre",
        "pension_imss", "brecha" 
        # (El cliente_activo_id fue retirado de aquí para evitar el bucle)
    ]
    for clave in claves_a_limpiar:
        if clave in st.session_state:
            del st.session_state[clave]

# Función Helper para ocultar valores sensibles
def f_val(valor, formato="${:,.2f}"):
    return "$ ••••••" if st.session_state.modo_privacidad else formato.format(valor)

# ══════════════════════════════════════════════════════════════════════════════
# LANDING — AUTH  (versión rediseñada y purificada)
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state["usuario_premium"] is None:

    # ── Estilos CSS ─────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* ── Keyframes ──────────────────────────────────────────────────────── */
    @keyframes gl_fadeUp {
      from { opacity: 0; transform: translateY(14px); }
      to   { opacity: 1; transform: translateY(0);    }
    }
    @keyframes gl_fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    @keyframes gl_drawLine {
      from { width: 0%; opacity: 0; }
      to   { width: 100%; opacity: 1; }
    }
    @keyframes gl_numBreathe {
      0%,  100% { opacity: 0.85; text-shadow: 0 0  0px rgba(68,136,255,0.0); }
      50%       { opacity: 1.00; text-shadow: 0 0 16px rgba(68,136,255,0.45); }
    }
    @keyframes gl_ruleGrow {
      from { width: 0; }
      to   { width: 2.75rem; }
    }

    /* ── Hero ───────────────────────────────────────────────────────────── */
    .gl-hero { padding: 3rem 0 1.25rem; }
    .gl-eyebrow {
        font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 0.28em;
        text-transform: uppercase; color: #4488FF; margin-bottom: 1.1rem;
        animation: gl_fadeIn 0.7s ease 0.08s both;
    }
    .gl-headline {
        font-family: 'EB Garamond', Georgia, serif; font-size: clamp(26px, 3.8vw, 46px);
        font-weight: 400; letter-spacing: 0.01em; line-height: 1.12; margin-bottom: 0;
        animation: gl_fadeUp 0.6s ease 0.16s both;
    }
    .gl-headline-rule {
        height: 2px; width: 0; background: linear-gradient(90deg, #4488FF, rgba(68,136,255,0.15));
        margin: 0.85rem 0; animation: gl_ruleGrow 0.9s cubic-bezier(.22,1,.36,1) 0.55s both;
    }
    .gl-tagline {
        font-family: 'EB Garamond', Georgia, serif; font-size: 16.5px; font-style: italic;
        opacity: 0.62; line-height: 1.65; animation: gl_fadeUp 0.6s ease 0.26s both;
    }

    /* ── Stat pills ─────────────────────────────────────────────────────── */
    .gl-pills { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 1.4rem; animation: gl_fadeUp 0.6s ease 0.4s both; }
    .gl-pill {
        display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.28rem 0.7rem;
        border: 0.5px solid rgba(68,136,255,0.22); background: rgba(68,136,255,0.035);
        font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 0.07em;
        color: rgba(255,255,255,0.56); border-radius: 2px; transition: all 0.2s ease;
    }
    .gl-pill:hover { border-color: rgba(68,136,255,0.48); background: rgba(68,136,255,0.07); }
    .gl-pill b { color: #4488FF; font-weight: 400; }

    /* ── Divider animado ────────────────────────────────────────────────── */
    .gl-divider {
        height: 0.5px; width: 0; background: linear-gradient(90deg, rgba(68,136,255,0.55), rgba(68,136,255,0.07), transparent);
        margin: 1.8rem 0 2.4rem; animation: gl_drawLine 1.4s cubic-bezier(.22,1,.36,1) 0.55s both;
    }

    /* ── Etiquetas de sección ───────────────────────────────────────────── */
    .gl-section-label {
        font-family: 'DM Mono', monospace; font-size: 9.5px; letter-spacing: 0.18em;
        text-transform: uppercase; opacity: 0.42; padding-bottom: 0.6rem;
        border-bottom: 0.5px solid rgba(68,136,255,0.1); margin-bottom: 0.9rem;
        animation: gl_fadeIn 0.55s ease 0.72s both;
    }

    /* ── Grid de tarjetas ───────────────────────────────────────────────── */
    .gl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; }
    .gl-card {
        padding: 0.85rem 0.95rem 0.9rem; border: 0.5px solid rgba(68,136,255,0.1);
        background: rgba(68,136,255,0.018); cursor: default;
        transition: all 0.22s ease; animation: gl_fadeUp 0.5s ease both;
    }
    .gl-card:hover {
        border-color: rgba(68,136,255,0.38); background: rgba(68,136,255,0.055);
        transform: translateY(-2px); box-shadow: 0 6px 20px rgba(68,136,255,0.06);
    }
    .gl-card:nth-child(1) { animation-delay: 0.80s; }
    .gl-card:nth-child(2) { animation-delay: 0.90s; }
    .gl-card:nth-child(3) { animation-delay: 1.00s; }
    .gl-card:nth-child(4) { animation-delay: 1.10s; }
    .gl-card:nth-child(5) { animation-delay: 1.20s; }
    .gl-card:nth-child(6) { animation-delay: 1.30s; }
    .gl-card:nth-child(7) { animation-delay: 1.40s; }

    .gl-card-tag { font-family: 'DM Mono', monospace; font-size: 8.5px; letter-spacing: 0.22em; text-transform: uppercase; color: #4488FF; opacity: 0.72; margin-bottom: 0.32rem; }
    .gl-card-title { font-family: 'EB Garamond', Georgia, serif; font-size: 14.5px; font-weight: 500; line-height: 1.3; color: rgba(255,255,255,0.9); margin-bottom: 0.22rem; }
    .gl-card-desc { font-family: 'EB Garamond', Georgia, serif; font-size: 12.5px; font-style: italic; opacity: 0.52; line-height: 1.46; }

    /* Tarjeta ancha — Monte Carlo */
    .gl-card-wide { grid-column: span 2; display: flex; align-items: center; gap: 1.2rem; }
    .gl-big-num { font-family: 'DM Mono', monospace; font-size: 38px; font-weight: 300; color: #4488FF; letter-spacing: -0.035em; line-height: 1; flex-shrink: 0; animation: gl_numBreathe 4.5s ease-in-out 2.2s infinite; }

    /* Columna auth */
    .gl-auth-header { animation: gl_fadeIn 0.55s ease 0.85s both; }

    /* Accesibilidad */
    @media (prefers-reduced-motion: reduce) {
        .gl-eyebrow, .gl-headline, .gl-headline-rule, .gl-tagline, .gl-pills, .gl-divider, .gl-section-label, .gl-card, .gl-big-num, .gl-auth-header {
            animation: none !important; opacity: 1 !important; transform: none !important; width: auto !important;
        }
        .gl-headline-rule { width: 2.75rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Hero ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class='gl-hero'>
        <div class='gl-eyebrow'>Motor GaLa · Sistema Premium</div>
        <div class='gl-headline'>Sistema Institucional de<br>Gestión de Capital</div>
        <div class='gl-headline-rule'></div>
        <div class='gl-tagline'>Optimización cuantitativa de portafolios sobre universos de hasta 500&nbsp;activos. Markowitz&nbsp;·&nbsp;SLSQP&nbsp;·&nbsp;Monte Carlo t-Student&nbsp;·&nbsp;HMM&nbsp;·&nbsp;Glide Path actuarial.</div>
        <div class='gl-pills'>
            <div class='gl-pill'><b>500</b>&thinsp;activos · S&amp;P 500 / NASDAQ 100</div>
            <div class='gl-pill'><b>3,500+</b>&thinsp;simulaciones Monte Carlo</div>
            <div class='gl-pill'><b>HMM</b>&thinsp;detección de régimen</div>
            <div class='gl-pill'><b>LDI</b>&thinsp;Ley 73 · IMSS · Fisher</div>
            <div class='gl-pill'><b>PDF</b>&thinsp;reporte institucional</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Divider
    st.markdown("<div class='gl-divider'></div>", unsafe_allow_html=True)

    # ── Columnas ─────────────────────────────────────────────────────────────
    col_info, col_auth = st.columns([1.3, 1], gap="large")

    with col_info:
        st.markdown("""
        <div class='gl-section-label'>Capacidades del sistema</div>
        <div class='gl-grid'>
            <div class='gl-card'>
                <div class='gl-card-tag'>Selección · ML</div>
                <div class='gl-card-title'>Screening Fundamental</div>
                <div class='gl-card-desc'>S&amp;P 500 y NASDAQ 100 filtrados por Market Cap, P/E, márgenes y Deuda/Capital. Clustering K-Means garantiza diversificación real entre sectores.</div>
            </div>
            <div class='gl-card'>
                <div class='gl-card-tag'>Optimización · SLSQP</div>
                <div class='gl-card-title'>Frontera Eficiente</div>
                <div class='gl-card-desc'>Sharpe máximo bajo restricciones duras de concentración, riesgo y Glide Path actuarial dinámico según horizonte de inversión.</div>
            </div>
            <div class='gl-card'>
                <div class='gl-card-tag'>Riesgo · Métricas</div>
                <div class='gl-card-title'>Gestión de Riesgo Extremo</div>
                <div class='gl-card-desc'>VaR, CVaR, Maximum Drawdown, Sortino. Stress Testing con shocks históricos: COVID, 2008, Bear Market 2022 e impacto cambiario USD/MXN.</div>
            </div>
            <div class='gl-card'>
                <div class='gl-card-tag'>Validación · Walk-Forward</div>
                <div class='gl-card-title'>Backtesting Sin Bias</div>
                <div class='gl-card-desc'>Metodología sin look-ahead bias. Recalibración periódica neta de comisiones operativas. Jensen's Alpha, Calmar y Sortino históricos.</div>
            </div>
            <div class='gl-card'>
                <div class='gl-card-tag'>Regímenes · HMM</div>
                <div class='gl-card-title'>Modelos Ocultos de Markov</div>
                <div class='gl-card-desc'>Detección automática de régimen Normal vs. Pánico/Tensión, integrada al proceso de rebalanceo activo de la cartera.</div>
            </div>
            <div class='gl-card'>
                <div class='gl-card-tag'>Actuarial · LDI</div>
                <div class='gl-card-title'>Modelado Pensional LDI</div>
                <div class='gl-card-desc'>Ley 73, Modalidad 40 topada a 25 UMAs, Ecuación de Fisher en términos reales. Prescripción automática de riesgo por Superávit.</div>
            </div>
            <div class='gl-card gl-card-wide'>
                <div class='gl-big-num'>3,500+</div>
                <div>
                    <div class='gl-card-tag'>Monte Carlo · t-Student</div>
                    <div class='gl-card-title'>Simulación de Escenarios Adversos</div>
                    <div class='gl-card-desc'>Distribuciones de cola pesada (gl ≈ 4) para modelar Cisnes Negros que la distribución gaussiana ignora. Percentiles de riqueza terminal calibrados.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_auth:
        st.markdown("<div class='gl-auth-header gl-section-label'>Acceso al sistema</div>", unsafe_allow_html=True)

        tab_login, tab_reg, tab_reset = st.tabs(["Iniciar sesión", "Crear cuenta", "Recuperar acceso"])

        with tab_login:
            st.caption("Ingrese sus credenciales para acceder al sistema.")
            with st.form("form_login_premium"):
                email_l   = st.text_input("Correo electrónico")
                pass_l    = st.text_input("Contraseña", type="password")
                login_btn = st.form_submit_button("Iniciar sesión", width='stretch')

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
                reg_btn  = st.form_submit_button("Crear cuenta", width='stretch')

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
            st.caption("Ingrese su correo. Se generará un token de recuperación que deberá compartir con la dirección del sistema para validar su identidad.")
            with st.form("form_solicitar_token"):
                email_rst = st.text_input("Correo electrónico registrado")
                sol_btn   = st.form_submit_button("Generar token", width='stretch')

            if sol_btn and email_rst:
                ok, resultado = generar_token_reset(email_rst)
                if ok:
                    st.success("Token generado.")
                    st.code(resultado, language=None)
                else:
                    st.error(resultado)

            with st.form("form_reset_pass"):
                email_r2    = st.text_input("Correo electrónico")
                token_r     = st.text_input("Token recibido")
                nueva_pass  = st.text_input("Nueva contraseña", type="password")
                nueva_pass2 = st.text_input("Confirmar nueva contraseña", type="password")
                reset_btn   = st.form_submit_button("Restablecer contraseña", width='stretch')

            if reset_btn:
                if nueva_pass != nueva_pass2:
                    st.error("Las contraseñas no coinciden.")
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
# Recuperamos la memoria guardada en Supabase (si no hay, inicia vacío)
mem_ui         = usuario.get("configuracion_ui") or {}

# ── Encabezado ─────────────────────────────────────────────────────────────────
col_enc, col_salir = st.columns([3, 1])
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
            letter-spacing: 0.01em;
            line-height: 1.2;
        '>Bienvenido, {nombre_display}</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 15px;
            font-style: italic;
            opacity: 0.7;
            margin-top: 0.25rem;
        '>Sistema Institucional de Gestión de Capital y Análisis de Riesgo{"&ensp;·&ensp;<span style='color:#17C37B;font-style:normal;'>Acceso GaLa Lite — descuento aplicado</span>" if tiene_lite else ""}</div>
    </div>
    """, unsafe_allow_html=True)

with col_salir:
    st.markdown("<div style='padding-top: 2rem;'></div>", unsafe_allow_html=True)
    if st.button("Cerrar sesión", width='stretch'):
        st.session_state["usuario_premium"] = None
        limpiar_estados_cliente()
        st.session_state.clear()
        st.rerun()

st.markdown(
    "<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 0;'></div>",
    unsafe_allow_html=True
)

def _header(eyebrow: str, titulo: str):
    st.markdown(f"""
    <div style='margin: 2rem 0 1.5rem;'>
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            opacity: 0.6;
            margin-bottom: 0.4rem;
        '>{eyebrow}</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 24px;
            font-weight: 400;
        '>{titulo}</div>
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR GLOBAL (ÚNICO)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    # ── 1. Carga optimizada (Adiós al flasheo constante) ──
    tasa_actual_banxico = obtener_tasa_referencia_banxico()
    tasa_rf = tasa_actual_banxico
    st.metric(label="Tasa de Referencia Banxico", value=f"{tasa_actual_banxico * 100:.2f}%")
    margen_sugerido = float(round(tasa_actual_banxico * 100, 1))

    # Sidebar: Módulo CRM - Gestión de Clientes
    st.markdown("---")
    st.subheader("👥 Expedientes (CRM)")

    clientes_db = obtener_clientes(usuario.get("id_corp"))
    nombres_clientes = {c["nombre_cliente"]: c for c in clientes_db}
    opciones_cliente = ["✚ Nuevo Cliente (Sin seleccionar)"] + list(nombres_clientes.keys())

    cliente_seleccionado = st.selectbox("Seleccionar expediente", opciones_cliente)

    # Inyección de datos a la memoria si se selecciona un cliente
    if cliente_seleccionado != "✚ Nuevo Cliente (Sin seleccionar)":
        datos_c = nombres_clientes[cliente_seleccionado]
        if st.session_state.get("cliente_activo_id") != datos_c["id"]:
            st.session_state["cliente_activo_id"] = datos_c["id"]
            limpiar_estados_cliente()
            
            # ── AQUÍ VA EL BLINDAJE CONTRA VALORES NULL DE LA BASE DE DATOS ──
            val_semanas = datos_c.get("semanas_cotizadas")
            st.session_state["semanas_cotizadas"] = int(val_semanas) if val_semanas is not None else 1800
            
            val_salario = datos_c.get("salario_promedio")
            st.session_state["salario_promedio"]  = float(val_salario) if val_salario is not None else 2000.0
            
            val_meta = datos_c.get("meta_mensual")
            st.session_state["meta_mensual"]      = float(val_meta) if val_meta is not None else 30000.0
            
            val_capital = datos_c.get("capital_acumulado")
            st.session_state["capital_acumulado"] = float(val_capital) if val_capital is not None else 2000000.0
            
            val_sim = datos_c.get("simular_m40")
            st.session_state["simular_m40"]       = bool(val_sim) if val_sim is not None else False
            
            val_tickers = datos_c.get("tickers_guardados")
            st.session_state["tickers_procesar"]  = str(val_tickers) if (val_tickers is not None and str(val_tickers).strip() != "") else "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"
            
            # Blindaje para la variable del peso máximo
            pm_db = datos_c.get("peso_maximo")
            if pm_db is not None:
                if isinstance(pm_db, float) and pm_db <= 1.0:
                    pm_db = int(pm_db * 100)
                st.session_state["peso_maximo_val"] = int(pm_db)
            else:
                st.session_state["peso_maximo_val"] = 40
            # ──────────────────────────────────────────────────────────────────
    
            st.rerun()
        st.caption("Cargado desde base de datos")
    else:
        if st.session_state.get("cliente_activo_id") is not None:
            st.session_state["cliente_activo_id"] = None
            limpiar_estados_cliente()
            st.rerun()
    
    # Botón para guardar el progreso
    with st.expander("Guardar cambios al expediente", expanded=False):
        nuevo_nombre = st.text_input("Nombre del cliente", value=cliente_seleccionado if cliente_seleccionado != "✚ Nuevo Cliente (Sin seleccionar)" else "")
        if st.button("Guardar Perfil Completo", width='stretch'):
            if not nuevo_nombre.strip():
                st.warning("Ingrese un nombre.")
            else:
                datos_guardar = {
                    "id_asesor": usuario["id"],
                    "nombre_cliente": nuevo_nombre.strip(),
                    "semanas_cotizadas": st.session_state.get("semanas_cotizadas", 1800),
                    "salario_promedio": st.session_state.get("salario_promedio", 2000.0),
                    "meta_mensual": st.session_state.get("meta_mensual", 30000.0),
                    "capital_acumulado": st.session_state.get("capital_acumulado", 2000000.0),
                    "simular_m40": st.session_state.get("simular_m40", False),
                    "tickers_guardados": st.session_state.get("tickers_procesar", "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"),
                    "peso_maximo": st.session_state.get("peso_maximo_val", 40)
                }
                if cliente_seleccionado != "✚ Nuevo Cliente (Sin seleccionar)" and nuevo_nombre == cliente_seleccionado:
                    datos_guardar["id"] = st.session_state["cliente_activo_id"]
    
                ok, msg = guardar_cliente(datos_guardar, usuario.get("id_corp"))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ── 3. Reducción de carga cognitiva (Módulos en Acordeón) ──
    st.markdown("---")
    with st.expander("1. Análisis Fundamental (Screening)", expanded=False):
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
                ejecutar_scr  = st.form_submit_button("Ejecutar análisis fundamental", width='stretch')
        else:
            ejecutar_scr = False

    # Sidebar: Módulo 2 – Parámetros de Optimización (Núcleo Principal Abierto)
    st.markdown("---")
    st.subheader("2. Parámetros de Optimización")

    # Inyección preventiva para evitar fallos si el key no existe
    if "tickers_procesar" not in st.session_state:
        st.session_state["tickers_procesar"] = st.session_state.get("tickers_screening", "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX") if usar_screening else "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX"

    with st.form("optim_form"):
        # ── RETIRAMOS EL KEY Y FORZAMOS EL VALUE ──
        tickers_actuales = st.session_state.get("tickers_procesar", "IVVPESO.MX, AAPL.MX, WALMEX.MX, CEMEXCPO.MX")
        tickers_input = st.text_area("Activos a optimizar", value=tickers_actuales, height=70)
        fecha_inicio  = st.date_input("Fecha de inicio", value=pd.Timestamp("2020-01-01"))
        fecha_fin     = st.date_input("Fecha de cierre", value=pd.Timestamp("2026-05-08"))
        
        st.markdown("---")
        st.subheader("Restricciones de concentración")
        
        pm_actual = int(st.session_state.get("peso_maximo_val", mem_ui.get("peso_maximo", 40)))
        pm_actual = max(10, min(100, pm_actual))
        
        peso_max_val = st.slider("Exposición máxima por activo (%)", 10, 100, value=pm_actual)
        peso_max = peso_max_val / 100
        
        if "limite_riesgo_manual" not in st.session_state:
            st.session_state["limite_riesgo_manual"] = 80
        peso_min = st.slider("Exposición mínima por activo (%)", 0, 10, 2) / 100
        peso_max = max(peso_max, peso_min)
        
        comision_broker = st.number_input("Comisión operativa (%)", value=0.15, step=0.05) / 100
        
        # ── NUEVO MÓDULO: RENTA FIJA Y LIQUIDEZ (TICKERS SINTÉTICOS) ──
        st.markdown("---")
        st.subheader("Renta Fija / Cuentas a la Vista")
        st.caption("Agregue instrumentos de tasa fija (Sofipos, Pagarés, Cetes). El motor ajustará el límite máximo de inversión según el capital inicial.")
        
        # DataFrame por defecto para que el usuario lo edite
        rf_default = pd.DataFrame([
            {"Instrumento": "Pagaré Mifel", "Tasa Anual (%)": 10.0, "Tope Máximo (MXN)": 500000},
            {"Instrumento": "Nu (Sofipo)", "Tasa Anual (%)": 14.5, "Tope Máximo (MXN)": 200000},
            {"Instrumento": "Cetes Directo", "Tasa Anual (%)": 11.0, "Tope Máximo (MXN)": 10000000}
        ])
        
        # El data_editor permite agregar, borrar o editar cuentas
        df_renta_fija_ui = st.data_editor(
            rf_default, 
            num_rows="dynamic", 
            use_container_width=True,
            hide_index=True,
            key="editor_renta_fija"
        )
        
        activar_renta_fija = st.toggle("Incluir Renta Fija en la Optimización SLSQP", value=True)
        
        st.markdown("---")
        st.subheader("Proyección de capital")
        capital_inicial       = st.number_input("Capital inicial (MXN)", min_value=0, value=100_000, step=10_000)
        frecuencia_aportacion = st.selectbox("Frecuencia de aportación", ["Mensual", "Trimestral", "Anual"], index=2)
        aportacion_mensual    = st.number_input("Aportación periódica (MXN)", min_value=0, value=100_000, step=10_000)
        horizonte_años        = st.slider("Horizonte de inversión (años)", min_value=1, max_value=40, value=int(mem_ui.get("horizonte", 10)))
        num_sims              = st.slider("Simulaciones Monte Carlo", 500, 5000, int(mem_ui.get("simulaciones", 2000)), step=500)
        
        # ── NUEVO: FRENO ACTUARIAL DINÁMICO (ERP) ──
        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
        activar_freno = st.toggle("Activar Freno Actuarial (Reversión a la media)", value=True, key="activar_freno_cagr")
        
        if activar_freno:
            # Calculamos el tope dinámico: Tasa Banxico actual + 6.0% (Prima histórica del S&P500)
            tope_sugerido = float(round((tasa_actual_banxico * 100) + 6.0, 1))
            st.slider(
                "Límite Máximo CAGR (%)", 5.0, 30.0, value=tope_sugerido, step=0.5,
                key="tope_actuarial_slider",
                help=f"Tope dinámico sugerido = Tasa Banxico ({tasa_actual_banxico*100:.2f}%) + Prima de Riesgo (6.0%). Límite para evitar extrapolaciones irracionales."
            )
        
        st.markdown("---")
        st.subheader("Benchmark comparativo")
        PERFILES_BENCHMARK = {
            "Agresivo (S&P 500 — SPY)":            "SPY",
            "Agresivo Tecnológico (Nasdaq — QQQ)": "QQQ",
            "Moderado (Global 60/40 — AOR)":       "AOR",
            "Conservador (Bonos Globales — AGG)":  "AGG",
        }
        benchmark_seleccion = st.selectbox("Perfil del benchmark", list(PERFILES_BENCHMARK.keys()))
        ejecutar = st.form_submit_button("Ejecutar optimización", width='stretch')

        if ejecutar:
            st.session_state["tickers_procesar"] = tickers_input # <── LA REGRESAMOS
            st.session_state["peso_maximo_val"] = peso_max_val
            guardar_memoria_ui_premium(peso_max_val, horizonte_años, num_sims)

    # ── Prescripción Actuarial LDI (ubicada fuera del formulario) ──
    usar_perfil_ldi = False
    if "riesgo_objetivo_ldi" in st.session_state:
        st.markdown("---")
        st.caption("⚙️ Prescripción Actuarial LDI disponible")
        usar_perfil_ldi = st.toggle(
            "Activar límite de riesgo automático (LDI)",
            value=True,
            help="Sobrescribe el riesgo máximo usando el déficit calculado en la Planeación de Retiro."
        )
        if usar_perfil_ldi:
            limite_riesgo_global = st.session_state["riesgo_objetivo_ldi"]
            st.caption(
                f"**Tope de riesgo bloqueado al {limite_riesgo_global*100:.1f}%** "
                f"({st.session_state['perfil_ldi_nombre']})"
            )
            st.caption("*(Proviene de la pestaña Planeación de Retiro. Ajuste los parámetros allí para modificar el límite.)*")

    # ── MÓDULO BLACK-LITTERMAN (También en acordeón para no saturar) ──
    st.markdown("---")
    with st.expander("3. Expectativas de Mercado (Black‑Litterman)", expanded=False):
        usar_bl = st.toggle("Incorporar visión de portafolio", value=st.session_state.get("usar_bl", False))
        st.session_state["usar_bl"] = usar_bl

        vistas_usuario = []
        if usar_bl:
            num_vistas = st.number_input("Número de perspectivas de inversión", 1, 5, 1)
            
            cadena_tickers = st.session_state.get("tickers_procesar", "IVVPESO.MX, AAPL.MX")
            tickers_temp = [t.strip().upper() for t in cadena_tickers.split(",") if t.strip()]
            
            for i in range(num_vistas):
                with st.container():
                    st.markdown(f"**Perspectiva {i+1}**")
                    tipo = st.selectbox("Tipo de expectativa", ["absoluta", "relativa"], key=f"tipo_{i}")
                    activo_1 = st.selectbox("Instrumento de referencia", tickers_temp, key=f"a1_{i}")
            
                    if tipo == "absoluta":
                        rendimiento = st.slider("Retorno esperado anual (%)", -50.0, 50.0, 10.0, step=1.0, key=f"rend_{i}") / 100
                        st.markdown(f"<span style='color:#17C37B;font-size:13px;'>Se proyecta que <b>{activo_1}</b> obtenga un retorno de <b>{rendimiento*100:.1f}%</b>.</span>", unsafe_allow_html=True)
                        vista = {"tipo": "absoluta", "activo_1": activo_1, "rendimiento_esperado": rendimiento}
                    else:
                        activos_rest = [t for t in tickers_temp if t != activo_1]
                        activo_2 = st.selectbox("Instrumento de comparación", activos_rest, key=f"a2_{i}") if activos_rest else activo_1
                        rendimiento = st.slider("Exceso de retorno esperado (%)", 0.0, 50.0, 5.0, step=1.0, key=f"rend_{i}") / 100
                        st.markdown(f"<span style='color:#17C37B;font-size:13px;'>Se estima que <b>{activo_1}</b> supere a <b>{activo_2}</b> en <b>{rendimiento*100:.1f}%</b>.</span>", unsafe_allow_html=True)
                        vista = {"tipo": "relativa", "activo_1": activo_1, "activo_2": activo_2, "rendimiento_esperado": rendimiento}
            
                    confianza = st.select_slider("Grado de certeza en la expectativa", ["Baja", "Media", "Alta"], value="Media", key=f"conf_{i}")
                    vista["confianza"] = confianza
                    vistas_usuario.append(vista)
            
        st.session_state["vistas_bl"] = vistas_usuario

    # Sidebar: Info del usuario
    st.markdown("---")
    st.markdown(f"**{nombre_display}**")
    st.caption(usuario["email"])
    if tiene_lite:
        st.caption("Acceso GaLa Lite — descuento aplicado")
    st.markdown("---")
    st.caption("Motor GaLa Premium · Sistema Institucional")

# ══════════════════════════════════════════════════════════════════════════════
# CACHÉ DE FUNCIONES Y SETUP DE TABS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, ttl=86400)
def cached_descargar_fundamentales(tickers):
    return descargar_fundamentales_paralelo(tickers, max_workers=3)
    
@st.cache_data(show_spinner=False, ttl=86400)
def obtener_pesos_mercado(tickers_list):
    df_fund = cached_descargar_fundamentales(tuple(tickers_list))
    if df_fund.empty or "Market Cap (B)" not in df_fund.columns:
        return pd.Series(1.0 / len(tickers_list), index=tickers_list)
    
    caps = df_fund.set_index("Ticker")["Market Cap (B)"]
    caps = caps.fillna(caps.median())
    caps = caps.replace(0, caps.median())
    pesos = caps / caps.sum()
    return pesos

@st.cache_data(show_spinner=False, ttl=3600)
def obtener_datos(tickers_key: str, inicio: str, fin: str):
    tickers_list = [t.strip() for t in tickers_key.split(",")]
    datos = cargar_datos(tickers_list, inicio, fin)
    retornos_diarios, retornos_anuales, matriz_cov = calcular_retornos(datos)
    return datos, retornos_diarios, retornos_anuales, matriz_cov

# REORDENAMIENTO DE TABS (Flujo Lógico de Banca de Inversión)
tabs_nombres = ["Dashboard Patrimonial", "Motor Cuantitativo", "Planeación LDI", "Noticias del Mercado", "Comunidad", "Glosario Técnico", "Sugerencias"]
if es_admin: tabs_nombres.append("Administración")

tabs_objetos  = st.tabs(tabs_nombres)
tab_wallet    = tabs_objetos[0]
tab_motor     = tabs_objetos[1]
tab_retiro    = tabs_objetos[2] 
tab_noticias  = tabs_objetos[3]
tab_comunidad = tabs_objetos[4]
tab_glosario  = tabs_objetos[5]
tab_feedback  = tabs_objetos[6]
tab_admin     = tabs_objetos[7] if es_admin else None

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TESORERÍA PATRIMONIAL (WALLET)
# ══════════════════════════════════════════════════════════════════════════════
with tab_wallet:
    col_tit, col_tog = st.columns([4, 1])
    
    with col_tit:
        _header("Consolidación de Activos", "Tesorería y Tracking Patrimonial")
        
    with col_tog:
        # Aquí vive ahora el switch, alineado a la derecha
        st.toggle("Ocultar saldos", key="modo_privacidad")
    
    st.caption("Registro de flujos de efectivo, conciliación de saldos y cálculo de tasa ponderada efectiva.")

    # ── CONEXIÓN REAL A SUPABASE ──
    cuentas_db = obtener_cuentas_wallet(usuario.get("id_corp"))
    
    if not cuentas_db:
        df_cuentas = pd.DataFrame(columns=["id", "institucion", "tasa_anual", "saldo"])
        capital_total = 0.0
    else:
        df_cuentas = pd.DataFrame(cuentas_db)
        df_cuentas = df_cuentas.rename(columns={"institucion": "Institución", "saldo": "Saldo (MXN)", "tasa_anual": "Tasa Anual (%)"})
        capital_total = df_cuentas["Saldo (MXN)"].sum()
    
    mapa_cuentas = dict(zip(df_cuentas["Institución"], df_cuentas["id"])) if not df_cuentas.empty else {}

    # Cálculos actuariales de rendimiento
    if capital_total > 0:
        df_cuentas["Peso (%)"] = (df_cuentas["Saldo (MXN)"] / capital_total) * 100
        tasa_ponderada = (df_cuentas["Tasa Anual (%)"] * (df_cuentas["Peso (%)"] / 100)).sum()
        renta_anual = capital_total * (tasa_ponderada / 100)
    else:
        if not df_cuentas.empty:
            df_cuentas["Peso (%)"] = 0.0
        tasa_ponderada = 0.0
        renta_anual = 0.0

    # 1. DASHBOARD DE POSICIÓN
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Capital Total (AUM)", f_val(capital_total))
    c2.metric("Tasa Efectiva Ponderada", f"{tasa_ponderada:.2f}%")
    c3.metric("Renta Mensual Estimada", f_val(renta_anual/12))
    c4.metric("Renta Diaria Estimada", f_val(renta_anual/365))

    st.markdown("---")

    col_tabla, col_ops = st.columns([1.5, 1], gap="large")

    # 2. ESTADO DE CUENTA
    with col_tabla:
        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Distribución de Capital</div>""", unsafe_allow_html=True)
        if df_cuentas.empty:
            st.info("No hay cuentas registradas. Utilice la 'Mesa de Operaciones' para aperturar su primera cuenta.")
        else:
            df_display = df_cuentas[["Institución", "Saldo (MXN)", "Tasa Anual (%)", "Peso (%)"]].copy()
            if st.session_state.modo_privacidad:
                df_display["Saldo (MXN)"] = "$ ••••••"
                
            st.dataframe(
                df_display,
                width='stretch',
                hide_index=True,
                column_config={
                    "Saldo (MXN)": st.column_config.NumberColumn(format="$%.2f") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
                    "Peso (%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")
                }
            )

    # 3. MESA DE OPERACIONES
    with col_ops:
        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Mesa de Operaciones</div>""", unsafe_allow_html=True)
        
        tab_flujo, tab_transf, tab_mtm, tab_nueva, tab_eliminar = st.tabs(["Flujo", "Transferencia", "MTM", "Nueva", "Eliminar"])

        with tab_transf:
            st.caption("Migración de capital entre cuentas sin alterar el patrimonio total.")
            with st.form("form_transferencia"):
                if len(df_cuentas) >= 2:
                    cta_origen = st.selectbox("Origen (Retiro)", list(mapa_cuentas.keys()), key="cta_orig")
                    cta_destino = st.selectbox("Destino (Aportación)", list(mapa_cuentas.keys()), key="cta_dest")
                    monto_transf = st.number_input("Monto a migrar (MXN)", min_value=1.0, step=1000.0)
                    nota_transf = st.text_input("Concepto", value="Rebalanceo / Migración de tasa")
                    
                    if st.form_submit_button("Ejecutar Transferencia", width='stretch'):
                        if cta_origen == cta_destino:
                            st.warning("Seleccione cuentas distintas para la migración.")
                        else:
                            id_origen = mapa_cuentas[cta_origen]
                            id_destino = mapa_cuentas[cta_destino]
                            saldo_origen = df_cuentas.loc[df_cuentas["id"] == id_origen, "Saldo (MXN)"].values[0]
                            saldo_destino = df_cuentas.loc[df_cuentas["id"] == id_destino, "Saldo (MXN)"].values[0]
                            
                            if monto_transf > saldo_origen:
                                st.error(f"Fondo insuficiente en {cta_origen}.")
                            else:
                                # 1. Retiro de la cuenta origen
                                registrar_transaccion_wallet(id_origen, saldo_origen, "GASTO", monto_transf, f"{nota_transf} (Hacia {cta_destino})")
                                # 2. Aportación a la cuenta destino
                                registrar_transaccion_wallet(id_destino, saldo_destino, "INGRESO", monto_transf, f"{nota_transf} (Desde {cta_origen})")
                                st.success("Migración de capital liquidada exitosamente.")
                                st.rerun()
                else:
                    st.info("Requiere al menos 2 cuentas aperturadas para realizar transferencias.")

        with tab_eliminar:
            st.caption("Cierre definitivo de cuentas inactivas.")
            with st.form("form_eliminar_cuenta"):
                if not df_cuentas.empty:
                    cta_eliminar = st.selectbox("Seleccione la cuenta a cerrar", list(mapa_cuentas.keys()))
                    
                    if st.form_submit_button("Cerrar Cuenta", type="primary", width='stretch'):
                        id_baja = mapa_cuentas[cta_eliminar]
                        saldo_baja = df_cuentas.loc[df_cuentas["id"] == id_baja, "Saldo (MXN)"].values[0]
                        
                        if saldo_baja > 0:
                            st.error("Protocolo de seguridad: No puede eliminar una cuenta con capital activo. Utilice la pestaña 'Transferencia' para vaciarla a $0.00 primero.")
                        else:
                            ok, msg = eliminar_cuenta_wallet(id_baja)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                else:
                    st.info("No hay cuentas disponibles en el sistema.")
        
        with tab_flujo:
            with st.form("form_flujo"):
                if not df_cuentas.empty:
                    cuenta_sel_nom = st.selectbox("Cuenta de origen/destino", list(mapa_cuentas.keys()))
                else:
                    cuenta_sel_nom = st.selectbox("Cuenta de origen/destino", ["(Vacío)"])
                    st.caption("Primero debe aperturar una cuenta.")

                tipo_flujo = st.radio("Tipo de movimiento", ["Aportación (Ingreso)", "Retiro (Gasto)"], horizontal=True)
                monto_flujo = st.number_input("Monto (MXN)", min_value=1.0, step=1000.0)
                nota_flujo = st.text_input("Concepto / Referencia")
                
                if st.form_submit_button("Registrar Transacción", width='stretch'):
                    if not df_cuentas.empty:
                        id_cta = mapa_cuentas[cuenta_sel_nom]
                        saldo_act = df_cuentas.loc[df_cuentas["id"] == id_cta, "Saldo (MXN)"].values[0]
                        tipo_db = "INGRESO" if "Ingreso" in tipo_flujo else "GASTO"
                        
                        if tipo_db == "GASTO" and monto_flujo > saldo_act:
                            st.error("Fondo insuficiente para el retiro.")
                        else:
                            ok, msg = registrar_transaccion_wallet(id_cta, saldo_act, tipo_db, monto_flujo, nota_flujo)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.warning("Debe aperturar una cuenta primero.")
                    
        with tab_mtm:
            st.caption("Concilie el saldo del sistema con el saldo real de su broker (Mark-to-Market).")
            
            if not df_cuentas.empty:
                cuenta_mtm_nom = st.selectbox("Cuenta a conciliar", list(mapa_cuentas.keys()))
                saldo_actual_mtm = df_cuentas.loc[df_cuentas["Institución"] == cuenta_mtm_nom, "Saldo (MXN)"].values[0]
                st.markdown(f"Saldo en sistema: **{f_val(saldo_actual_mtm)}**")
            else:
                cuenta_mtm_nom = st.selectbox("Cuenta a conciliar", ["(Vacío)"])
                saldo_actual_mtm = 0.0
                st.markdown(f"Saldo en sistema: **{f_val(0.0)}**")
                
            with st.form("form_mtm"):
                nuevo_saldo = st.number_input("Saldo real en la plataforma (MXN)", min_value=0.0, value=float(saldo_actual_mtm), step=100.0)
                nota_mtm = st.text_input("Concepto del ajuste", placeholder="Ej. Rendimiento mensual")
                
                if st.form_submit_button("Ejecutar Ajuste a Mercado", width='stretch'):
                    if not df_cuentas.empty:
                        diferencia = nuevo_saldo - saldo_actual_mtm
                        if diferencia == 0:
                            st.success("La cuenta está perfectamente cuadrada.")
                        else:
                            id_cta_mtm = mapa_cuentas[cuenta_mtm_nom]
                            concepto_mtm = nota_mtm if nota_mtm.strip() else "Ajuste Mark-to-Market"
                            
                            ok, msg = registrar_transaccion_wallet(id_cta_mtm, saldo_actual_mtm, "AJUSTE MTM", diferencia, concepto_mtm)
                            if ok:
                                st.success(f"Variación de {f_val(diferencia)} MXN contabilizada.")
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.warning("Debe aperturar una cuenta primero.")

        with tab_nueva:
            with st.form("form_nueva_cuenta"):
                nom_cuenta = st.text_input("Institución o Broker (Ej. Finsus, GBM)")
                tasa_cuenta = st.number_input("Tasa de rendimiento anual esperada (%)", min_value=0.0, step=0.5)
                saldo_ini = st.number_input("Saldo de apertura (MXN)", min_value=0.0, step=1000.0)
                
                if st.form_submit_button("Crear Cuenta Institucional", width='stretch'):
                    if not nom_cuenta.strip():
                        st.warning("Ingrese un nombre de institución válido.")
                    else:
                        ok, msg = agregar_cuenta_wallet(usuario["id"], usuario.get("id_corp"), nom_cuenta, tasa_cuenta, saldo_ini)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    st.markdown("---")
    
    col_tit, col_btn = st.columns([4, 1])
    with col_tit:
        st.subheader("Analítica de Flujos y Evolución de Capital")
    with col_btn:
        if st.button("Refrescar Datos", width='stretch'):
            st.rerun()
    
    if not df_cuentas.empty:
        ids_cuentas = df_cuentas["id"].tolist()
        movimientos_db = obtener_historial_movimientos(ids_cuentas)
        
        if movimientos_db:
            df_movs = pd.DataFrame(movimientos_db)
            
            df_movs["created_at_utc"] = pd.to_datetime(df_movs["created_at"], errors="coerce", utc=True)
            # En lugar de borrarlos, si la fecha es Nula (NaT), le asignamos el momento actual exacto
            df_movs["created_at_utc"] = df_movs["created_at_utc"].fillna(pd.Timestamp.now(tz="UTC"))
            df_movs["Fecha Local"] = df_movs["created_at_utc"].dt.tz_convert("America/Mexico_City").dt.tz_localize(None)
            
            df_movs["Día"] = df_movs["Fecha Local"].dt.floor("D")
            df_movs["Mes"] = df_movs["Fecha Local"].dt.to_period("M").astype(str)
            
            def calcular_flujo(row):
                m = float(row["monto"])
                t = str(row["tipo"]).upper()
                if t == "GASTO": return -abs(m)
                elif t == "INGRESO": return abs(m)
                return m 

            df_movs["Flujo Neto"] = df_movs.apply(calcular_flujo, axis=1)
            
            df_cashflow = df_movs.groupby(["Mes", "tipo"])["Flujo Neto"].sum().unstack(fill_value=0)
            df_diario = df_movs.groupby("Día")["Flujo Neto"].sum().reset_index()
            
            flujo_total_registrado = df_diario["Flujo Neto"].sum()
            capital_semilla = capital_total - flujo_total_registrado
            
            df_diario["Capital Acumulado"] = capital_semilla + df_diario["Flujo Neto"].cumsum()
            df_linea = df_diario.set_index("Día")[["Capital Acumulado"]]

            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Evolución del Patrimonio (AUM)</div>""", unsafe_allow_html=True)
                st.line_chart(df_linea, width='stretch', color="#17C37B")
                
            with col_graf2:
                st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Cash Flow Mensual (Ingresos vs Egresos)</div>""", unsafe_allow_html=True)
                cols_cashflow = []
                if "INGRESO" in df_cashflow.columns: cols_cashflow.append("INGRESO")
                if "GASTO" in df_cashflow.columns: cols_cashflow.append("GASTO")
                
                if cols_cashflow:
                    st.bar_chart(df_cashflow[cols_cashflow], width='stretch')
                else:
                    st.bar_chart(df_cashflow, width='stretch')
            
            with st.expander("Ver Auditoría Completa de Transacciones (Libro Mayor)", expanded=False):
                df_mostrar = df_movs.sort_values("Fecha Local", ascending=False).copy()
                mapa_inverso_cuentas = dict(zip(df_cuentas["id"], df_cuentas["Institución"]))
                df_mostrar["Cuenta"] = df_mostrar["id_cuenta"].map(mapa_inverso_cuentas)
                
                df_mostrar = df_mostrar[["Fecha Local", "Cuenta", "tipo", "monto", "concepto"]]
                df_mostrar.columns = ["Fecha (CDMX)", "Institución", "Tipo", "Monto (MXN)", "Concepto"]
                
                df_mostrar["Fecha (CDMX)"] = df_mostrar["Fecha (CDMX)"].dt.strftime("%Y-%m-%d %H:%M")
                
                if st.session_state.modo_privacidad:
                    df_mostrar["Monto (MXN)"] = "$ ••••••"
                    
                st.dataframe(df_mostrar, width='stretch', hide_index=True)
        else:
            st.info("Aún no hay transacciones históricas para generar la analítica.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MOTOR CUANTITATIVO
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

                    st.success(
                        f"Universo: {len(df_fund)}  |  Tras filtro: {len(df_filtrado)}  "
                        f"|  Representantes: {len(df_mejores)}"
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Instrumentos que superaron el filtro**")
                        st.dataframe(df_clusterizado.sort_values("Profit Margin %", ascending=False),
                                     height=300, width='stretch')
                    with c2:
                        st.markdown("**Selección óptima por cluster**")
                        st.dataframe(df_mejores[["Ticker","Nombre","Sector","Cluster",
                                                 "Market Cap (B)","P/E Ratio","Profit Margin %"]],
                                     height=300, width='stretch')
                    st.info(f"Cartera sugerida (guardada en memoria): **{tickers_sugeridos}**")

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
            opacity: 0.8;
        '>Configure los parámetros en el panel izquierdo y ejecute la optimización para iniciar el análisis.</div>
        """, unsafe_allow_html=True)
    else:
        benchmark_elegido = PERFILES_BENCHMARK[benchmark_seleccion]
        if ejecutar:
            # Eliminamos la línea conflictiva, el Sidebar ya actualiza los tickers automáticamente
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
                datos            = datos_full[tickers].copy()
                retornos_diarios = retornos_full[tickers].copy()
                retornos_para_bt = retornos_full
                _, retornos_anuales, matriz_cov = calcular_retornos(datos)
        except Exception as e:
            st.error(f"Error al descargar históricos: {e}")
            st.stop()

        if ejecutar:
            with st.spinner("Calibrando motor cuantitativo y análisis de regímenes..."):
                st.session_state.df_regimenes = entrenar_modelo_markov(datos)
                REFUGIOS      = {"TLT","IEF","SHY","BND","AGG","BIL","GLD","IAU","USDC-USD","CASH"}
                es_riesgo     = np.array([0.0 if t.upper() in REFUGIOS else 1.0 for t in tickers])
                num_refugios  = np.sum(es_riesgo == 0.0)
                
                # ── IMPLEMENTACIÓN BLACK-LITTERMAN ──
                if st.session_state.get("usar_bl", False) and len(st.session_state.get("vistas_bl", [])) > 0:
                    pesos_mkt = obtener_pesos_mercado(tickers)
                    retornos_usar, matriz_cov_usar = calcular_black_litterman(
                        retornos_anuales, 
                        matriz_cov, 
                        pesos_mkt, 
                        st.session_state["vistas_bl"], 
                        tasa_rf
                    )
                else:
                    retornos_usar = retornos_anuales
                    matriz_cov_usar = matriz_cov
                    
                    # ── EXPANSIÓN DE MATRIZ: INYECCIÓN DE RENTA FIJA ──
                nombres_activos_finales = list(tickers)
                es_riesgo_final = list(es_riesgo)
                limites_inferiores = [peso_min] * len(tickers)
                limites_superiores = [peso_max] * len(tickers)
                
                if activar_renta_fija and not df_renta_fija_ui.empty:
                    df_rf = df_renta_fija_ui.dropna() # Limpiamos filas vacías
                    
                    for idx, row in df_rf.iterrows():
                        nombre_rf = row["Instrumento"]
                        tasa_rf_act = row["Tasa Anual (%)"] / 100.0
                        tope_mxn = row["Tope Máximo (MXN)"]
                        
                        # 1. Ajuste del Límite Máximo del SLSQP (Transformación de Monto a Peso)
                        # Si el cliente tiene $1,000,000 y el tope es $500,000, el peso máximo es 50%.
                        peso_tope_calculado = min(1.0, tope_mxn / capital_inicial) if capital_inicial > 0 else 1.0
                        
                        # 2. Expansión de las matrices
                        nombres_activos_finales.append(nombre_rf)
                        es_riesgo_final.append(0.0) # Identificador para que el backtest sepa que es refugio
                        
                        # Agregamos la tasa al vector de retornos esperados
                        retornos_usar = pd.concat([retornos_usar, pd.Series({nombre_rf: tasa_rf_act})])
                        # Expansión de retornos_diarios para que el Monte Carlo y Stress Test lo reconozcan
                        tasa_diaria = (1 + tasa_rf_act) ** (1/252) - 1
                        retornos_diarios[nombre_rf] = tasa_diaria
                        
                        # Añadimos una nueva fila y columna a la Matriz de Covarianza (llena de ceros)
                        nueva_fila = pd.DataFrame(0.0, index=[nombre_rf], columns=matriz_cov_usar.columns)
                        matriz_cov_usar = pd.concat([matriz_cov_usar, nueva_fila])
                        matriz_cov_usar[nombre_rf] = 0.0 # Nueva columna
                        
                        # Le damos una volatilidad mínima en la diagonal (1% anual para evitar singularidad matricial)
                        matriz_cov_usar.loc[nombre_rf, nombre_rf] = 0.0001
                        
                        # Guardamos sus restricciones personalizadas para el optimizador
                        limites_inferiores.append(0.0) # La renta fija no tiene mínimo obligatorio
                        limites_superiores.append(peso_tope_calculado)

                # Convertimos de nuevo a array de numpy
                es_riesgo_final = np.array(es_riesgo_final)
                bounds_personalizados = tuple(zip(limites_inferiores, limites_superiores))
                
                # ── LÓGICA DE RESTRICCIÓN DE RIESGO ──
                if usar_perfil_ldi and st.session_state.get("riesgo_objetivo_ldi") is not None:
                    riesgo_maximo_final = float(st.session_state["riesgo_objetivo_ldi"])
                elif not usar_perfil_ldi:
                    riesgo_maximo_final = st.session_state.get("limite_riesgo_manual", 80) / 100
                else:
                    riesgo_maximo_final = min(1.0, max(0.20, horizonte_años / 15.0))
                
                riesgo_maximo_final = max(0.0, min(1.0, riesgo_maximo_final))

                riesgo_minimo_requerido = np.sum(es_riesgo) * peso_min
                if riesgo_maximo_final < riesgo_minimo_requerido:
                    riesgo_maximo_final = riesgo_minimo_requerido + 0.001

                resultados, pesos_guardados = simular_portafolios(retornos_usar, matriz_cov_usar, tasa_rf, num_portafolios=num_sims)
                
                # Convertimos de nuevo a array de numpy
                es_riesgo_final = np.array(es_riesgo_final)
                bounds_personalizados = tuple(zip(limites_inferiores, limites_superiores))

                # ── PURIFICACIÓN DE DATOS PARA SCIPY (PANDAS -> NUMPY) ──
                # Extraemos solo los valores numéricos float64 para que el SLSQP no colapse
                ret_numpy = retornos_usar.to_numpy(dtype=float) if hasattr(retornos_usar, 'to_numpy') else np.array(retornos_usar, dtype=float)
                cov_numpy = matriz_cov_usar.to_numpy(dtype=float) if hasattr(matriz_cov_usar, 'to_numpy') else np.array(matriz_cov_usar, dtype=float)

                # ── LLAMADA CONECTADA AL NUEVO MOTOR ASIMÉTRICO ──
                pesos_opt = optimizar_sharpe_slsqp(
                    ret_numpy, 
                    cov_numpy, 
                    tasa_rf,
                    peso_min=peso_min, 
                    peso_max=peso_max, 
                    max_riesgo_total=riesgo_maximo_final,
                    es_riesgo=es_riesgo_final,
                    bounds_personalizados=bounds_personalizados
                )

                if pesos_opt is None:
                    st.error("**COLAPSO MATEMÁTICO (Restricciones Imposibles):** El optimizador no pudo encontrar una solución porque las reglas chocan entre sí. \n\n**Causa probable:** Su 'Límite de Riesgo' le exige al motor meter mucho capital en liquidez, pero la suma de los 'Topes Máximos' de sus cuentas de Renta Fija es insuficiente para absorber ese dinero. \n\n**Solución:** Agregue un instrumento sin límite (ej. Cetes a 10 Millones) o aumente el límite máximo de exposición por activo.")
                    st.stop() # <── Freno de mano total, no mostramos gráficos falsos
                    
                if len(pesos_opt) != len(nombres_activos_finales):
                    st.error("Error estructural de dimensiones en la matriz de activos.")
                    st.stop()

                ret_opt    = float(np.sum(pesos_opt * retornos_usar))
                vol_opt    = float(np.sqrt(np.dot(pesos_opt.T, np.dot(matriz_cov_usar, pesos_opt))))
                sharpe_opt = float((ret_opt - tasa_rf) / vol_opt)

                st.session_state.optimizado  = True
                st.session_state.pesos_opt   = pesos_opt
                st.session_state.ret_opt     = ret_opt
                st.session_state.vol_opt     = vol_opt
                st.session_state.sharpe_opt  = sharpe_opt
                st.session_state.resultados  = resultados
                
                # ── GUARDAMOS LAS VARIABLES EXPANDIDAS EN MEMORIA ──
                st.session_state.nombres_activos_finales = nombres_activos_finales
                st.session_state.retornos_diarios_exp = retornos_diarios

        res        = st.session_state.resultados
        pesos_opt  = st.session_state.pesos_opt
        ret_opt    = st.session_state.ret_opt
        vol_opt    = st.session_state.vol_opt
        sharpe_opt = st.session_state.sharpe_opt
        
        # ── RECUPERAMOS LAS VARIABLES EXPANDIDAS DE LA MEMORIA ──
        nombres_activos_finales = st.session_state.get("nombres_activos_finales", tickers)
        retornos_diarios = st.session_state.get("retornos_diarios_exp", retornos_diarios)

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
            yaxis_title="Retorno Anual (%)", height=480, legend=dict(x=0.01, y=0.99), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_markowitz, width='stretch', key="chart_markowitz")

        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace; font-size: 10px;
            letter-spacing: 0.12em; text-transform: uppercase;
            opacity: 0.6; margin: 1.5rem 0 0.75rem;
        '>Distribución óptima del capital</div>
        """, unsafe_allow_html=True)
        # Reemplaza la línea que dice "Activo": tickers
        df_pesos = pd.DataFrame({"Activo": nombres_activos_finales, "Peso (%)": (pesos_opt*100).round(2)}) \
            .sort_values("Peso (%)", ascending=False)
        st.dataframe(df_pesos, width='stretch')

        # Rebalanceo
        st.markdown("---")
        _header("Asistente de rebalanceo", "Instrucciones de Asignación")
        st.caption("Instrucciones exactas para asignar el capital según los pesos óptimos. Asume capital en liquidez total.")

        capital_rebalanceo = st.number_input("Capital disponible para asignar (MXN)",
            min_value=0, value=int(capital_inicial), step=10_000, key="capital_rebalanceo",
            help="Por defecto usa el capital inicial configurado.")

        df_rebalanceo = pd.DataFrame({
            "Activo":               nombres_activos_finales,
            "Peso Óptimo (%)":      (pesos_opt * 100).round(2),
            "Monto Objetivo (MXN)": (pesos_opt * capital_rebalanceo).round(0).astype(int),
        }).sort_values("Peso Óptimo (%)", ascending=False).reset_index(drop=True)
        
        # Enmascarar montos si privacidad está activa
        if st.session_state.modo_privacidad:
            df_rebalanceo["Instrucción en Mercado"] = df_rebalanceo["Monto Objetivo (MXN)"].apply(lambda m: "Invertir $ ••••••")
        else:
            df_rebalanceo["Instrucción en Mercado"] = df_rebalanceo["Monto Objetivo (MXN)"].apply(lambda m: f"Invertir ${m:,}")

        st.dataframe(df_rebalanceo[["Activo","Peso Óptimo (%)","Monto Objetivo (MXN)","Instrucción en Mercado"]],
            width='stretch',
            column_config={
                "Monto Objetivo (MXN)": st.column_config.NumberColumn(format="$%d") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
                "Peso Óptimo (%)":      st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.2f%%"),
            })

        total_asignado = df_rebalanceo["Monto Objetivo (MXN)"].sum()
        diferencia     = capital_rebalanceo - total_asignado
        c1, c2, c3 = st.columns(3)
        c1.metric("Capital disponible",    f_val(capital_rebalanceo))
        c2.metric("Total a asignar",       f_val(total_asignado))
        c3.metric("Diferencia (redondeo)", f_val(diferencia),
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
            
            # ── RESTRICCIÓN DE RIESGO PARA BACKTESTING ──
            if usar_perfil_ldi and st.session_state.get("riesgo_objetivo_ldi") is not None:
                riesgo_maximo_bt = float(st.session_state["riesgo_objetivo_ldi"])
            elif not usar_perfil_ldi:
                riesgo_maximo_bt = st.session_state.get("limite_riesgo_manual", 80) / 100
            else:
                riesgo_maximo_bt = min(1.0, max(0.20, horizonte_años / 15.0))
            riesgo_maximo_bt = max(0.0, min(1.0, riesgo_maximo_bt))
            
            df_equity, benchmark_ticker, retorno_port, retorno_bench = correr_backtest(
                retornos_para_bt, 
                tasa_rf, 
                capital_inicial, 
                peso_min, 
                peso_max,
                riesgo_maximo_bt,
                es_riesgo_arr, 
                st.session_state.df_regimenes,
                comision_broker, 
                benchmark_elegido
            )

        metricas_bt = calcular_metricas_backtest(retorno_port, retorno_bench, tasa_rf,
            df_equity["Portafolio GaLa (Dinámico)"], df_equity[f"Benchmark ({benchmark_ticker})"])

        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace; font-size: 10px;
            letter-spacing: 0.12em; text-transform: uppercase;
            opacity: 0.6; margin-bottom: 0.75rem;
        '>Análisis comparativo de rendimiento</div>
        """, unsafe_allow_html=True)
        comparativas = [
            ("CAGR",         f"{metricas_bt['cagr_port']*100:.2f}%",  f"{metricas_bt['cagr_bench']*100:.2f}%"),
            ("Volatilidad",  f"{metricas_bt['vol_port']*100:.2f}%",   f"{metricas_bt['vol_bench']*100:.2f}%"),
            ("Sharpe",       f"{metricas_bt['sharpe_port']:.4f}",       f"{metricas_bt['sharpe_bench']:.4f}"),
            ("Sortino",      f"{metricas_bt['sortino_port']:.4f}",      f"{metricas_bt['sortino_bench']:.4f}"),
            ("Max Drawdown", f"{metricas_bt['mdd_port']*100:.2f}%",   f"{metricas_bt['mdd_bench']*100:.2f}%"),
            ("Calmar",       f"{metricas_bt['calmar_port']:.4f}",       f"{metricas_bt['calmar_bench']:.4f}"),
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
            mode="lines", line=dict(width=1.5, color="rgba(150,150,150,0.6)", dash="dot"), name=benchmark_ticker))
        fig_bt.update_layout(template="plotly_dark", xaxis_title="Fecha", yaxis_title="Capital (USD)",
            height=420, legend=dict(x=0.01, y=0.99), hovermode="x unified", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bt, width='stretch', key="chart_bt")

        capital_anual = df_equity.groupby(df_equity.index.year).last()
        anuales = capital_anual.pct_change().dropna() * 100

        fig_anuales = go.Figure()
        fig_anuales.add_trace(go.Bar(
            x=anuales.index.astype(str), 
            y=anuales["Portafolio GaLa (Dinámico)"],
            name="Motor GaLa", 
            marker_color="#4488ff"
        ))
        fig_anuales.add_trace(go.Bar(
            x=anuales.index.astype(str), 
            y=anuales[f"Benchmark ({benchmark_ticker})"],
            name=benchmark_ticker, 
            marker_color="rgba(150,150,150,0.5)"
        ))
        fig_anuales.add_hline(y=0, line_color="white", line_width=0.5)
        fig_anuales.update_layout(
            template="plotly_dark", 
            barmode="group",
            xaxis_title="Año", 
            yaxis_title="Retorno (%)", 
            height=360, 
            legend=dict(x=0.01, y=0.99),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_anuales, width='stretch', key="chart_anuales")

        # Monte Carlo
        st.markdown("---")
        _header("Distribución t-Student · Fat tails calibrados", "Proyección de Capital — Monte Carlo")
        retorno_port_mc = retornos_diarios @ pesos_opt
        
        # ── LÓGICA DEL HAIRCUT ACTUARIAL BLINDADO ──
        usar_freno = st.session_state.get('activar_freno_cagr', True)
        
        if usar_freno:
            # Leemos el slider (si no existe aún, usamos 15% como seguro de vida)
            tope_act = st.session_state.get('tope_actuarial_slider', 15.0) / 100
            rendimiento_mc = min(ret_opt, tope_act)
            
            if ret_opt > tope_act:
                st.warning(f"**Reversión a la Media:** El portafolio tiene un retorno histórico atípico ({ret_opt*100:.2f}%). Para evitar proyecciones financieras irreales a {horizonte_años} años, la simulación ha topado el interés compuesto al **{tope_act*100:.1f}%**, pero mantiene intacta la alta volatilidad original ({vol_opt*100:.2f}%) para estresar el modelo correctamente.")
            else:
                st.info(f"**Prudencia Actuarial:** Freno encendido (Límite: {tope_act*100:.1f}%), pero el rendimiento histórico ({ret_opt*100:.2f}%) está dentro de parámetros estructurales normales. No se aplicó recorte.")
        else:
            rendimiento_mc = ret_opt
            if ret_opt > 0.20 and horizonte_años > 5:
                st.error(f"**Riesgo de Extrapolación:** El freno actuarial está APAGADO. Está proyectando un retorno del **{ret_opt*100:.2f}%** compuesto anualmente por **{horizonte_años} años**. Esto asume que el portafolio batirá a los mejores gestores de la historia ininterrumpidamente. Úselo solo para visualización a corto plazo.")

        # ── CABLE CONECTADO: INYECCIÓN FISCAL AL MONTE CARLO ──
        usar_fiscal_mc = st.session_state.get('ldi_fiscal', False)
        ingreso_comp_mc = st.session_state.get('ldi_ingreso', 0.0)
        
        # Por defecto, la aportación es la normal de la barra lateral
        aportacion_mc = aportacion_mensual
        
        if usar_fiscal_mc and ingreso_comp_mc > 0:
            ingreso_anual = ingreso_comp_mc * 12
            aport_anual = aportacion_mensual * 12
            limite_10 = ingreso_anual * 0.10
            limite_5u = obtener_uma_actual() * 365 * 5
            
            monto_ded = min(aport_anual, limite_10, limite_5u)
            
            # Tasa marginal ISR dinámica
            if ingreso_comp_mc > 100000: t_isr = 0.34
            elif ingreso_comp_mc > 50000: t_isr = 0.30
            elif ingreso_comp_mc > 25000: t_isr = 0.23
            else: t_isr = 0.15
                
            devolucion_anual = monto_ded * t_isr
            
            # Prorrateamos el cheque del SAT a nivel mensual para inyectarlo al flujo estocástico
            aportacion_mc = aportacion_mensual + (devolucion_anual / 12)
            
            st.success(f"**Efecto Fiscal Activo en Simulación:** El motor estocástico está inyectando **\${devolucion_anual:,.2f} MXN extra al año** provenientes del escudo fiscal (Art. 151), prorrateados en aportaciones de \${devolucion_anual/12:,.2f} al mes libres de riesgo.")

        # ── EJECUCIÓN DEL MOTOR ──
        escenarios, p5, p25, p50, p75, p95, benchmark_fijo, df_t = simular_capital(
            capital_inicial=capital_inicial, 
            aportacion_periodica=aportacion_mc, 
            rendimiento_anual=rendimiento_mc,   # <── Aquí entra la magia: Podado o Puro
            volatilidad_anual=vol_opt,
            meses=horizonte_años*12, 
            frecuencia_aportacion=frecuencia_aportacion,
            tasa_benchmark=tasa_actual_banxico, 
            num_simulaciones=num_sims,
            retornos_diarios=retorno_port_mc
        )

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
            height=480, legend=dict(x=0.01, y=0.99), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_mc, width='stretch', key="chart_mc")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Adverso (P5)",    f_val(p5[-1], "${:,.0f}"))
        c2.metric("Base (P50)",      f_val(p50[-1], "${:,.0f}"))
        c3.metric("Favorable (P95)", f_val(p95[-1], "${:,.0f}"))
        c4.metric("Tasa fija",       f_val(benchmark_fijo[-1], "${:,.0f}"),
                  delta=f_val(p50[-1]-benchmark_fijo[-1], "${:,.0f} diferencial") if not st.session_state.modo_privacidad else None)

        # Matriz de hitos
        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace; font-size: 10px;
            letter-spacing: 0.12em; text-transform: uppercase;
            opacity: 0.6; margin: 1.5rem 0 0.5rem;
        '>Matriz de capitalización por horizonte temporal</div>
        """, unsafe_allow_html=True)
        st.caption("Comparativa del escenario base (P50) vs tasa fija en hitos clave.")

        n_meses_total = horizonte_años * 12
        hitos_meses   = list(dict.fromkeys([m for m in [12, 36, 60, n_meses_total] if m <= n_meses_total]))
        hitos_labels  = {12: "1 año", 36: "3 años", 60: "5 años", n_meses_total: f"{horizonte_años} años (fin)"}

        filas_hitos = []
        for m in hitos_meses:
            idx = min(m, len(p50) - 1)
            
            # ── ANTÍDOTO ANTI-NAN ──
            # Si un ticker mal escrito corrompe la simulación, forzamos el valor a 0 para evitar el crash de Python
            val_p5    = p5[idx] if not np.isnan(p5[idx]) else 0
            val_p50   = p50[idx] if not np.isnan(p50[idx]) else 0
            val_p95   = p95[idx] if not np.isnan(p95[idx]) else 0
            val_bench = benchmark_fijo[idx] if not np.isnan(benchmark_fijo[idx]) else 0
            
            filas_hitos.append({
                "Horizonte":           hitos_labels.get(m, f"Mes {m}"),
                "Adverso P5 (MXN)":    int(val_p5),
                "Base P50 (MXN)":      int(val_p50),
                "Favorable P95 (MXN)": int(val_p95),
                "Tasa fija (MXN)":     int(val_bench),
                "Ventaja P50 vs Fija": int(val_p50 - val_bench),
            })
            
        df_hitos = pd.DataFrame(filas_hitos)
        if st.session_state.modo_privacidad:
            for col in ["Adverso P5 (MXN)", "Base P50 (MXN)", "Favorable P95 (MXN)", "Tasa fija (MXN)", "Ventaja P50 vs Fija"]:
                df_hitos[col] = "$ ••••••"
                
        st.dataframe(df_hitos, width='stretch', hide_index=True,
            column_config={
                "Adverso P5 (MXN)":   st.column_config.NumberColumn(format="$%d") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
                "Base P50 (MXN)":     st.column_config.NumberColumn(format="$%d") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
                "Favorable P95 (MXN)":st.column_config.NumberColumn(format="$%d") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
                "Tasa fija (MXN)":    st.column_config.NumberColumn(format="$%d") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
                "Ventaja P50 vs Fija":st.column_config.NumberColumn(format="$%d") if not st.session_state.modo_privacidad else st.column_config.TextColumn(),
            })

        # Riesgo institucional
        st.markdown("---")
        _header("Análisis de Riesgo Institucional", "VaR · CVaR · Drawdown · Stress Test")
        capital_riesgo      = st.number_input("Capital de referencia (USD)", value=200_000, step=10_000)
        retorno_port_diario = retornos_diarios @ pesos_opt

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin:1.5rem 0 .75rem;'>Value at Risk y Expected Shortfall</div>""", unsafe_allow_html=True)
        var_cvar = calcular_var_cvar(retorno_port_diario, capital_riesgo)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("VaR 95% Histórico", f"{var_cvar['VaR_95_hist']*100:.2f}%", f"-{f_val(abs(var_cvar['VaR_95_hist'])*capital_riesgo, '${:,.0f} USD')}")
        c2.metric("VaR 99% Histórico", f"{var_cvar['VaR_99_hist']*100:.2f}%", f"-{f_val(abs(var_cvar['VaR_99_hist'])*capital_riesgo, '${:,.0f} USD')}")
        c3.metric("CVaR 95%",          f"{var_cvar['CVaR_95']*100:.2f}%",     f"-{f_val(abs(var_cvar['CVaR_95'])*capital_riesgo, '${:,.0f} USD')}")
        c4.metric("CVaR 99%",          f"{var_cvar['CVaR_99']*100:.2f}%",     f"-{f_val(abs(var_cvar['CVaR_99'])*capital_riesgo, '${:,.0f} USD')}")

        fig_var = go.Figure()
        fig_var.add_trace(go.Histogram(x=retorno_port_diario*100, nbinsx=80,
            marker_color="rgba(68,136,255,0.7)", name="Retornos diarios"))
        fig_var.add_vline(x=var_cvar["VaR_95_hist"]*100, line_color="red",    line_dash="dash",  annotation_text="VaR 95%")
        fig_var.add_vline(x=var_cvar["CVaR_95"]*100,     line_color="orange", line_dash="dash",  annotation_text="CVaR 95%")
        fig_var.add_vline(x=var_cvar["VaR_99_hist"]*100, line_color="magenta",line_dash="dot",   annotation_text="VaR 99%")
        fig_var.update_layout(template="plotly_dark", height=380, xaxis_title="Retorno Diario (%)", yaxis_title="Frecuencia", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_var, width='stretch', key="chart_var")

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin:1.5rem 0 .75rem;'>Maximum Drawdown</div>""", unsafe_allow_html=True)
        dd_serie, max_dd, inicio_dd, fin_dd, duracion_dd = calcular_drawdown(retorno_port_diario)
        c1,c2,c3 = st.columns(3)
        c1.metric("Maximum Drawdown", f"{max_dd*100:.2f}%", f"-{f_val(abs(max_dd)*capital_riesgo, '${:,.0f} USD')}")
        c2.metric("Duración",         f"{duracion_dd} días ({duracion_dd//30} meses)")
        c3.metric("Período",          f"{inicio_dd.strftime('%b %Y')} — {fin_dd.strftime('%b %Y')}")

        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(x=dd_serie.index, y=dd_serie*100,
            fill="tozeroy", fillcolor="rgba(255,68,68,0.3)", line=dict(color="red", width=1), name="Drawdown"))
        fig_dd.add_hline(y=max_dd*100, line_color="gold", line_dash="dash", annotation_text=f"Max DD: {max_dd*100:.2f}%")
        fig_dd.update_layout(template="plotly_dark", height=350, xaxis_title="Fecha", yaxis_title="Drawdown (%)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_dd, width='stretch', key="chart_dd")

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin:1.5rem 0 .75rem;'>Sortino vs Sharpe</div>""", unsafe_allow_html=True)
        sortino, desv_down = calcular_sortino(retorno_port_diario, ret_opt, tasa_rf)
        c1,c2,c3 = st.columns(3)
        c1.metric("Ratio de Sharpe",          f"{sharpe_opt:.4f}")
        c2.metric("Ratio de Sortino",         f"{sortino:.4f}")
        c3.metric("Desviación downside anual",f"{desv_down*100:.2f}%")

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin:1.5rem 0 .75rem;'>Stress Testing — Escenarios Históricos</div>""", unsafe_allow_html=True)
        
        df_stress = calcular_stress_test(pesos_opt, nombres_activos_finales, capital_riesgo, retornos_diarios)
        
        if df_stress is not None and not df_stress.empty and "Pérdida (%)" in df_stress.columns:
            fig_stress = go.Figure(go.Bar(
                x=df_stress["Pérdida (%)"], y=df_stress["Escenario"], orientation="h",
                marker_color=["red" if p < -15 else "orange" if p < -8 else "gold" for p in df_stress["Pérdida (%)"]],
                text=[f"{p:.1f}%" for p in df_stress["Pérdida (%)"]],
                textposition="outside"))
            fig_stress.update_layout(template="plotly_dark", height=350, xaxis_title="Impacto en Capital (%)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_stress, width='stretch', key="chart_stress")
            
            # ── ALERTA DE COBERTURA CAMBIARIA ──
            if any(p > 0 for p in df_stress["Pérdida (%)"]):
                st.success(
                    "**Efecto de Cobertura Cambiaria Detectado:** El modelo proyecta rendimientos POSITIVOS en escenarios "
                    "de crisis global. Esto no es un error algorítmico, sino el efecto de tener un portafolio "
                    "altamente concentrado en activos dolarizados (USD). Cuando ocurre un pánico bursátil, el "
                    "Peso Mexicano suele devaluarse violentamente contra el Dólar, lo cual compensa e incluso "
                    "supera las caídas de las acciones al valuar su patrimonio en moneda local."
                )
            
            df_stress_disp = df_stress.copy()
            if st.session_state.modo_privacidad:
                df_stress_disp["Pérdida Estimada (USD)"] = "$ ••••••"
            st.dataframe(df_stress_disp, width='stretch')
        else:
            st.info(
                " **Aviso de modelado:** No fue posible simular los escenarios de estrés histórico. "
                "Esto es completamente normal si el portafolio incluye activos (como criptomonedas o IPOs recientes) "
                "que no cotizaban en los mercados durante las crisis históricas evaluadas (ej. Crisis Subprime 2008)."
            )

        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin:1.5rem 0 .75rem;'>Correlación Dinámica Rolling — 60 días</div>""", unsafe_allow_html=True)
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
                yaxis=dict(range=[-1.1, 1.1]), xaxis_title="Fecha", yaxis_title="Coeficiente de Pearson", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_corr, width='stretch', key="chart_corr")
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
                xaxis_title="Fecha", yaxis_title="Precio", legend=dict(x=0.01, y=0.99), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hmm, width='stretch', key="chart_hmm")
            pct = (df_regimenes["Regimen"] == 1).mean() * 100
            c1, c2 = st.columns(2)
            c1.metric("Régimen normal",   f"{100-pct:.1f}%")
            c2.metric("Régimen de tensión",f"{pct:.1f}%")
        else:
            st.info("Ejecute la optimización para generar el análisis de regímenes.")

        # Reporte PDF
        st.markdown("---")
        _header("Exportar", "Reporte Institucional")
        
        nombre_defecto = cliente_seleccionado if cliente_seleccionado != "✚ Nuevo Cliente (Sin seleccionar)" else "Cliente Institucional"
        nombre_imprimir = st.text_input("Nombre a imprimir en la portada del PDF:", value=nombre_defecto)

        col_btn_pdf, col_esp = st.columns([1, 3])
        with col_btn_pdf:
            if st.button("Generar reporte PDF", type="primary", width='stretch'):
                with st.spinner("Generando reporte..."):
                    try:
                        # ── RE-CÁLCULO ACTUARIAL DE CONTROL DE CALIDAD ──
                        # Leemos los parámetros que guardamos en la sesión global
                        pimss = st.session_state.get('pension_imss', 0.0)
                        meta = st.session_state.get('meta_mensual', 40000.0)
                        swr_rate = st.session_state.get('tasa_retiro', 0.04)
                        
                        # Si el portafolio ya está optimizado, forzamos que la página 2 use la tasa real óptima (ret_opt)
                        if st.session_state.optimizado:
                            cap_actual = st.session_state.get('ldi_capital_actual', 200000.0)
                            aport_mensual = st.session_state.get('ldi_aportacion_mensual', 5000.0)
                            anos_hz = st.session_state.get('ldi_anios_horizonte', 10)
                            inf_rate = st.session_state.get('ldi_inflacion', 4.0) / 100 if st.session_state.get('ldi_inflacion', 4.0) > 1.0 else st.session_state.get('ldi_inflacion', 0.04)
                            
                            # Proyección estricta con el retorno del portafolio óptimo
                            cap_real_opt = MotorActuarial.proyeccion_ppr_real(cap_actual, aport_mensual, anos_hz, ret_opt, inf_rate)
                            _, brecha_definitiva, _ = MotorActuarial.calcular_brecha_pensional_real(meta, pimss, cap_real_opt, swr_rate)
                        else:
                            brecha_definitiva = st.session_state.get('brecha', 0.0)

                        # Ejecución blindada del PDF
                        pdf_bytes = generar_reporte(
                            nombre_cliente=nombre_imprimir,
                            meta_mensual=meta,
                            tasa_retiro_swr=swr_rate,
                            regimen_pensional=st.session_state.get('regimen', 'PPR Puro'),
                            tickers=nombres_activos_finales, pesos_opt=pesos_opt, ret_opt=ret_opt, vol_opt=vol_opt,
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
                            limite_riesgo_global=st.session_state.get('riesgo_objetivo_ldi', None),
                            perfil_estrategico=st.session_state.get('perfil_ldi_nombre', None),
                            pension_imss=pimss,
                            brecha_pensional=brecha_definitiva, # <── INYECCIÓN DE LA BRECHA DEFINITIVA SINCRO
                            semanas_cotizadas=st.session_state.get('semanas_cotizadas', None),
                            salario_promedio=st.session_state.get('salario_promedio', None),
                            simular_m40=st.session_state.get('simular_m40', False),
                        )
                        st.download_button(
                            label="Descargar reporte PDF", data=pdf_bytes,
                            file_name=f"MotorGaLa_{nombre_imprimir.replace(' ', '')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf")
                        st.success("Reporte generado correctamente.")
                    except Exception as e:
                        st.error(f"Error al generar el reporte: {e}")
                        st.exception(e)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PLANEACIÓN DE RETIRO (LDI PERSONAL EN TÉRMINOS REALES)
# ═══════════════════════════════════════════════════════════════════════════
with tab_retiro:
    _header("Modelado Actuarial LDI", "Planeación de Retiro Integral")
    st.caption("Proyección de flujos ajustados a poder adquisitivo actual mediante la Ecuación de Fisher.")

    # ── EL CEREBRO DEL TAB: Selector de Régimen ──
    regimen = st.radio(
        "Selecciona tu Régimen Pensional:",
        ["PPR Puro / Ley 97 (Generación Afore)", "Ley 73 (Beneficio IMSS + Suplemento Privado)"],
        horizontal=True, key="regimen"
    )
    
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    
    col_param, col_priv = st.columns(2, gap="large")
    
    pension_imss = 0.0  # Por defecto 0 para PPR Puro
    
    with col_param:
        if "Ley 73" in regimen:
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>1. Parámetros IMSS (Ley 73)</div>""", unsafe_allow_html=True)
            simular_m40 = st.toggle("Activar Estrategia: Modalidad 40 Topada", key="simular_m40")
            semanas_cotizadas = st.slider("Semanas Cotizadas Estimadas", min_value=500, max_value=3000, value=1500, step=50, key="ldi_semanas")
            tiene_pareja = st.checkbox("Aplicar Asignación Familiar (15%)", value=False, key="ldi_pareja")
            
            if simular_m40:
                st.info("**M40 Activado:** Salario Promedio topado a 25 UMAs.")
                salario_promedio = 25 * obtener_uma_actual()
                st.metric("Salario Promedio Diario", f_val(salario_promedio))
            else:
                salario_promedio = st.number_input("Salario Promedio Diario (MXN)", min_value=100.0, max_value=3500.0, value=800.0, step=100.0, key="ldi_salario_promedio")
                
            edad_retiro = st.selectbox("Edad de retiro proyectada", [60, 61, 62, 63, 64, 65], index=5, key="ldi_edad_retiro")
        
        else:
            # ── VISTA PARA PPR PURO ──
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>1. Horizonte de Acumulación (PPR)</div>""", unsafe_allow_html=True)
            st.info("Bajo este régimen, el **100%** de tu flujo de retiro provendrá de la desacumulación de tu capital privado. No se estiman rentas vitalicias gubernamentales.")
            anios_horizonte = st.slider("Años faltantes para el retiro", min_value=1, max_value=50, value=40, help="Horizonte de tiempo para el interés compuesto.", key="ldi_anios_horizonte")
            edad_retiro = 65 # Solo de referencia
            
    with col_priv:
        st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>2. Capitalización Privada y Meta</div>""", unsafe_allow_html=True)
        
        meta_mensual = st.number_input("Ingreso Mensual Objetivo (Pesos de Hoy)", min_value=10000, step=5000, value=40000, key="meta_mensual")
        
        col_cap1, col_cap2 = st.columns(2)
        capital_actual = col_cap1.number_input("Capital Inicial (MXN)", min_value=0, step=50000, value=200000, key="ldi_capital_actual")
        aportacion_mensual = col_cap2.number_input("Aportación Mensual (MXN)", min_value=0, step=1000, value=5000, key="ldi_aportacion_mensual")
        
        # ── NUEVO: MÓDULO DE ALPHA FISCAL (ART. 151) ──
        usar_fiscal = st.toggle("Activar Optimización Fiscal (Deducibilidad Art. 151)", key="ldi_fiscal")
        if usar_fiscal:
            ingreso_comprobable = st.number_input("Ingreso Mensual Bruto Comprobable (MXN)", min_value=10000, value=60000, step=5000, key="ldi_ingreso", help="Se utiliza para calcular su tasa marginal de ISR y el tope exacto de deducción (10% o 5 UMAs).")
            st.caption("El modelo simulará que el saldo devuelto por el SAT se reinvierte en el portafolio cada mes de abril.")
        else:
            ingreso_comprobable = 0.0

        if "Ley 73" in regimen:
            anios_horizonte = st.slider("Años de acumulación restantes", min_value=1, max_value=40, value=10, key="ldi_anios_horizonte")
            
        st.markdown("<div style='font-size:12px; color:#94A3B8; margin-top:10px;'>Calibración Estocástica</div>", unsafe_allow_html=True)
        col_tasas1, col_tasas2, col_tasas3 = st.columns(3)
        inflacion = col_tasas1.number_input("Inflación (%)", value=4.0, step=0.5, key="ldi_inflacion") / 100
        
        # ── INTERCONEXIÓN INTELIGENTE: Si ya se optimizó el portafolio, sugerimos esa tasa real de la pestaña 2
        ret_opt_actual = st.session_state.get('ret_opt')
        tasa_base = ret_opt_actual if ret_opt_actual is not None else 0.15
        tasa_sugerida = float(tasa_base * 100)
        
        tasa_portafolio = col_tasas2.number_input("Rend. Anual (%)", value=tasa_sugerida, step=1.0, key="ldi_tasa_portafolio_input") / 100
        
        tasa_retiro = col_tasas3.number_input("Tasa SWR (%)", value=4.0, step=0.5, key="ldi_tasa_swr_input") / 100
        st.session_state["tasa_retiro"] = tasa_retiro

    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    
    if st.button("Ejecutar Modelado Actuarial", type="primary", width='stretch'):
        with st.spinner("Descontando flujos por inflación y calculando Ecuación de Fisher..."):
            
            uma_actual = obtener_uma_actual()
            
            if "Ley 73" in regimen:
                pension_imss = MotorActuarial.estimar_pension_ley73(semanas_cotizadas, salario_promedio, edad_retiro, uma_actual, tiene_pareja)
                st.session_state['semanas_cotizadas'] = semanas_cotizadas
                st.session_state['salario_promedio'] = salario_promedio
            else:
                pension_imss = 0.0
                st.session_state['semanas_cotizadas'] = None
                st.session_state['salario_promedio'] = None
            
            # ── LLAMADA AL MOTOR ACTUALIZADA CON ALPHA FISCAL ──
            capital_acumulado_real = MotorActuarial.proyeccion_ppr_real(
                capital_inicial=capital_actual, 
                aportacion_mensual=aportacion_mensual, 
                anios=anios_horizonte, 
                tasa_anual=tasa_portafolio, 
                inflacion=inflacion,
                ingreso_mensual=ingreso_comprobable,      # <── Nuevo parámetro fiscal
                aplicar_beneficio_fiscal=usar_fiscal,     # <── Interruptor fiscal
                uma_actual=uma_actual                     # <── Tope legal actualizado
            )
            
            # La segunda línea queda prácticamente igual, pero ahora recibe el nuevo capital "dopado"
            ingreso_total, brecha, flujo_privado = MotorActuarial.calcular_brecha_pensional_real(
                meta_mensual, 
                pension_imss, 
                capital_acumulado_real, 
                tasa_retiro
            )
            
            st.session_state['pension_imss'] = pension_imss
            st.session_state['brecha'] = brecha

            st.markdown("---")
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#17C37B;margin-bottom:.75rem;'>Diagnóstico Actuarial (Valores Reales - Pesos de Hoy)</div>""", unsafe_allow_html=True)
            
            st.info(f"**Proyección del Fondo Privado:** Al finalizar el periodo de {anios_horizonte} años, el capital acumulado equivaldrá a **${capital_acumulado_real:,.2f} MXN en poder adquisitivo actual**, habiendo descontado una erosión inflacionaria del {inflacion*100:.1f}% anual.")
            
            m1, m2, m3 = st.columns(3)
            if "Ley 73" in regimen:
                m1.metric("Pensión IMSS Estimada", f_val(pension_imss), "Base vitalicia")
            else:
                m1.metric("Pensión Gubernamental", "$0.00", "Régimen PPR Puro")
                
            m2.metric("Flujo Privado (SWR)", f_val(flujo_privado), f"Retiro: {tasa_retiro*100:.1f}% anual")
            
            if brecha <= 0:
                m3.metric("Ingreso Total Mensual", f_val(ingreso_total), f"+{f_val(abs(brecha))} sobre la meta")
                st.success(f"**Superávit Estructural:** La acumulación supera la meta de {f_val(meta_mensual)}. El enfoque debe centrarse en preservación patrimonial.")
                riesgo_sugerido = 0.20 
                perfil_estrategico = "Conservador Institucional (LDI Preservación)"
            else:
                m3.metric("Ingreso Total Mensual", f_val(ingreso_total), f"-{f_val(abs(brecha))} de déficit", delta_color="inverse")
                st.warning(f"**Déficit de Cobertura:** Existe una brecha de {f_val(brecha)} mensuales (valor real). Se requiere incrementar aportaciones, alargar el horizonte de acumulación o asumir mayor riesgo en el portafolio.")
                
                deficit_tolerable = 30000.0
                factor_necesidad = min(brecha / deficit_tolerable, 1.0)
                riesgo_sugerido = min(0.20 + (0.60 * factor_necesidad), 0.85)
                perfil_estrategico = "Moderado / Crecimiento Actuarial"

            st.session_state["riesgo_objetivo_ldi"] = riesgo_sugerido
            st.session_state["perfil_ldi_nombre"] = perfil_estrategico
            
            st.markdown("---")
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:#4488FF;margin-bottom:.75rem;'>Prescripción Algorítmica de Portafolio</div>""", unsafe_allow_html=True)
            st.info(f"**Perfil asignado:** {perfil_estrategico}\n\n" f"**Límite Máximo de Renta Variable Sugerido:** {riesgo_sugerido*100:.1f}%\n\n" f"El Motor GaLa ha calibrado automáticamente esta restricción. Ejecuta el Optimizador SLSQP en la pestaña 'Motor Cuantitativo' para acatar este mandato de riesgo.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — NOTICIAS DEL MERCADO
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
                        st.link_button("Leer", url_destino, width='stretch')
                st.markdown("---")
            except Exception:
                continue

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — COMUNIDAD
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

    st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin:1.5rem 0 .75rem;'>Nueva publicación</div>""", unsafe_allow_html=True)
    with st.form("form_comunidad"):
        titulo_post    = st.text_input("Título", placeholder="Ej. Análisis del sector energético mexicano Q2 2026")
        categoria_post = st.selectbox("Categoría", ["Análisis de mercado","Estrategia de inversión",
            "Macro y economía","Fintech y tecnología","Gestión de riesgo","Pregunta a la comunidad"])
        contenido_post = st.text_area("Contenido",
            placeholder="Comparta su análisis, perspectiva o pregunta...", height=150)
        post_btn = st.form_submit_button("Enviar para revisión", width='stretch')

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
    st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Publicaciones recientes</div>""", unsafe_allow_html=True)

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
# TAB 6 — GLOSARIO TÉCNICO
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
# TAB 7 — SUGERENCIAS
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
        enviado = st.form_submit_button("Enviar comentario", width='stretch')

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

# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — ADMINISTRACIÓN (OCULTO)
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
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Publicaciones pendientes de revisión</div>""", unsafe_allow_html=True)
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
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Retroalimentación directa de los usuarios</div>""", unsafe_allow_html=True)
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
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Base de datos de adopción</div>""", unsafe_allow_html=True)
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
                st.dataframe(df_users[["nombre_display","email","tiene_lite"]], width='stretch')
            else:
                st.info("No se pudieron cargar los datos de usuarios.")

        with sub_leads:
            st.markdown("""<div style='font-family:"DM Mono",monospace;font-size:10px;letter-spacing:.12em;text-transform:uppercase;opacity:0.6;margin-bottom:.75rem;'>Embudo de ventas — Prospectos corporativos</div>""", unsafe_allow_html=True)
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
                    return "<span style='display:inline-flex;align-items:center;gap:5px;font-family:\"DM Mono\",monospace;font-size:10px;letter-spacing:.08em;text-transform:uppercase;opacity:0.6;'><span style='width:5px;height:5px;background:gray;border-radius:50%;'></span>Pendiente</span>"

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
                                if st.button("Registrar contacto", key=f"lead_{l['id']}", type="primary", width='stretch'):
                                    try:
                                        db.table("leads_b2b").update({"contactado": True}).eq("id", l["id"]).execute()
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error: {e}")


