import streamlit as st
import requests
from datetime import datetime
import plotly.graph_objects as go
from supabase import create_client

from modulos.actuaria_alm import simular_brecha_duracion, calcular_rcs_mercado, optimizar_inmunizacion
import numpy as np 

# ── Configuración de página Institucional ──────────────────────────────────────
st.set_page_config(
    page_title="GaLa Institutional Solutions",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CSS Institucional ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=DM+Mono:wght@300;400;500&display=swap');

/* ── Reset y base ─────────────────────────────────────────────────────── */
#MainMenu {visibility: hidden;}
footer     {visibility: hidden;}
header     {visibility: hidden;}

html, body, [class*="css"] {
    font-family: 'EB Garamond', Georgia, serif;
}

.stApp {
    background-color: #0C0F14;
}

/* ── Tipografía ───────────────────────────────────────────────────────── */
h1, h2, h3 {
    font-family: 'EB Garamond', Georgia, serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
    color: #E8EDF5 !important;
}

p, div, label, span {
    font-family: 'EB Garamond', Georgia, serif;
    color: #B0BACA;
}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    justify-content: center;
    background: transparent;
    border-bottom: 0.5px solid rgba(68,136,255,0.2);
    gap: 2rem;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 400 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: #5A6780 !important;
    background: transparent !important;
    border: none !important;
    padding: 0.75rem 0.5rem !important;
}

.stTabs [aria-selected="true"] {
    color: #4488FF !important;
    border-bottom: 1px solid #4488FF !important;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div > div {
    background-color: #0F1420 !important;
    border: 0.5px solid rgba(68,136,255,0.2) !important;
    border-radius: 4px !important;
    color: #E8EDF5 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}

[data-testid="stNumberInput"] input:focus,
[data-testid="stTextInput"] input:focus {
    border-color: rgba(68,136,255,0.6) !important;
    box-shadow: 0 0 0 1px rgba(68,136,255,0.15) !important;
}

/* ── Slider ───────────────────────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div {
    background: linear-gradient(90deg, #4488FF, #4488FF) !important;
}

/* ── Métricas ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0F1420 0%, #111827 100%);
    border: 0.5px solid rgba(68,136,255,0.15);
    border-radius: 6px;
    padding: 1.25rem 1.5rem;
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
    font-size: 1.6rem !important;
    color: #E8EDF5 !important;
    letter-spacing: -0.02em !important;
}

/* ── Botones ──────────────────────────────────────────────────────────── */
.stButton > button, .stFormSubmitButton > button {
    background: transparent !important;
    border: 0.5px solid rgba(68,136,255,0.5) !important;
    color: #4488FF !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.5rem !important;
    border-radius: 3px !important;
    transition: all 0.2s ease !important;
    width: 100%;
}

.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: rgba(68,136,255,0.08) !important;
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

/* ── Divisor ──────────────────────────────────────────────────────────── */
hr {
    border: none !important;
    border-top: 0.5px solid rgba(68,136,255,0.15) !important;
    margin: 2rem 0 !important;
}

/* ── Dataframe / tabla ────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(68,136,255,0.15) !important;
    border-radius: 6px !important;
}

/* ── Alertas ──────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 4px !important;
    border-left-width: 2px !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 13px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Conexión a Base de Datos ───────────────────────────────────────────────────
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    db = create_client(url, key)
except Exception as e:
    st.error(f"Error al inicializar la base de datos: {e}")

# ── Conexión API Banxico ───────────────────────────────────────────────────────
@st.cache_data(ttl=21600)
def obtener_tasa_libre_riesgo():
    try:
        token = st.secrets["TOKEN_BANXICO"]
        url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43936/datos/oportuno?token={token}"
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=5)
        if response.status_code == 200:
            str_valor = response.json()["series"][0]["datos"][0]["dato"]
            return float(str_valor) / 100
    except:
        pass
    return 0.065

# ── Encabezado institucional ───────────────────────────────────────────────────
st.markdown("""
<div style='text-align: center; padding: 3rem 0 1.5rem;'>
    <div style='
        font-family: "DM Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        color: #4488FF;
        margin-bottom: 1.25rem;
    '>Motor GaLa · Soluciones Institucionales</div>
    <div style='
        font-family: "EB Garamond", Georgia, serif;
        font-size: clamp(28px, 4vw, 42px);
        font-weight: 400;
        color: #E8EDF5;
        letter-spacing: 0.02em;
        margin-bottom: 0.75rem;
        line-height: 1.2;
    '>Asset &amp; Liability Management</div>
    <div style='
        font-family: "EB Garamond", Georgia, serif;
        font-size: 17px;
        font-style: italic;
        color: #5A6780;
        margin-bottom: 0.5rem;
    '>Plataforma cuantitativa para aseguradoras bajo normativa Solvencia II</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── Navegación Principal ───────────────────────────────────────────────────────
tab_demo, tab_contacto, tab_login = st.tabs([
    "Simulador ALM",
    "Solicitar Evaluación",
    "Acceso Institucional",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: SIMULADOR ALM
# ══════════════════════════════════════════════════════════════════════════════
with tab_demo:

    tasa_mercado = obtener_tasa_libre_riesgo()

    st.markdown(f"""
    <div style='
        text-align: center;
        font-family: "DM Mono", monospace;
        font-size: 12px;
        letter-spacing: 0.08em;
        color: #5A6780;
        margin: 1.5rem 0 2.5rem;
    '>
        Tasa Libre de Riesgo &nbsp;·&nbsp; CETES 28d (Banxico)
        &nbsp;&nbsp;
        <span style='
            color: #17C37B;
            font-size: 14px;
            font-weight: 500;
            letter-spacing: 0.05em;
        '>{tasa_mercado*100:.2f}%</span>
    </div>
    """, unsafe_allow_html=True)

    # ── BLOQUE SUPERIOR: Inputs y Diagnóstico ──
    col_act, col_pas, col_res = st.columns([1, 1, 1.5], gap="large")

    with col_act:
        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #4488FF;
            margin-bottom: 1.25rem;
            padding-bottom: 0.5rem;
            border-bottom: 0.5px solid rgba(68,136,255,0.2);
        '>Activos — Inversiones</div>
        """, unsafe_allow_html=True)

        v_activos   = st.number_input("Valor de Activos (M MXN)",          value=1000.0, step=50.0)
        d_activos   = st.number_input("Duración de Activos (Años)",        value=4.5,    step=0.1)
        vol_activos = st.slider("Volatilidad Anual del Portafolio",        0.0, 0.3, 0.08, format="%.2f")

    with col_pas:
        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #FF6B6B;
            margin-bottom: 1.25rem;
            padding-bottom: 0.5rem;
            border-bottom: 0.5px solid rgba(255,107,107,0.2);
        '>Pasivos — Reservas</div>
        """, unsafe_allow_html=True)

        v_pasivos = st.number_input("Valor de Pasivos (M MXN)",   value=920.0, step=50.0)
        d_pasivos = st.number_input("Duración de Pasivos (Años)", value=6.2,   step=0.1)

    with col_res:
        st.markdown("""
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #B0BACA;
            margin-bottom: 1.25rem;
            padding-bottom: 0.5rem;
            border-bottom: 0.5px solid rgba(176,186,202,0.15);
        '>Análisis de Riesgo ALM</div>
        """, unsafe_allow_html=True)

        gap = simular_brecha_duracion(d_activos, d_pasivos, v_activos, v_pasivos)
        scr = calcular_rcs_mercado(v_activos, vol_activos)

        color_gap = "#17C37B" if abs(gap) < 0.5 else ("#d4a017" if abs(gap) < 1.5 else "#FF4B4B")
        estado_gap = "Inmunizado" if abs(gap) < 0.5 else ("Riesgo Moderado" if abs(gap) < 1.5 else "Riesgo Crítico")

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=gap,
            number={
                'font': {'family': 'DM Mono', 'size': 32, 'color': color_gap},
                'suffix': ' años',
            },
            title={
                'text': (
                    f"Brecha de Duración<br>"
                    f"<span style='font-size:11px; font-family:DM Mono; "
                    f"color:{color_gap}; letter-spacing:0.1em; text-transform:uppercase;'>"
                    f"{estado_gap}</span>"
                ),
                'font': {'family': 'EB Garamond', 'size': 15, 'color': '#B0BACA'},
            },
            gauge={
                'axis': {'range': [-5, 5], 'tickfont': {'family': 'DM Mono', 'size': 9, 'color': '#5A6780'}, 'tickwidth': 1, 'tickcolor': '#1E2535'},
                'bar': {'color': color_gap, 'thickness': 0.2},
                'bgcolor': '#0C0F14',
                'borderwidth': 0,
                'steps': [
                    {'range': [-5.0, -1.5], 'color': 'rgba(255,75,75,0.12)'},
                    {'range': [-1.5, -0.5], 'color': 'rgba(212,160,23,0.12)'},
                    {'range': [-0.5,  0.5], 'color': 'rgba(23,195,123,0.12)'},
                    {'range': [ 0.5,  1.5], 'color': 'rgba(212,160,23,0.12)'},
                    {'range': [ 1.5,  5.0], 'color': 'rgba(255,75,75,0.12)'},
                ],
                'threshold': {'line': {'color': color_gap, 'width': 2}, 'thickness': 0.8, 'value': gap},
            },
        ))
        fig.update_layout(
            height=280,  
            margin=dict(l=24, r=24, t=85, b=8), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font={'family': 'EB Garamond'}
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── BLOQUE INFERIOR: Optimizador SLSQP ──
    st.markdown("---")
    st.markdown("""
    <div style='
        font-family: "DM Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: #4488FF;
        margin-bottom: 1rem;
    '>Motor de Inmunización (SLSQP)</div>
    """, unsafe_allow_html=True)

   if st.button("Generar Portafolio Óptimo de Cobertura", type="primary"):
        # Alineamos los activos con el motor shock-proof que probaste en el backend
        nombres_mercado = ["CETES 1A", "Mbono 3A", "Mbono 10A", "Deuda Corp 5A"]
        duraciones_mercado = np.array([0.9, 2.8, 8.1, 4.2])
        convexidades_mercado = np.array([1.2, 9.5, 78.4, 22.1]) 
        yields_mercado = np.array([0.10, 0.09, 0.085, 0.11])
        
        # Estimación de la convexidad del pasivo basada en la duración introducida
        conv_pasivo = (d_pasivos ** 2) * 1.33
        
        with st.spinner("Ejecutando algoritmo de calce estocástico..."):
            # Pasamos los 5 parámetros requeridos al nuevo motor
            resultado = optimizar_inmunizacion(
                duraciones_mercado, 
                convexidades_mercado, 
                yields_mercado, 
                d_pasivos, 
                conv_pasivo
            )
            
            if resultado["exito"]:
                col_res_txt, col_res_plot = st.columns([1, 1.5], gap="large")
                
                with col_res_txt:
                    st.success(f"✅ **Calce Logrado:** {resultado['duracion_lograda']:.2f} años")
                    st.info(f"📈 **Yield Optimizado:** {resultado['rendimiento_esperado']*100:.2f}%")
                    st.metric("Convexidad del Portafolio", f"{resultado['convexidad_lograda']:.2f}")
                    
                    st.markdown("<br><span style='color:#B0BACA; font-size:14px;'>Estructura del portafolio:</span>", unsafe_allow_html=True)
                    for nombre, peso in zip(nombres_mercado, resultado["pesos"]):
                        if peso > 0.01:
                            st.markdown(f"- **{nombre}:** {peso*100:.1f}%")
                            
                with col_res_plot:
                    labels_f = [n for n, p in zip(nombres_mercado, resultado["pesos"]) if p > 0.01]
                    valores_f = [p for p in resultado["pesos"] if p > 0.01]
                    
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=labels_f, 
                        values=valores_f, 
                        hole=.5,
                        textinfo='label+percent',
                        marker=dict(colors=['#4488FF', '#17C37B', '#d4a017', '#FF4B4B'])
                    )])
                    fig_pie.update_layout(
                        showlegend=False,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(t=10, b=10, l=10, r=10),
                        height=250,
                        font={'family': 'DM Mono', 'color': '#B0BACA', 'size': 11}
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.error("⚠️ Riesgo estructural: No hay instrumentos disponibles para calzar una duración o convexidad tan extrema.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: FORMULARIO DE CONTACTO
# ══════════════════════════════════════════════════════════════════════════════
with tab_contacto:

    st.markdown("""
    <div style='max-width: 680px; margin: 2rem auto 2.5rem;'>
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #4488FF;
            margin-bottom: 0.75rem;
        '>Licenciamiento Exclusivo</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 22px;
            color: #E8EDF5;
            margin-bottom: 1rem;
            line-height: 1.4;
        '>Solicite una evaluación técnica</div>
        <div style='
            font-family: "EB Garamond", Georgia, serif;
            font-size: 16px;
            font-style: italic;
            color: #5A6780;
            line-height: 1.65;
        '>
            Motor GaLa opera bajo licenciamiento institucional. Nuestra arquitectura incluye
            modelado estocástico de escenarios de tasas, calce de convexidad activo-pasivo y
            cumplimiento normativo CUSF / Solvencia II.
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_form, col_esp = st.columns([1.4, 1], gap="large")

    with col_form:
        with st.form("form_demo"):
            c1, c2 = st.columns(2, gap="medium")
            with c1:
                nombre_demo = st.text_input("Nombre completo")
                cargo_demo  = st.text_input("Cargo", placeholder="Ej. Director de Riesgos (CRO), CFO, etc.")
            with c2:
                empresa_demo = st.text_input("Institución")
                email_demo   = st.text_input("Correo corporativo")

            intereses_lista = st.multiselect(
                "Áreas de interés (Puede seleccionar varias)",
                [
                    "Análisis Integral (Suite Completa)",
                    "Optimización de Reservas (Solvencia II)",
                    "Calce de Activos y Pasivos (ALM)",
                    "Proyecciones de Capital Estocásticas",
                    "Otro requerimiento específico"
                ],
                default=["Análisis Integral (Suite Completa)"] # Nudge comercial
            )
            
            # Un campo extra para contexto de alto valor
            comentarios = st.text_area("Detalles del requerimiento o comentarios (Opcional)", height=68)

            submit_demo = st.form_submit_button(
                "Solicitar demostración técnica",
                type="primary",
                use_container_width=True,
            )

            if submit_demo:
                if nombre_demo and empresa_demo and email_demo and intereses_lista:
                    try:
                        # Convertimos la lista en un solo texto separado por comas
                        str_intereses = ", ".join(intereses_lista)
                        
                        # Si dejaron comentarios, se los pegamos al final del string
                        if comentarios.strip():
                            str_intereses += f" | Notas: {comentarios.strip()}"

                        db.table("leads_b2b").insert({
                            "nombre":     nombre_demo.strip(),
                            "cargo":      cargo_demo.strip(),
                            "empresa":    empresa_demo.strip(),
                            "email":      email_demo.strip().lower(),
                            "interes":    str_intereses, # Mandamos el texto ensamblado
                            "contactado": False,
                        }).execute()
                        st.success(
                            "Solicitud registrada. Nuestro equipo de arquitectura cuantitativa "
                            "se pondrá en contacto en las próximas 24 horas hábiles."
                        )
                    except Exception as e:
                        st.error(f"Error de conexión: {e}")
                else:
                    st.warning("Complete los campos obligatorios (Nombre, Institución, Correo y al menos un Interés).")

    with col_esp:
        st.markdown("""
        <div style='
            padding: 2rem;
            border: 0.5px solid rgba(68,136,255,0.15);
            border-radius: 6px;
            background: linear-gradient(135deg, rgba(15,20,32,0.8) 0%, rgba(17,24,39,0.8) 100%);
            margin-top: 0.25rem;
        '>
            <div style='
                font-family: "DM Mono", monospace;
                font-size: 10px;
                letter-spacing: 0.15em;
                text-transform: uppercase;
                color: #4488FF;
                margin-bottom: 1.25rem;
            '>Módulos disponibles</div>
            <div style='
                font-family: "EB Garamond", Georgia, serif;
                font-size: 15px;
                color: #B0BACA;
                line-height: 2;
            '>
                <div style='color:#E8EDF5; margin-bottom: 0.25rem;'>Análisis de Brecha de Duración</div>
                <div style='color:#E8EDF5; margin-bottom: 0.25rem;'>RCS — Requerimiento de Capital de Solvencia</div>
                <div style='color:#E8EDF5; margin-bottom: 0.25rem;'>Optimización de Frontera Eficiente ALM</div>
                <div style='color:#E8EDF5; margin-bottom: 0.25rem;'>Monte Carlo bajo escenarios de tasas</div>
                <div style='color:#E8EDF5; margin-bottom: 0.25rem;'>Cumplimiento CUSF / Solvencia II</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: LOGIN INSTITUCIONAL
# ══════════════════════════════════════════════════════════════════════════════
with tab_login:

    st.markdown("""
    <div style='
        max-width: 420px;
        margin: 3rem auto 0;
        text-align: center;
    '>
        <div style='
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            color: #5A6780;
            margin-bottom: 2.5rem;
        '>Portal de Acceso Institucional</div>
    </div>
    """, unsafe_allow_html=True)

    col_esp1, col_log, col_esp2 = st.columns([1, 1.2, 1])
    
    with col_log:
        # Eliminamos el HTML conflictivo y dejamos los inputs directos
        st.text_input("ID Corporativo",              key="log_id")
        st.text_input("Llave de Acceso (Token)",     type="password", key="log_pass")

        if st.button("Autenticar Terminal", use_container_width=True):
            st.info("Módulo de autenticación corporativa en fase de despliegue.")

        st.markdown("""
        <div style='
            margin-top: 1.5rem;
            font-family: "DM Mono", monospace;
            font-size: 10px;
            letter-spacing: 0.06em;
            color: #2E3A4E;
            text-align: center;
            line-height: 1.6;
        '>
            Acceso exclusivo para clientes licenciados.<br>
            Para solicitar credenciales, contacte al equipo técnico.
        </div>
        """, unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='
    margin-top: 6rem;
    padding: 1.5rem 0;
    border-top: 0.5px solid rgba(68,136,255,0.1);
    display: flex;
    justify-content: space-between;
    align-items: center;
'>
    <div style='
        font-family: "DM Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.12em;
        color: #2E3A4E;
        text-transform: uppercase;
    '>Motor GaLa Quant Solutions</div>
    <div style='
        font-family: "DM Mono", monospace;
        font-size: 10px;
        letter-spacing: 0.08em;
        color: #2E3A4E;
    '>&copy; {datetime.now().year} &nbsp;·&nbsp; Todos los derechos reservados</div>
</div>
""", unsafe_allow_html=True)
