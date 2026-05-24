import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from modulos.actuaria_alm import calcular_duracion_convexidad, optimizar_inmunizacion
from modulos.reportes import generar_pdf_inmunizacion
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

# ── CSS Institucional y Componentes ────────────────────────────────────────────
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

/* Componente de Métricas Globales */
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

/* Área Ingesta - File Uploader Refinado */
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

/* Tablas Corporativas */
[data-testid="stDataFrame"] {
    border: 0.5px solid rgba(68,136,255,0.12) !important;
    border-radius: 6px !important;
}

/* Botonera de Acción */
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

# ── Encabezado de Dos Columnas Consistente ─────────────────────────────────────
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


# ── MÓDULOS DE INGESTA (CON JERARQUÍA PROFESIONAL DE TRES NIVELES) ──────────────
st.markdown("""
<div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #4488FF; margin-bottom: 0.4rem;'>Paso 1: Mapeo de Balance</div>
<div style='font-family: "EB Garamond", Georgia, serif; font-size: 22px; color: #E8EDF5; font-weight: 400; margin-bottom: 1.5rem;'>Carga de Information Financiera</div>
""", unsafe_allow_html=True)

col_pasivos, col_activos = st.columns(2, gap="large")

with col_pasivos:
    st.markdown("""
    <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #FF6B6B; margin-bottom: 0.4rem;'>Obligaciones</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 18px; color: #E8EDF5; font-weight: 400; margin-bottom: 0.5rem;'>Matriz de Pasivos</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; font-style: italic; color: #5A6780; line-height: 1.6; margin-bottom: 1.25rem;'>
        Proyección de flujos de salida correspondientes a las deudas y reservas técnicas.
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
        Inventario actual de instrumentos de deuda elegibles dentro del balance corporativo.
    </div>
    <div style='padding: 0.8rem 1rem; background: rgba(68,136,255,0.03); border: 0.5px solid rgba(68,136,255,0.15); border-radius: 4px; font-family: "DM Mono", monospace; font-size: 10px; color: #5A6780; line-height: 1.8; margin-bottom: 1rem;'>
        Formatos admitidos &nbsp;·&nbsp; .xlsx &nbsp;/&nbsp; .csv<br>
        Columnas exigidas &nbsp;·&nbsp; <span style='color: #B0BACA;'>Instrumento</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Valor_Mercado</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Duracion</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Convexidad</span> &nbsp;/&nbsp; <span style='color: #B0BACA;'>Tasa_YTM</span>
    </div>
    """, unsafe_allow_html=True)
    archivo_activos = st.file_uploader("Cargar Activos", type=["xlsx", "csv"], label_visibility="collapsed", key="up_act")


# ── PROCESAMIENTO ACTUARIAL Y DIAGNÓSTICO DE RIESGO ────────────────────────────
st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)

if archivo_pasivos is not None and archivo_activos is not None:
    try:
        df_pasivos = pd.read_csv(archivo_pasivos) if archivo_pasivos.name.endswith('.csv') else pd.read_excel(archivo_pasivos)
        df_activos = pd.read_csv(archivo_activos) if archivo_activos.name.endswith('.csv') else pd.read_excel(archivo_activos)

        # Encabezado técnico de auditoría
        st.markdown("""
        <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.4rem;'>Validación</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 22px; color: #E8EDF5; font-weight: 400; margin-bottom: 1.5rem;'>Auditoría de Brecha Estructural</div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        valor_total_pasivos = df_pasivos['Flujo_Esperado'].sum()
        valor_total_activos = df_activos['Valor_Mercado'].sum()
        
        c1.metric("Valor Total Activos", f"${valor_total_activos:,.2f} M")
        c2.metric("Valor Total Pasivos", f"${valor_total_pasivos:,.2f} M")
        
        ratio = valor_total_activos / valor_total_pasivos
        c3.metric("Ratio de Cobertura", f"{ratio*100:.1f}%")

        # ── NUEVO: MÓDULO DE STRESS TESTING (SHOCKS MACROECONÓMICOS) ──
        st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #FF4B4B; margin-bottom: 0.4rem;'>Stress Test Macro (Solvencia II)</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 22px; color: #E8EDF5; font-weight: 400; margin-bottom: 1rem;'>Shock en Curva de Tasas de Interés</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; font-style: italic; color: #5A6780; line-height: 1.6; margin-bottom: 1.5rem;'>
            Desplace el control para simular un escenario adverso de política monetaria (movimiento paralelo de la curva) y reestructurar bajo estrés.
        </div>
        """, unsafe_allow_html=True)
        
        col_slider, col_esp = st.columns([1.5, 1])
        with col_slider:
            shock_bps = st.slider("Desplazamiento de Tasa (Puntos Base)", min_value=-300, max_value=300, value=0, step=25)
        
        # ── MOTOR DE OPTIMIZACIÓN ──
        st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
        
        if st.button("Ejecutar Inmunización Estocástica (SLSQP)", type="primary"):
            with st.spinner("Modelando escenarios y calculando calce óptimo..."):
                
                # Inyectamos el shock de estrés a la tasa libre de riesgo y a los yields de mercado
                tasa_base = 0.065
                tasa_estresada = tasa_base + (shock_bps / 10000.0)
                yields_estresados = df_activos['Tasa_YTM'].values + (shock_bps / 10000.0)
                
                # Exigencia del pasivo bajo el nuevo escenario
                valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(
                    df_pasivos['Flujo_Esperado'].values, 
                    df_pasivos['Año'].values, 
                    tasa_estresada
                )
                
                # Optimización de cartera
                resultado = optimizar_inmunizacion(
                    df_activos['Duracion'].values, 
                    df_activos['Convexidad'].values, 
                    yields_estresados, 
                    dur_pasivo, 
                    conv_pasivo
                )
                
                if resultado["exito"]:
                    st.markdown("---")
                    st.markdown("""
                    <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #17C37B; margin-bottom: 0.4rem;'>Paso 3: Reestructuración</div>
                    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 22px; color: #E8EDF5; font-weight: 400; margin-bottom: 1.5rem;'>Portafolio Óptimo de Cobertura</div>
                    """, unsafe_allow_html=True)

                    col_res_txt, col_res_plot = st.columns([1, 1.5], gap="large")
                    
                    with col_res_txt:
                        st.success(f"**Calce de Duración:** {resultado['duracion_lograda']:.2f} años")
                        st.info(f"**Yield Esperado:** {resultado['rendimiento_esperado']*100:.2f}%")
                        st.metric("Cobertura de Convexidad", f"{resultado['convexidad_lograda']:.2f}")
                        
                        st.markdown("<br><div style='font-family: \"DM Mono\", monospace; font-size: 10px; letter-spacing: 0.1em; color: #5A6780; text-transform: uppercase; margin-bottom: 0.5rem;'>Estructura Exigida</div>", unsafe_allow_html=True)
                        
                        # Corrección UI: Reemplazo de asteriscos por etiqueta <b> de HTML
                        for nombre, peso in zip(df_activos['Instrumento'].values, resultado["pesos"]):
                            if peso > 0.01:
                                st.markdown(f"<div style='color:#B0BACA; font-family: \"EB Garamond\", serif; font-size: 15px;'>&bull; <b>{nombre}:</b> {peso*100:.1f}%</div>", unsafe_allow_html=True)
                                
                    with col_res_plot:
                        labels_f = [n for n, p in zip(df_activos['Instrumento'].values, resultado["pesos"]) if p > 0.01]
                        valores_f = [p for p in resultado["pesos"] if p > 0.01]
                        
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=labels_f, 
                            values=valores_f, 
                            hole=.5,
                            textinfo='label+percent',
                            marker=dict(colors=['#4488FF', '#17C37B', '#d4a017', '#FF4B4B', '#9D4EDD'])
                        )])
                        fig_pie.update_layout(
                            showlegend=False,
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            margin=dict(t=10, b=10, l=10, r=10),
                            height=280,
                            font={'family': 'DM Mono', 'color': '#B0BACA', 'size': 11}
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                        # ── BOTÓN DE DESCARGA PDF ──
                        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
                        
                        # Generamos los bytes del reporte
                        pdf_bytes = generar_pdf_inmunizacion(
                            empresa=empresa_cliente,
                            val_activos=valor_total_activos,
                            val_pasivos=valor_total_pasivos,
                            ratio=ratio,
                            dur_lograda=resultado['duracion_lograda'],
                            yield_opt=resultado['rendimiento_esperado'],
                            conv_lograda=resultado['convexidad_lograda'],
                            nombres_inst=df_activos['Instrumento'].values,
                            pesos_inst=resultado['pesos'],
                            shock=shock_bps
                        )
                        
                        st.download_button(
                            label="Exportar Reporte Regulatorio (PDF)",
                            data=pdf_bytes,
                            file_name=f"Reporte_ALM_{empresa_cliente.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            type="secondary",
                            use_container_width=True
                        )
                else:
                    st.error("Riesgo estructural crítico: La cartera de activos cargada no cuenta con la liquidez, duración o convexidad suficiente para inmunizar el balance bajo este nivel de estrés.")
    except Exception as e:
        st.error(f"Error de formato. Columnas requeridas ausentes o estructura de datos inválida. Detalle técnico: {e}")
elif archivo_pasivos is not None or archivo_activos is not None:
    st.info("Aguardando ingesta del archivo complementario para inicializar diagnóstico ALM.")

# ── Cierre de sesión ───────────────────────────────────────────────────────────
st.markdown("---")
col_btn, col_esp = st.columns([1, 4])
with col_btn:
    if st.button("Cerrar sesión / Desconectar", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["empresa"]     = ""
        st.switch_page("app_institucional.py")
