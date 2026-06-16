import streamlit as st
import numpy as np
from transformers import pipeline
import yfinance as yf  # <── IMPORTANTE: Agregamos el conector directo a la bolsa

# ── 1. CARGA DEL MODELO EN MEMORIA CACHÉ ──
@st.cache_resource
def cargar_motor_finbert():
    # ProsusAI/finbert es el estándar Quant para noticias financieras
    return pipeline("sentiment-analysis", model="ProsusAI/finbert", top_k=3)

# ── 2. EL PUENTE ACTUARIAL (GENERADOR DE VISTAS) ──
def generar_vistas_black_litterman(noticias_macro, tickers_temp, llave_api=None):
    vistas_generadas = []
    
    try:
        motor_ia = cargar_motor_finbert()
    except Exception as e:
        return False, [{"error": f"Fallo al cargar FinBERT: {e}"}]

    VOLATILIDAD_BASE = 0.20
    FACTOR_SENSIBILIDAD = 0.50
    
    for ticker in tickers_temp:
        try:
            # ── INGESTA DIRECTA Y PRECISA ──
            # Ignoramos la caja revuelta de 'noticias_macro' y descargamos directo de la fuente
            info_ticker = yf.Ticker(ticker)
            noticias_crudas = info_ticker.news
            
            if not noticias_crudas:
                continue
                
            # Extraemos solo los títulos (FinBERT es experto en titulares puros)
            textos = [n.get('title', '') for n in noticias_crudas[:5]]
            textos = [t for t in textos if len(t.strip()) > 10]
            
            if not textos:
                continue
                
            # ── INFERENCIA MATEMÁTICA LOCAL ──
            resultados = motor_ia(textos)
            
            score_acumulado = 0.0
            for res in resultados:
                prob_pos = next((x['score'] for x in res if x['label'] == 'positive'), 0.0)
                prob_neg = next((x['score'] for x in res if x['label'] == 'negative'), 0.0)
                score_acumulado += (prob_pos - prob_neg)
                
            sentimiento_promedio = score_acumulado / len(textos)
            rendimiento_proyectado = sentimiento_promedio * FACTOR_SENSIBILIDAD * VOLATILIDAD_BASE
            
            if abs(rendimiento_proyectado) < 0.001:
                rendimiento_proyectado = 0.001 if sentimiento_promedio >= 0 else -0.001
                
            if abs(sentimiento_promedio) >= 0.60:
                confianza = "Alta"
            elif abs(sentimiento_promedio) >= 0.25:
                confianza = "Media"
            else:
                confianza = "Baja"
                
            vistas_generadas.append({
                "activo_1": ticker,
                "tipo": "absoluta",
                "rendimiento_esperado": round(rendimiento_proyectado, 4),
                "confianza": confianza
            })
            
        except Exception as e:
            # Si un ticker no tiene datos o falla, la ejecución sigue sin detener la firma entera
            continue
            
    if not vistas_generadas:
        vistas_generadas.append({
            "activo_1": tickers_temp[0],
            "tipo": "absoluta",
            "rendimiento_esperado": 0.001,
            "confianza": "Baja"
        })

    return True, vistas_generadas
