# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================
import streamlit as st
import numpy as np
from transformers import pipeline
import yfinance as yf
import math  

# ── 1. CARGA DEL MODELO EN MEMORIA CACHÉ ──
@st.cache_resource
def cargar_motor_finbert():
    # Requiere tener instalado 'transformers' y 'torch'
    return pipeline("sentiment-analysis", model="ProsusAI/finbert", top_k=3)

# ── 2. EL PUENTE ACTUARIAL DUAL (NLP + MOMENTUM) ──
def generar_vistas_black_litterman(tickers_temp): # <-- Eliminado el argumento llave_api
    vistas_generadas = []
    
    try:
        motor_ia = cargar_motor_finbert()
        ia_disponible = True
    except Exception as e:
        ia_disponible = False
        print(f"Advertencia: Motor IA desactivado. Detalle: {e}")

    VOLATILIDAD_BASE = 0.20
    FACTOR_SENSIBILIDAD = 0.50
    
    for ticker in tickers_temp:
        try:
            info_ticker = yf.Ticker(ticker)
            noticias_crudas = info_ticker.news
            
            # Extraemos títulos validando que existan y tengan sustancia
            textos = [n.get('title', '') for n in noticias_crudas[:5]] if noticias_crudas else []
            textos = [t for t in textos if isinstance(t, str) and len(t.strip()) > 10]
            
            sentimiento_promedio = 0.0
            
            # ── VÍA 1: INFERENCIA DE TEXTO (FINBERT) ──
            if textos and ia_disponible:
                resultados = motor_ia(textos)
                score_acumulado = 0.0
                for res in resultados:
                    prob_pos = next((x['score'] for x in res if x['label'] == 'positive'), 0.0)
                    prob_neg = next((x['score'] for x in res if x['label'] == 'negative'), 0.0)
                    score_acumulado += (prob_pos - prob_neg)
                sentimiento_promedio = score_acumulado / len(textos)
                
            # ── VÍA 2: INFERENCIA CUANTITATIVA (MOMENTUM) ──
            else:
                hist = info_ticker.history(period="1mo")
                
                if hist.empty or "Close" not in hist.columns:
                    continue  
                    
                hist_clean = hist["Close"].dropna()
                if len(hist_clean) < 2:
                    continue
                
                precio_inicial = float(hist_clean.iloc[0])
                precio_final = float(hist_clean.iloc[-1])
                
                if precio_inicial <= 0 or math.isnan(precio_inicial) or math.isnan(precio_final):
                    continue
                
                retorno_mensual = (precio_final / precio_inicial) - 1
                
                if math.isnan(retorno_mensual) or math.isinf(retorno_mensual):
                    continue
                
                # Suavizamos un poco el multiplicador (x5 = 20% para saturar)
                sentimiento_promedio = max(min(retorno_mensual * 5, 1.0), -1.0)

            # ── CÁLCULO DEL RENDIMIENTO ESPERADO (Q) ──
            rendimiento_proyectado = sentimiento_promedio * FACTOR_SENSIBILIDAD * VOLATILIDAD_BASE
            
            if math.isnan(rendimiento_proyectado) or math.isinf(rendimiento_proyectado):
                continue
            
            # Blindaje matemático para evitar matrices singulares en Omega
            if abs(rendimiento_proyectado) < 0.001:
                rendimiento_proyectado = 0.001 if sentimiento_promedio >= 0 else -0.001
                
            # Calibración de la Confianza
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
            
        except Exception:
            continue
            
    # Paracaídas de emergencia total
    if not vistas_generadas and tickers_temp:
        vistas_generadas.append({
            "activo_1": tickers_temp[0],
            "tipo": "absoluta",
            "rendimiento_esperado": 0.001,
            "confianza": "Baja"
        })

    return True, vistas_generadas
