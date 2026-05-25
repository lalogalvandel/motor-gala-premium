import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from supabase import create_client
import requests  # nuevo

from modulos.actuaria_alm import (
    calcular_duracion_convexidad, optimizar_inmunizacion, calcular_rcs_mercado,
    frontera_eficiente_alm  # nueva función
)
from modulos.reportes import generar_pdf_inmunizacion
from modulos.estocastica import generar_escenarios_tasas, calcular_var_excedente  # modificado

# ── Configuración de página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Panel ALM | Motor GaLa",
    page_icon="logo_gala-removebg-preview.png",
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

# ── API Banxico (tasa dinámica) ─────────────────────────────────────────────────
@st.cache_data(ttl=21600)
def obtener_tasa_libre_riesgo():
    try:
        token = st.secrets["TOKEN_BANXICO"]
        url_banxico = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF43936/datos/oportuno?token={token}"
        response = requests.get(url_banxico, headers={"Accept": "application/json"}, timeout=5)
        if response.status_code == 200:
            str_valor = response.json()["series"][0]["datos"][0]["dato"]
            return float(str_valor) / 100
    except:
        pass
    return 0.065

# ── CSS ────────────────────────────────────────────────────────────────────────
# (idéntico al que ya tienes)
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
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: #5A6780 !important;
    
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-wrap: break-word !important;
    line-height: 1.4 !important;
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

col_logo, col_texto, col_session = st.columns([0.6, 2.4, 1], vertical_alignment="center")

with col_logo:
    st.image("logo_gala.png", use_container_width=True)

with col_texto:
    st.markdown(f"""
    <div style='display: flex; flex-direction: column; justify-content: center; border-left: 1px solid rgba(68,136,255,0.2); padding-left: 2.5rem; margin-left: 0.5rem; min-height: 70px;'>
        <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #4488FF; margin-bottom: 0.4rem;'>Terminal ALM Institucional</div>
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: clamp(22px, 3vw, 32px); font-weight: 400; color: #E8EDF5; letter-spacing: 0.01em; line-height: 1.2;'>{empresa_cliente}</div>
    </div>
    """, unsafe_allow_html=True)

with col_session:
    st.markdown("""
    <div style='display: flex; justify-content: flex-end; align-items: center; height: 100%;'>
        <div style='display: flex; align-items: center; gap: 7px; font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: #17C37B;'>
            <span style='width: 6px; height: 6px; background: #17C37B; border-radius: 50%; box-shadow: 0 0 6px rgba(23,195,123,0.5);'></span>
            Sesión activa
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='border-bottom: 0.5px solid rgba(68,136,255,0.15); margin-top: 1rem; margin-bottom: 2.5rem;'></div>", unsafe_allow_html=True)

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
    # Obtener tasa dinámica
    tasa_mercado = obtener_tasa_libre_riesgo()
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

        # Valores base
        valor_total_pasivos = df_pasivos['Flujo_Esperado'].sum()
        valor_total_activos = df_activos['Valor_Mercado'].sum()
        ratio = valor_total_activos / valor_total_pasivos

        # RCS paramétrico (VaR de mercado) – mantenemos como referencia
        rcs_mercado = calcular_rcs_mercado(valor_total_activos, vol_cartera)

        # ── SCR de Tasa de Interés (con tasa dinámica) ──
        # Duración promedio actual de los activos (ponderada por valor de mercado)
        d_activos_actual = np.average(df_activos['Duracion'].values, weights=df_activos['Valor_Mercado'].values)

        # Usamos la tasa de Banxico (dinámica)
        tasa_base = tasa_mercado
        delta_y = shock_bps / 10000.0

        # 1) Activos estresados: aproximación de segundo orden por instrumento
        valores_estresados_activos = 0.0
        for _, row in df_activos.iterrows():
            v = row['Valor_Mercado']
            d_mod = row['Duracion']          # asumimos que ya es duración modificada
            c = row['Convexidad']
            v_stress = v * (1 - d_mod * delta_y + 0.5 * c * (delta_y ** 2))
            valores_estresados_activos += v_stress

        # 2) Pasivos estresados: recalculamos VP exacto con la tasa estresada
        flujos = df_pasivos['Flujo_Esperado'].values
        tiempos = df_pasivos['Año'].values
        tasa_estresada = tasa_base + delta_y
        valores_presentes_estresados = flujos * (1 + tasa_estresada) ** -tiempos
        valor_estresado_pasivos = np.sum(valores_presentes_estresados)

        # 3) Excedente en escenario base y estresado
        excedente_base = valor_total_activos - valor_total_pasivos
        excedente_stress = valores_estresados_activos - valor_estresado_pasivos

        # Shock inverso para capturar el peor caso
        delta_y_neg = -shock_bps / 10000.0
        valores_estresados_activos_neg = 0.0
        for _, row in df_activos.iterrows():
            v = row['Valor_Mercado']
            d_mod = row['Duracion']
            c = row['Convexidad']
            v_stress_neg = v * (1 - d_mod * delta_y_neg + 0.5 * c * (delta_y_neg ** 2))
            valores_estresados_activos_neg += v_stress_neg
        tasa_estresada_neg = tasa_base + delta_y_neg
        vp_pasivos_neg = np.sum(flujos * (1 + tasa_estresada_neg) ** -tiempos)
        excedente_stress_neg = valores_estresados_activos_neg - vp_pasivos_neg

        # Pérdida máxima entre ambos escenarios
        perdida_pos = excedente_base - excedente_stress
        perdida_neg = excedente_base - excedente_stress_neg
        scr_tasa = max(perdida_pos, perdida_neg, 0)

        # Ratio estresado (escenario que generó la pérdida máxima)
        if perdida_pos >= perdida_neg:
            ratio_estresado = valores_estresados_activos / valor_estresado_pasivos
        else:
            ratio_estresado = valores_estresados_activos_neg / vp_pasivos_neg

        # ── Métricas de auditoría ──
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Activos totales",   f"${valor_total_activos:,.2f} M")
        c2.metric("Pasivos nominales", f"${valor_total_pasivos:,.2f} M")
        if ratio >= 1:
            c3.metric("Ratio de cobertura", f"{ratio*100:.1f}%", "Suficiente")
        else:
            c3.metric("Ratio de cobertura", f"{ratio*100:.1f}%", "-Déficit", delta_color="inverse")
        c4.metric("SCR Tasa de Interés", f"${scr_tasa:,.2f} M", help="Pérdida máxima en excedente ante shock de tasas")

        # ── Cumplimiento Normativo ──
        st.markdown("---")
        st.markdown("""
        <div style='margin-bottom: 1.25rem;'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.3rem;'>Cumplimiento CUSF / Solvencia II</div>
        </div>
        """, unsafe_allow_html=True)

        # Evaluación de cumplimiento
        cumple_ratio = ratio >= 1.0
        capital_disponible = excedente_base
        cumple_capital = capital_disponible >= scr_tasa
        cumple_estres = ratio_estresado >= 1.0

        if cumple_ratio and cumple_capital and cumple_estres:
            color_semaforo = "#17C37B"
            dictamen = "Cumplimiento satisfactorio"
        elif cumple_ratio and not cumple_capital:
            color_semaforo = "#d4a017"
            dictamen = "Condicionado — Capital insuficiente para SCR de tasa"
        else:
            color_semaforo = "#FF4B4B"
            dictamen = "Insuficiente — No se alcanza el ratio de cobertura mínimo"

        col_cump1, col_cump2, col_cump3 = st.columns(3)
        col_cump1.metric("Ratio de cobertura (mín. 100%)", f"{ratio*100:.1f}%", 
                         "✓" if cumple_ratio else "✗")
        col_cump2.metric("Capital disponible vs SCR tasa", f"${capital_disponible:,.2f} M",
                         f"Excede en ${capital_disponible - scr_tasa:,.2f} M" if cumple_capital else f"Déficit de ${scr_tasa - capital_disponible:,.2f} M")
        col_cump3.metric("Ratio estresado (shock {shock_bps} pb)".format(shock_bps=shock_bps), f"{ratio_estresado*100:.1f}%",
                         "✓" if cumple_estres else "✗")

        st.markdown(f"""
        <div style='margin-top: 1rem; padding: 1rem 1.25rem; border-left: 3px solid {color_semaforo}; background: rgba(68,136,255,0.02); border-radius: 4px;'>
            <span style='font-family: "DM Mono", monospace; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; color: {color_semaforo};'>{dictamen}</span>
            <span style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; color: #B0BACA; margin-left: 1rem;'>{'Todos los indicadores dentro de límites regulatorios.' if color_semaforo == '#17C37B' else 'Se requiere fortalecer la posición de capital o reducir exposición a tasa.'}</span>
        </div>
        """, unsafe_allow_html=True)

                # ── Paso 4: Optimizador ──
        st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
        col_btn_opt, col_esp = st.columns([1, 3])
        with col_btn_opt:
            ejecutar = st.button("Ejecutar Inmunización SLSQP", type="primary", use_container_width=True)

        if ejecutar:
            with st.spinner("Modelando escenarios y calculando calce óptimo..."):
                # La tasa estresada se construye a partir de la dinámica
                tasa_estresada_opt = tasa_mercado + (shock_bps / 10000.0)
                yields_estresados = df_activos['Tasa_YTM'].values + (shock_bps / 10000.0)

                valor_pasivo, dur_pasivo, conv_pasivo = calcular_duracion_convexidad(
                    df_pasivos['Flujo_Esperado'].values, df_pasivos['Año'].values, tasa_estresada_opt
                )

                resultado = optimizar_inmunizacion(
                    df_activos['Duracion'].values,
                    df_activos['Convexidad'].values,
                    yields_estresados,
                    dur_pasivo,
                    conv_pasivo,
                    v_activos=valor_total_activos,
                    v_pasivos=valor_total_pasivos,
                    vol_activos=vol_cartera,
                    d_activos=d_activos_actual
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

        # ── Paso 5: Frontera Eficiente (NUEVO) ──
        st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='margin-bottom: 1.75rem;'>
            <div style='font-family: "DM Mono", monospace; font-size: 10px; letter-spacing: 0.2em; text-transform: uppercase; color: #5A6780; margin-bottom: 0.4rem;'>Paso 5 — Frontera Eficiente</div>
            <div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; font-weight: 400;'>Optimización de Frontera Eficiente ALM</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Calcular Frontera Eficiente", type="primary"):
            with st.spinner("Trazando frontera eficiente..."):
                # Convexidad del pasivo ajustada
                ratio_ap = valor_total_pasivos / valor_total_activos
                conv_pasivo_est = (dur_pasivo_actual**2 + dur_pasivo_actual/(1+tasa_mercado)) * ratio_ap
                frontera = frontera_eficiente_alm(
                    df_activos['Duracion'].values,
                    df_activos['Convexidad'].values,
                    yields_estresados,  # o los rendimientos base
                    dur_pasivo_actual,
                    conv_pasivo_est,
                    v_activos=valor_total_activos,
                    v_pasivos=valor_total_pasivos,
                    vol_activos=vol_cartera,
                    d_activos=d_activos_actual,
                    num_puntos=20
                )

                # Graficar
                puntos_validos = [p for p in frontera if p["exito"]]
                if puntos_validos:
                    yields = [p["yield"]*100 for p in puntos_validos]
                    scrs = [p["scr_est"] for p in puntos_validos]
                    duraciones = [p["duracion"] for p in puntos_validos]

                    fig_frontera = go.Figure()
                    fig_frontera.add_trace(go.Scatter(
                        x=scrs, y=yields, mode='lines+markers',
                        marker=dict(size=8, color='#4488FF'),
                        line=dict(color='#4488FF', width=2),
                        name='Frontera eficiente',
                        hovertemplate='SCR: %{x:.2f} M<br>Yield: %{y:.2f}%<br>Duración: %{customdata:.2f} años',
                        customdata=duraciones
                    ))
                    fig_frontera.update_layout(
                        title="Frontera Eficiente: Yield vs SCR de Tasa",
                        xaxis_title="SCR estimado (M MXN)",
                        yaxis_title="Yield esperado (%)",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='DM Mono', color='#B0BACA'),
                        height=400
                    )
                    st.plotly_chart(fig_frontera, use_container_width=True)

                    # Permitir seleccionar punto
                    seleccion = st.selectbox("Seleccione un punto de la frontera para ver la composición",
                                             [f"{d:.2f} años / {y:.2f}% yield" for d, y in zip(duraciones, yields)])
                    idx = [f"{d:.2f} años / {y:.2f}% yield" for d, y in zip(duraciones, yields)].index(seleccion)
                    pesos_opt = puntos_validos[idx]["pesos"]
                    st.markdown("**Composición del portafolio seleccionado:**")
                    for nombre, peso in zip(df_activos['Instrumento'].values, pesos_opt):
                        if peso > 0.01:
                            st.markdown(f"- {nombre}: {peso*100:.1f}%")
                else:
                    st.warning("No se pudo construir la frontera eficiente con los parámetros actuales.")

        # ── Simulación Estocástica (mejorada) ──
        st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-family: "EB Garamond", Georgia, serif; font-size: 24px; color: #E8EDF5; margin-bottom: 1.5rem;'>
            Simulación Estocástica (Monte Carlo)
        </div>
        """, unsafe_allow_html=True)

        if st.button("Ejecutar Simulación de VaR del Excedente"):
            with st.spinner("Calculando distribución de pérdidas..."):
                # Parámetros Vasicek (podrían ser ajustables)
                kappa = 0.15
                theta = tasa_mercado
                sigma = 0.02
                n_escenarios = 1000
                n_pasos = 12

                var_99_5, perdidas, tasas_finales = calcular_var_excedente(
                    df_pasivos['Flujo_Esperado'].values,
                    df_pasivos['Año'].values,
                    valor_total_activos,
                    d_activos_actual,
                    np.average(df_activos['Convexidad'].values, weights=df_activos['Valor_Mercado'].values),
                    tasa_mercado,
                    n_escenarios, n_pasos, kappa, theta, sigma
                )

                # Histograma de pérdidas
                fig_hist = go.Figure(data=[go.Histogram(x=perdidas, nbinsx=50, marker_color='#4488FF')])
                fig_hist.update_layout(
                    title="Distribución de Pérdidas del Excedente (1 año)",
                    xaxis_title="Pérdida (M MXN)",
                    yaxis_title="Frecuencia",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='DM Mono', color='#B0BACA'),
                    height=300
                )
                st.plotly_chart(fig_hist, use_container_width=True)

                st.markdown(f"""
                <div style='background: rgba(68,136,255,0.05); padding: 1.5rem; border-radius: 6px; border: 0.5px solid rgba(68,136,255,0.2);'>
                    <div style='font-family: "DM Mono", monospace; font-size: 10px; text-transform: uppercase; color: #4488FF;'>VaR del Excedente (99.5% confianza)</div>
                    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 20px; color: #E8EDF5;'>
                        <b>${var_99_5:,.2f} M</b>
                    </div>
                    <div style='font-family: "EB Garamond", Georgia, serif; font-size: 14px; color: #5A6780; font-style: italic;'>
                        Con un 99.5% de confianza, la pérdida en el excedente no superará este monto en un horizonte de 1 año bajo el modelo Vasicek.
                    </div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error de formato. Verifique que ambos archivos contengan las columnas requeridas. Detalle: {e}")

elif df_pasivos is None or df_activos is None:
    st.markdown("""
    <div style='margin-top: 1rem; padding: 1rem 1.5rem; border: 0.5px solid rgba(212,160,23,0.2); border-left: 2px solid rgba(212,160,23,0.4); border-radius: 4px; background: rgba(212,160,23,0.02); font-family: "DM Mono", monospace; font-size: 11px; letter-spacing: 0.04em; color: #d4a017;'>
        Pendiente &nbsp;·&nbsp; Cargue ambos archivos para inicializar el diagnóstico ALM.
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
