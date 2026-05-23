import streamlit as st
import pandas as pd

# ── Control de acceso ──────────────────────────────────────────────────────────
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    st.switch_page("app_institucional.py")

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel ALM | Motor GaLa",
    page_icon="",
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
    background-image:
        linear-gradient(rgba(68,136,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(68,136,255,0.03) 1px, transparent 1px);
    background-size: 48px 48px;
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
    background-color: rgba(68,136,255,0.03) !important;
    border: 0.5px dashed rgba(68,136,255,0.3) !important;
    border-radius: 6px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stFileUploadDropzone"]:hover {
    background-color: rgba(68,136,255,0.06) !important;
    border-color: rgba(68,136,255,0.55) !important;
}

/* Dataframe */
[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(68,136,255,0.12) !important;
    border-radius: 6px !important;
}

/* Botón */
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
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #4488FF;
            margin-bottom: 0.6rem;
        '>Motor GaLa &nbsp;·&nbsp; Panel Institucional</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: clamp(22px, 3vw, 32px);
            font-weight: 400;
            color: #E8EDF5;
            letter-spacing: 0.01em;
            line-height: 1.2;
        '>{empresa_cliente}</div>
    </div>
    """, unsafe_allow_html=True)

with col_session:
    st.markdown("""
    <div style='
        display: flex;
        justify-content: flex-end;
        align-items: flex-start;
        padding-top: 2rem;
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

st.markdown(
    "<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 2.5rem;'></div>",
    unsafe_allow_html=True
)

# ── Ingesta de pasivos ─────────────────────────────────────────────────────────
col_info, col_upload = st.columns([1, 1.5], gap="large")

with col_info:
    st.markdown("""
    <div style='
        font-family: "DM Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #4488FF;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 0.5px solid rgba(68,136,255,0.15);
    '>Ingesta de Pasivos</div>
    <div style='
        font-family: "EB Garamond", Georgia, serif;
        font-size: 22px;
        color: #E8EDF5;
        margin-bottom: 0.75rem;
        font-weight: 400;
    '>Proyección de Flujos de Salida</div>
    <div style='
        font-family: "EB Garamond", Georgia, serif;
        font-size: 15px;
        font-style: italic;
        color: #5A6780;
        line-height: 1.65;
        margin-bottom: 1.5rem;
    '>
        Cargue la matriz de flujos de salida correspondiente a sus reservas técnicas:
        siniestros esperados, vencimientos de pólizas y rescates proyectados.
    </div>
    <div style='
        padding: 1rem 1.25rem;
        background: rgba(68,136,255,0.03);
        border: 0.5px solid rgba(68,136,255,0.12);
        border-radius: 4px;
        font-family: "DM Mono", monospace;
        font-size: 10px;
        color: #5A6780;
        line-height: 2;
        letter-spacing: 0.04em;
    '>
        Formatos &nbsp;·&nbsp; .xlsx &nbsp;/&nbsp; .csv<br>
        Columnas requeridas &nbsp;·&nbsp;
        <span style='color: #B0BACA;'>Año</span> &nbsp;/&nbsp;
        <span style='color: #B0BACA;'>Flujo_Esperado</span>
    </div>
    """, unsafe_allow_html=True)

with col_upload:
    st.markdown("<div style='padding-top: 2.5rem;'></div>", unsafe_allow_html=True)
    archivo_pasivos = st.file_uploader(
        "Matriz de flujos",
        type=["xlsx", "csv"],
        label_visibility="collapsed"
    )

# ── Procesamiento y vista previa ───────────────────────────────────────────────
if archivo_pasivos is not None:
    try:
        if archivo_pasivos.name.endswith('.csv'):
            df_pasivos = pd.read_csv(archivo_pasivos)
        else:
            df_pasivos = pd.read_excel(archivo_pasivos)

        st.markdown("---")

        st.markdown("""
        <div style='margin-bottom: 1.5rem;'>
            <div style='
                font-family: "DM Mono", monospace;
                font-size: 10px;
                letter-spacing: 0.15em;
                text-transform: uppercase;
                color: #5A6780;
                margin-bottom: 0.4rem;
            '>Validación</div>
            <div style='
                font-family: "EB Garamond", Georgia, serif;
                font-size: 22px;
                color: #E8EDF5;
                font-weight: 400;
            '>Auditoría de Flujos</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Períodos proyectados",      f"{len(df_pasivos)}")
        c2.metric("Pasivos nominales totales", f"${df_pasivos['Flujo_Esperado'].sum():,.2f} M")
        c3.metric("Estado del archivo",        "Validado")

        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

        st.dataframe(
            df_pasivos,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Año":            st.column_config.NumberColumn(format="%d"),
                "Flujo_Esperado": st.column_config.NumberColumn(format="$%f M"),
            }
        )

    except Exception as e:
        st.error(
            f"Error al procesar el archivo. Verifique que contenga las columnas "
            f"'Año' y 'Flujo_Esperado' con el formato esperado. Detalle: {e}"
        )

# ── Cierre de sesión ───────────────────────────────────────────────────────────
st.markdown("---")
col_btn, col_esp = st.columns([1, 4])
with col_btn:
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["empresa"]     = ""
        st.switch_page("app_institucional.py")
