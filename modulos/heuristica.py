import streamlit as st
import numpy as np
from transformers import pipeline

# ── 1. CARGA DEL MODELO EN MEMORIA CACHÉ ──
# Usamos @st.cache_resource para descargar el modelo de 400MB solo una vez.
# Si recargas la página, Streamlit usará el que ya está en la memoria RAM.
@st.cache_resource
def cargar_motor_finbert():
    # ProsusAI/finbert es el estándar de la industria Quant para noticias financieras
    return pipeline("sentiment-analysis", model="ProsusAI/finbert", top_k=3)

# ── 2. EL PUENTE ACTUARIAL (GENERADOR DE VISTAS) ──
def generar_vistas_black_litterman(noticias_macro, tickers_temp, llave_api=None):
    """
    Lee las noticias de Yahoo Finance, las procesa por FinBERT y calcula 
    el vector de expectativas para el modelo de Black-Litterman.
    (El parámetro llave_api se mantiene para no romper la compatibilidad con app.py)
    """
    vistas_generadas = []
    
    try:
        motor_ia = cargar_motor_finbert()
    except Exception as e:
        return False, [{"error": f"Fallo al cargar FinBERT: {e}"}]

    # Parámetros del puente matemático
    # En una versión futura, volatilidad_base puede calcularse dinámicamente desde la matriz de covarianza
    VOLATILIDAD_BASE = 0.20  # Asumimos 20% de volatilidad anual estándar
    FACTOR_SENSIBILIDAD = 0.50 # Qué tan agresivo es el impacto de la noticia en el precio
    
    for ticker in tickers_temp:
        # Filtramos las noticias específicas de este activo
        noticias_ticker = [n for n in noticias_macro if n.get('ticker') == ticker]
        
        if not noticias_ticker:
            continue
            
        # Extraemos textos limpios (título + resumen) limitando a las 5 más recientes para ser rápidos
        textos = [f"{n.get('title', '')} {n.get('summary', '')}" for n in noticias_ticker[:5]]
        textos = [t for t in textos if len(t.strip()) > 10]
        
        if not textos:
            continue
            
        # ── INFERENCIA DE LA RED NEURONAL ──
        # FinBERT devuelve algo como: [[{'label': 'positive', 'score': 0.8}, {'label': 'neutral', 'score': 0.15}...]]
        resultados = motor_ia(textos)
        
        score_acumulado = 0.0
        
        for res in resultados:
            # Extraemos las probabilidades de cada etiqueta
            prob_pos = next((x['score'] for x in res if x['label'] == 'positive'), 0.0)
            prob_neg = next((x['score'] for x in res if x['label'] == 'negative'), 0.0)
            
            # El sentimiento neto es Positivo menos Negativo
            score_acumulado += (prob_pos - prob_neg)
            
        sentimiento_promedio = score_acumulado / len(textos)
        
        # ── CÁLCULO DEL RENDIMIENTO ESPERADO (Q) ──
        rendimiento_proyectado = sentimiento_promedio * FACTOR_SENSIBILIDAD * VOLATILIDAD_BASE
        
        # Blindaje para evitar la Matriz Omega Singular (cero absoluto)
        if abs(rendimiento_proyectado) < 0.001:
            rendimiento_proyectado = 0.001 if sentimiento_promedio >= 0 else -0.001
            
        # Asignación probabilística de la Confianza
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
        
    if not vistas_generadas:
        # Si no hubo noticias en absoluto, forzamos una vista mínima para el primer activo y que la app no colapse
        vistas_generadas.append({
            "activo_1": tickers_temp[0],
            "tipo": "absoluta",
            "rendimiento_esperado": 0.001,
            "confianza": "Baja"
        })

    return True, vistas_generadas
