import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from supabase import create_client

from modulos.actuaria_alm import calcular_duracion_convexidad, optimizar_inmunizacion, calcular_rcs_mercado
from modulos.reportes import generar_pdf_inmunizacion
from modulos.estocastica import generar_escenarios_tasas, calcular_var_estocastico

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel ALM | Motor GaLa",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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
    
    /* ── EL ARREGLO MÁGICO ── */
    white-space: normal !important;   
    overflow: visible !important;   
    text-overflow: clip !important;  
    line-height: 1.4 !important;     
    display: block !important;       
    width: 100% !important;      
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
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: clamp(22px, 3vw, 32px); font-weight: 400; color: #E8EDF5; letter-spacing: 0.01em; line-height: 1.2;'>{empresa_cliente}</div>
    </div>
    """, unsafe_allow_html=True)

with col_session:
    st.markdown("""
    <div style='display: flex; justify-content: flex-end; align-items: flex-start; padding-top: 2rem;'>
        <div style='display: flex; align-items: center; gap: 7px; font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: #17C37B;'>
            <span style='width: 6px; height: 6px; background: #17C37B; border-radius: 50%; box-shadow: 0 0 6px rgba(23,195,123,0.5);'></span>
            Sesión activa
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-bottom: 2.5rem;'></div>", unsafe_allow_html=True)

# ── Paso 1: Ingesta (Simétrica y Limpia) ───────────────────────────────────────
st.markdown("""
<div style='margin-bottom: 1.75rem;'>
    <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.4rem;'>Paso 1 — Mapeo de Balance</div>
    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; font-weight: 400;'>Carga de Información Financiera</div>
</div>
""", unsafe_allow_html=True)

col_pasivos, col_activos = st.columns(2, gap="large")

df_pasivos = None
df_activos = None

if st.session_state.get("db_pasivos"):
    df_pasivos = pd.DataFrame(st.session_state["db_pasivos"])
if st.session_state.get("db_activos"):
    df_activos = pd.DataFrame(st.session_state["db_activos"])

def _badge_estado(sincronizado: bool) -> str:
    if sincronizado:
        return "<span style='display:inline-flex; align-items:center; gap:5px; font-family:\"DM Mono\",monospace; font-size:10px; letter-spacing:0.08em; text-transform:uppercase; color:#17C37B;'><span style='width:5px;height:5px;background:#17C37B; border-radius:50%;box-shadow:0 0 5px rgba(23,195,123,0.5);'></span>Sincronizado</span>"
    return "<span style='display:inline-flex; align-items:center; gap:5px; font-family:\"DM Mono\",monospace; font-size:10px; letter-spacing:0.08em; text-transform:uppercase; color:#5A6780;'><span style='width:5px;height:5px;background:#5A6780; border-radius:50%;'></span>Pendiente</span>"

with col_pasivos:
    st.markdown(f"""
    <div style='padding: 1.5rem 1.75rem 1.25rem; background: rgba(255,107,107,0.02); border: 0.5px solid rgba(255,107,107,0.15); border-radius: 6px; margin-bottom: 0.75rem; height: 100%;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #FF6B6B;'>Obligaciones</div>
            {_badge_estado(df_pasivos is not None)}
        </div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 18px; color: #E8EDF5; margin-bottom: 0.6rem;'>Matriz de Pasivos</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; font-style: italic; color: #5A6780; line-height: 1.6; margin-bottom: 1rem;'>Proyección de flujos de salida correspondientes a las reservas técnicas.</div>
        <div style='font-family: "DM Mono", monospace; font-size: 10px; color: #2E3A4E; letter-spacing: 0.04em; line-height: 1.8; margin-bottom: 1.25rem;'>Columnas &nbsp;·&nbsp; <span style="color:#B0BACA;">Año</span> &nbsp;/&nbsp; <span style="color:#B0BACA;">Flujo_Esperado</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    archivo_pasivos = st.file_uploader("Pasivos", type=["xlsx", "csv"], label_visibility="collapsed", key="up_pas")
    if archivo_pasivos is not None:
        df_temp = pd.read_csv(archivo_pasivos) if archivo_pasivos.name.endswith('.csv') else pd.read_excel(archivo_pasivos)
        datos_json = df_temp.to_dict(orient="records")
        if st.session_state.get("db_pasivos") != datos_json:
            st.session_state["db_pasivos"] = datos_json
            try: db.table("usuarios_b2b").update({"pasivos_json": datos_json}).eq("id_corp", st.session_state.get("id_corp", "")).execute()
            except: pass
            st.rerun()

with col_activos:
    st.markdown(f"""
    <div style='padding: 1.5rem 1.75rem 1.25rem; background: rgba(68,136,255,0.02); border: 0.5px solid rgba(68,136,255,0.15); border-radius: 6px; margin-bottom: 0.75rem; height: 100%;'>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #4488FF;'>Inversiones</div>
            {_badge_estado(df_activos is not None)}
        </div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 18px; color: #E8EDF5; margin-bottom: 0.6rem;'>Cartera de Activos</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; font-style: italic; color: #5A6780; line-height: 1.6; margin-bottom: 1rem;'>Inventario actual de instrumentos de deuda elegibles dentro del balance.</div>
        <div style='font-family: "DM Mono", monospace; font-size: 10px; color: #2E3A4E; letter-spacing: 0.04em; line-height: 1.8; margin-bottom: 1.25rem;'>Columnas &nbsp;·&nbsp; <span style="color:#B0BACA;">Instrumento</span> &nbsp;/&nbsp; <span style="color:#B0BACA;">Valor_Mercado</span> &nbsp;/&nbsp; <span style="color:#B0BACA;">Duracion</span> &nbsp;/&nbsp; <span style="color:#B0BACA;">Convexidad</span> &nbsp;/&nbsp; <span style="color:#B0BACA;">Tasa_YTM</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    archivo_activos = st.file_uploader("Activos", type=["xlsx", "csv"], label_visibility="collapsed", key="up_act")
    if archivo_activos is not None:
        df_temp = pd.read_csv(archivo_activos) if archivo_activos.name.endswith('.csv') else pd.read_excel(archivo_activos)
        datos_json = df_temp.to_dict(orient="records")
        if st.session_state.get("db_activos") != datos_json:
            st.session_state["db_activos"] = datos_json
            try: db.table("usuarios_b2b").update({"activos_json": datos_json}).eq("id_corp", st.session_state.get("id_corp", "")).execute()
            except: pass
            st.rerun()

# ── Procesamiento actuarial ────────────────────────────────────────────────────
st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)

if df_pasivos is not None and df_activos is not None:
    try:
        st.markdown("---")

        # ── Paso 2: Calibración y Parámetros ──
        st.markdown("""
        <div style='margin-bottom: 1.75rem;'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.4rem;'>Paso 2 — Calibración y Escenarios</div>
            <div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; font-weight: 400;'>Parámetros de Riesgo (Solvencia II)</div>
        </div>
        """, unsafe_allow_html=True)

        col_param1, col_param2 = st.columns(2, gap="large")
        with col_param1:
            vol_cartera = st.slider(
                "Volatilidad Anual del Portafolio (%)",
                min_value=0.0, max_value=0.30, value=0.08, step=0.01, format="%.2f",
                help="Nivel de volatilidad estimado para el cálculo regulatorio del RCS."
            )
        with col_param2:
            shock_bps = st.slider(
                "Shock en Curva de Tasas (Puntos Base)", 
                min_value=-300, max_value=300, value=0, step=25,
                help="Desplazamiento paralelo para simular estrés de política monetaria."
            )

        # ── Paso 3: Auditoría y RCS ──
        st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='margin-bottom: 1.75rem;'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.4rem;'>Paso 3 — Validación Regulatoria</div>
            <div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; font-weight: 400;'>Auditoría de Brecha Estructural y Capital</div>
        </div>
        """, unsafe_allow_html=True)

        valor_total_pasivos = df_pasivos['Flujo_Esperado'].sum()
        valor_total_activos = df_activos['Valor_Mercado'].sum()
        ratio               = valor_total_activos / valor_total_pasivos
        rcs                 = calcular_rcs_mercado(valor_total_activos, vol_cartera)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Activos totales",   f"${valor_total_activos:,.2f} M")
        c2.metric("Pasivos nominales", f"${valor_total_pasivos:,.2f} M")
        
        if ratio >= 1:
            c3.metric("Ratio de cobertura", f"{ratio*100:.1f}%", "Suficiente")
        else:
            c3.metric("Ratio de cobertura", f"{ratio*100:.1f}%", "-Déficit", delta_color="inverse")
            
        c4.metric("RCS (Riesgo Mercado)", f"${rcs:,.2f} M", "-Capital Exigido", delta_color="inverse")

        # ── Paso 4: Optimizador ──
        st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
        col_btn_opt, col_esp = st.columns([1, 3])
        with col_btn_opt:
            ejecutar = st.button("Ejecutar Inmunización SLSQP", type="primary", use_container_width=True)

        if ejecutar:
            with st.spinner("Modelando escenarios y calculando calce óptimo..."):
                tasa_base      = 0.065
                tasa_estresada = tasa_base + (shock_bps / 10000.0)
                yields_estresados = df_activos['Tasa_YTM'].values + (shock_bps / 10000.0)

                valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(
                    df_pasivos['Flujo_Esperado'].values, df_pasivos['Año'].values, tasa_estresada
                )
                resultado = optimizar_inmunizacion(
                    df_activos['Duracion'].values, df_activos['Convexidad'].values, yields_estresados, dur_pasivo, conv_pasivo
                )

                if resultado["exito"]:
                    st.markdown("---")
                    st.markdown("""
                    <div style='margin-bottom: 1.75rem;'>
                        <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #17C37B; margin-bottom: 0.4rem;'>Paso 4 — Reestructuración</div>
                        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; font-weight: 400;'>Portafolio Óptimo de Cobertura</div>
                    </div>
                    """, unsafe_allow_html=True)

                    col_res_txt, col_res_plot = st.columns([1, 1.5], gap="large")

                    with col_res_txt:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Duración lograda",    f"{resultado['duracion_lograda']:.2f} años")
                        c2.metric("Yield esperado",      f"{resultado['rendimiento_esperado']*100:.2f}%")
                        c3.metric("Convexidad lograda",  f"{resultado['convexidad_lograda']:.2f}")

                        st.markdown("""
                        <div style='margin-top: 1.5rem; font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.75rem; padding-bottom: 0.4rem; border-bottom: 0.5px solid rgba(68,136,255,0.12);'>
                            Estructura de Cobertura
                        </div>
                        """, unsafe_allow_html=True)

                        for nombre, peso in zip(df_activos['Instrumento'].values, resultado["pesos"]):
                            if peso > 0.01:
                                st.markdown(f"""
                                <div style='display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0; border-bottom: 0.5px solid rgba(68,136,255,0.06);'>
                                    <span style='font-family: "EB Garamond", Georgia, serif; font-size: 15px; color: #B0BACA;'>{nombre}</span>
                                    <span style='font-family: "DM Mono", monospace; font-size: 12px; color: #4488FF;'>{peso*100:.1f}%</span>
                                </div>
                                """, unsafe_allow_html=True)

                        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)

                        pdf_bytes = generar_pdf_inmunizacion(
                            empresa_cliente, valor_total_activos, valor_total_pasivos, ratio,
                            resultado['duracion_lograda'], resultado['rendimiento_esperado'], resultado['convexidad_lograda'],
                            df_activos['Instrumento'].values, resultado['pesos'], shock_bps
                        )
                        st.download_button(
                            label     = "Exportar reporte regulatorio (PDF)",
                            data      = pdf_bytes,
                            file_name = f"Reporte_ALM_{empresa_cliente.replace(' ', '_')}.pdf",
                            mime      = "application/pdf",
                            type      = "secondary",
                            use_container_width=True
                        )

                    with col_res_plot:
                        labels_f  = [n for n, p in zip(df_activos['Instrumento'].values, resultado["pesos"]) if p > 0.01]
                        valores_f = [p for p in resultado["pesos"] if p > 0.01]

                        fig_pie = go.Figure(data=[go.Pie(
                            labels=labels_f, values=valores_f, hole=0.55, textinfo='label+percent',
                            marker=dict(colors=['#4488FF','#17C37B','#d4a017','#FF4B4B','#9D4EDD'], line=dict(color='#0C0F14', width=2)),
                            textfont=dict(family='DM Mono', size=10, color='#B0BACA'),
                        )])
                        fig_pie.add_annotation(text="Cobertura", x=0.5, y=0.5, font=dict(family='EB Garamond', size=13, color='#5A6780'), showarrow=False)
                        fig_pie.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=16, b=16, l=16, r=16), height=300)
                        st.plotly_chart(fig_pie, use_container_width=True)

                else:
                    st.error("La cartera de activos no cuenta con duración o liquidez suficiente para inmunizar el balance bajo el nivel de estrés configurado. Revise la composición de la cartera o reduzca el shock aplicado.")

    except Exception as e:
        st.error(f"Error de formato. Verifique que ambos archivos contengan las columnas requeridas. Detalle: {e}")

elif df_pasivos is None or df_activos is None:
    st.markdown("""
    <div style='margin-top: 1rem; padding: 1rem 1.5rem; border: 0.5px solid rgba(212,160,23,0.2); border-left: 2px solid rgba(212,160,23,0.4); border-radius: 4px; background: rgba(212,160,23,0.02); font-family: "DM Mono", monospace; font-size: 11px; letter-spacing: 0.04em; color: #d4a017;'>
        Pendiente &nbsp;·&nbsp; Cargue ambos archivos para inicializar el diagnóstico ALM.
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; margin-bottom: 1.5rem;'>
    Simulación Estocástica (Monte Carlo)
</div>
""", unsafe_allow_html=True)

if st.button("Ejecutar 1,000 Escenarios de Mercado"):
    with st.spinner("Proyectando caminos de tasas..."):
        escenarios = generar_escenarios_tasas(0.065, 1000, 12, 0.15, 0.065, 0.02)
        
        # Gráfico
        fig_mc = go.Figure()
        for i in range(50):
            fig_mc.add_trace(go.Scatter(y=escenarios[:, i], line=dict(color='rgba(68,136,255,0.1)', width=1)))
        fig_mc.update_layout(
            title="Proyección de Tasas (Vasicek)",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#1E2535'),
            height=300, showlegend=False
        )
        st.plotly_chart(fig_mc, use_container_width=True)

        # VaR
        var_95 = calcular_var_estocastico(escenarios, confianza=0.95)
        st.markdown(f"""
        <div style='background: rgba(68,136,255,0.05); padding: 1.5rem; border-radius: 6px; border: 0.5px solid rgba(68,136,255,0.2);'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; text-transform: uppercase; color: #4488FF;'>Resultado del Análisis Estocástico</div>
            <div style='font-family: "EB Garamond", Georgia, serif; font-size: 20px; color: #E8EDF5;'>
                VaR (95% confianza): <b>{abs(var_95)*10000:.1f} bps</b>
            </div>
            <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; color: #5A6780; font-style: italic;'>
                Existe un 5% de probabilidad de que el shock en la tasa de interés supere los {abs(var_95)*10000:.1f} puntos base.
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── Cierre de sesión ───────────────────────────────────────────────────────────
st.markdown("---")
col_btn, col_esp = st.columns([1, 4])
with col_btn:
    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["empresa"]     = ""
        st.session_state["db_pasivos"]  = None
        st.session_state["db_activos"]  = None
        st.switch_page("app_institucional.py")
