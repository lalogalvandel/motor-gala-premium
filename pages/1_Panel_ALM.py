import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from supabase import create_client
from modulos.actuaria_alm import calcular_duracion_convexidad, optimizar_inmunizacion, calcular_rcs_mercado
from modulos.reportes import generar_pdf_inmunizacion

# ── Control de acceso ──────────────────────────────────────────────────────────
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    st.switch_page("app_institucional.py")

# ── Supabase ───────────────────────────────────────────────────────────────────
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    db  = create_client(url, key)
except:
    pass

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

#MainMenu, footer, header { visibility: hidden; }

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

/* Métricas */
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

/* File uploader */
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

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(68,136,255,0.12) !important;
    border-radius: 6px !important;
}

/* Slider */
[data-testid="stSlider"] > div > div > div {
    background: linear-gradient(90deg, #4488FF, #4488FF) !important;
}

/* Botones */
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
[data-testid="baseButton-primary"] {
    background: #4488FF !important;
    color: #0C0F14 !important;
    border: none !important;
    font-weight: 500 !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #5594FF !important;
}

/* Alertas */
[data-testid="stAlert"] {
    border-radius: 4px !important;
    border-left-width: 2px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 12px !important;
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
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: clamp(22px
