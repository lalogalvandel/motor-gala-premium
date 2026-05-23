import streamlit as st
from datetime import datetime

# ── Configuración de página Institucional ──────────────────────────────────────
st.set_page_config(
    page_title="GaLa Institutional Solutions",
    page_icon="🏛️",
    layout="centered", # Centrado para que el login se vea elegante y minimalista
    initial_sidebar_state="collapsed"
)

# ── Estilos CSS Minimalistas ───────────────────────────────────────────────────
st.markdown("""
<style>
    /* Ocultar menú de Streamlit y footer para dar look de software privado */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── Encabezado B2B ─────────────────────────────────────────────────────────────
st.markdown("<div style='text-align: center; margin-top: 3rem;'>", unsafe_allow_html=True)
st.title("Motor GaLa")
st.markdown("### Institutional Asset & Liability Management")
st.markdown("*Plataforma cuantitativa avanzada para Aseguradoras y Fondos de Inversión.*")
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("---")

# ── Sistema de Acceso / Demo ───────────────────────────────────────────────────
# Usamos tabs limpios para separar el Login del formulario de ventas
tab_login, tab_demo = st.tabs(["Acceso a Clientes", "Solicitar Demo Corporativa"])

with tab_login:
    st.subheader("Portal de Acceso")
    email_inst = st.text_input("Correo corporativo", key="login_email")
    pass_inst = st.text_input("Contraseña", type="password", key="login_pass")
    
    if st.button("Ingresar al Sistema", use_container_width=True, type="primary"):
        if email_inst and pass_inst:
            # Aquí conectaremos con la tabla usuarios_institucionales después
            st.warning("El módulo de autenticación B2B está en construcción.")
        else:
            st.error("Ingrese credenciales corporativas válidas.")

with tab_demo:
    st.subheader("Contacto Comercial")
    st.markdown("Motor GaLa opera bajo licenciamiento exclusivo. Solicite una evaluación técnica de nuestra arquitectura para su institución.")
    
    with st.form("form_demo"):
        col1, col2 = st.columns(2)
        with col1:
            nombre_demo = st.text_input("Nombre completo del solicitante")
            cargo_demo = st.text_input("Cargo (Ej. Actuario Jefe, CRO)")
        with col2:
            empresa_demo = st.text_input("Institución / Aseguradora")
            email_demo = st.text_input("Correo corporativo")
            
        interes = st.selectbox("Área de interés principal", [
            "Optimización de Reservas (Solvencia II)",
            "Calce de Activos y Pasivos (ALM)",
            "Proyecciones de Capital Estocásticas",
            "Otro"
        ])
        
        submit_demo = st.form_submit_button("Agendar demostración técnica", use_container_width=True)
        
        if submit_demo:
            if nombre_demo and empresa_demo and email_demo:
                # Aquí enviaremos los datos a la tabla leads_b2b en Supabase
                st.success("Solicitud recibida. Nuestro equipo se pondrá en contacto para agendar la evaluación.")
            else:
                st.error("Por favor, complete los campos obligatorios.")

# ── Pie de página corporativo ──────────────────────────────────────────────────
st.markdown("<div style='margin-top: 5rem; text-align: center; color: gray; font-size: 0.8rem;'>", unsafe_allow_html=True)
st.markdown(f"&copy; {datetime.now().year} Motor GaLa Quant Solutions. Todos los derechos reservados.")
st.markdown("</div>", unsafe_allow_html=True)
