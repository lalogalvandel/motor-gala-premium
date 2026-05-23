import streamlit as st

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
        align-items: center;
        height: 100%;
        padding-top: 1.5rem;
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

st.markdown("<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 2.5rem;'></div>",
            unsafe_allow_html=True)

# ── Sección principal ──────────────────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom: 0.4rem;'>
    <div style='
        font-family: "DM Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #5A6780;
        margin-bottom: 0.5rem;
    '>Asset & Liability Management</div>
    <div style='
        font-family: "EB Garamond", Georgia, serif;
        font-size: 24px;
        color: #E8EDF5;
        font-weight: 400;
    '>Panel de Control Estocástico</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style='
    margin: 1.5rem 0 2.5rem;
    padding: 1.25rem 1.5rem;
    border: 0.5px solid rgba(68,136,255,0.15);
    border-left: 2px solid rgba(68,136,255,0.4);
    border-radius: 4px;
    background: rgba(68,136,255,0.03);
    font-family: "EB Garamond", Georgia, serif;
    font-size: 15px;
    font-style: italic;
    color: #5A6780;
    line-height: 1.65;
'>
    Este entorno alojará las tablas de pasivos, la cartera de inversiones institucional
    y el optimizador SLSQP operando sobre los datos en producción de la aseguradora.
    Los módulos se activarán conforme avance el despliegue.
</div>
""", unsafe_allow_html=True)

# ── Cierre de sesión ───────────────────────────────────────────────────────────
st.markdown("---")

col_btn, col_esp = st.columns([1, 4])
with col_btn:
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["empresa"]     = ""
        st.switch_page("app_institucional.py")
