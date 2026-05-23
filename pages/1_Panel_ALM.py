import streamlit as st
import pandas as pd

# ── Control de acceso ──────────────────────────────────────────────────────────
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    st.switch_page("app_institucional.py")

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel ALM | Motor GaLa",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=DM+Mono:wght@300;400;500&display=swap');

#MainMenu {visibility: hidden;}
footer     {visibility: hidden;}
header     {visibility: hidden;}

html, body, [class*="css"] {
    font-family: 'EB Garamond', Georgia, serif;
}

.stApp {
    background-color: #0C0F14;
}

h1, h2, h3 {
    font-family: 'EB Garamond', Georgia, serif !important;
    font-weight: 500 !important;
    color: #E8EDF5 !important;
}

hr {
    border: none !important;
    border-top: 0.5px solid rgba(68,136,255,0.12) !important;
    margin: 2rem 0 !important;
}

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
    font-size: 1.4rem !important;
    color: #E8EDF5 !important;
    letter-spacing: -0.02em !important;
}

[data-testid="stFileUploadDropzone"] {
    background-color: rgba(68,136,255,0.03) !important;
    border: 0.5px dashed rgba(68,136,255,0.3) !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploadDropzone"]:hover {
    background-color: rgba(68,136,255,0.06) !important;
    border-color: rgba(68,136,255,0.55) !important;
}

[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(68,136,255,0.12) !important;
    border-radius: 6px !important;
}

.stButton > button {
    background: transparent !important;
    border: 0.5px solid rgba(68,136,255,0.3) !important;
    color: #4488FF !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.55rem 1.25rem !important;
    border-radius: 3px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: rgba(68,136,255,0.06) !important;
    border-color: #4488FF !important;
}
</style>
""", unsafe_allow_html=True)

# ── Encabezado ─────────────────────────────────────────────────────────────────
empresa_cliente = st.session_state.get("empresa", "Institución Financiera")

col_header, col_session = st.columns([3, 1])

with col_header:
    st.markdown(f"""
    <div style='padding: 1.5rem 0 1.25rem;'>
        <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #4488FF; margin-bottom: 0.6rem;'>Motor GaLa &nbsp;·&nbsp; Panel Institucional</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: clamp(22px, 3vw, 32px); font-weight: 400; color: #E8EDF5; letter-spacing: 0.01em; line-height: 1.2;'>{empresa_cliente}</div>
    </div>
    """, unsafe_allow_html=True)

with col_session:
    st.markdown("""
    <div style='display: flex; justify-content: flex-end; align-items: flex-start; padding-top: 2rem;'>
        <div style='display: flex; align-items: center; gap: 7px; font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: #17C37B;'>
            <span style='width: 6px; height: 6px; background: #17C37B; border-radius: 50%; display: inline-block; box-shadow: 0 0 6px rgba(23,195,123,0.5);'></span>
            Sesión activa
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 2.5rem;'></div>", unsafe_allow_html=True)

# ── MÓDULOS DE INGESTA (ACTIVOS Y PASIVOS) ─────────────────────────────────────
st.markdown("""
<div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #4488FF; margin-bottom: 0.4rem;'>Paso 1: Mapeo de Balance</div>
<div style='font-family: "EB Garamond", Georgia, serif; font-size: 22px; color: #E8EDF5; font-weight: 400; margin-bottom: 1.5rem;'>Carga de Información Financiera</div>
""", unsafe_allow_html=True)

col_pasivos, col_activos = st.columns(2, gap="large")

with col_pasivos:
    st.markdown("""
    <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #FF6B6B; margin-bottom: 0.4rem;'>Obligaciones</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 18px; color: #E8EDF5; font-weight: 400; margin-bottom: 0.5rem;'>Matriz de Pasivos</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; font-style: italic; color: #5A6780; line-height: 1.6; margin-bottom: 1.25rem;'>
        Proyección de flujos de salida (siniestros esperados, rescates).
    </div>
    <div style='padding: 0.8rem 1rem; background: rgba(255,107,107,0.03); border: 0.5px solid rgba(255,107,107,0.15); border-radius: 4px; font-family: "DM Mono", monospace; font-size: 10px; color: #5A6780; line-height: 1.8; margin-bottom: 1rem;'>
        Formatos admitidos &nbsp;·&nbsp; .xlsx &nbsp;/&nbsp; .csv<br>
        Columnas exigidas &nbsp;·&nbsp; <span style='color: #B0BACA;'>Año</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Flujo_Esperado</span>
    </div>
    """, unsafe_allow_html=True)
    archivo_pasivos = st.file_uploader("Cargar Pasivos", type=["xlsx", "csv"], label_visibility="collapsed", key="up_pas")

with col_activos:
    st.markdown("""
    <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #4488FF; margin-bottom: 0.4rem;'>Inversiones</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 18px; color: #E8EDF5; font-weight: 400; margin-bottom: 0.5rem;'>Cartera de Activos</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; font-style: italic; color: #5A6780; line-height: 1.6; margin-bottom: 1.25rem;'>
        Inventario actual de instrumentos de deuda en balance.
    </div>
    <div style='padding: 0.8rem 1rem; background: rgba(68,136,255,0.03); border: 0.5px solid rgba(68,136,255,0.15); border-radius: 4px; font-family: "DM Mono", monospace; font-size: 10px; color: #5A6780; line-height: 1.8; margin-bottom: 1rem;'>
        Formatos admitidos &nbsp;·&nbsp; .xlsx &nbsp;/&nbsp; .csv<br>
        Columnas exigidas &nbsp;·&nbsp; <span style='color: #B0BACA;'>Instrumento</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Valor_Mercado</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Duracion</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Convexidad</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Tasa_YTM</span>
    </div>
    """, unsafe_allow_html=True)
    archivo_activos = st.file_uploader("Cargar Activos", type=["xlsx", "csv"], label_visibility="collapsed", key="up_act")

# ── PROCESAMIENTO ESTOCÁSTICO ──────────────────────────────────────────────────
st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)

if archivo_pasivos is not None and archivo_activos is not None:
    try:
        # Lectura segura de ambos archivos
        df_pasivos = pd.read_csv(archivo_pasivos) if archivo_pasivos.name.endswith('.csv') else pd.read_excel(archivo_pasivos)
        df_activos = pd.read_csv(archivo_activos) if archivo_activos.name.endswith('.csv') else pd.read_excel(archivo_activos)

        # Diagnóstico del Balance
        st.markdown("""
        <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.4rem;'>Validación</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 22px; color: #E8EDF5; font-weight: 400; margin-bottom: 1.5rem;'>Auditoría de Brecha Estructural</div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        valor_total_pasivos = df_pasivos['Flujo_Esperado'].sum()
        valor_total_activos = df_activos['Valor_Mercado'].sum()
        
        # Ponderación de duración de activos (Promedio ponderado)
        df_activos['Peso'] = df_activos['Valor_Mercado'] / valor_total_activos
        duracion_activos_cartera = (df_activos['Duracion'] * df_activos['Peso']).sum()

        c1.metric("Valor Total Activos", f"${valor_total_activos:,.2f} M")
        c2.metric("Valor Total Pasivos", f"${valor_total_pasivos:,.2f} M")
        
        ratio = valor_total_activos / valor_total_pasivos
        c3.metric("Ratio de Cobertura", f"{ratio*100:.1f}%")

        # Botón de Optimización
        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        if st.button("Ejecutar Inmunización SLSQP", type="primary"):
            st.info("Módulo cuantitativo en espera de conexión para reestructuración de cartera.")

    except Exception as e:
        st.error(f"Error de formato. Columnas requeridas ausentes o estructura inválida. Detalle técnico: {e}")
elif archivo_pasivos is not None or archivo_activos is not None:
    st.info("Aguardando ingesta del archivo complementario para inicializar diagnóstico ALM.")

# ── Cierre de sesión ───────────────────────────────────────────────────────────
st.markdown("---")
col_btn, col_esp = st.columns([1, 4])
with col_btn:
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["empresa"]     = ""
        st.switch_page("app_institucional.py")
