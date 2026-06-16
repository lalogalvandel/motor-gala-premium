import streamlit as st
import numpy as np
from transformers import pipeline
import yfinance as yf

# ── 1. CARGA DEL MODELO EN MEMORIA CACHÉ ──
@st.cache_resource
def cargar_motor_finbert():
    # ProsusAI/finbert es el estándar Quant para noticias financieras
    return pipeline("sentiment-analysis", model="ProsusAI/finbert", top_k=3)

# ── 2. EL PUENTE ACTUARIAL DUAL (NLP + MOMENTUM) ──
def generar_vistas_black_litterman(noticias_macro, tickers_temp, llave_api=None):
    vistas_generadas = []
    
    # Intentamos cargar FinBERT, si falla no importa, el motor usará matemáticas puras
    try:
        motor_ia = cargar_motor_finbert()
        ia_disponible = True
    except Exception:
        ia_disponible = False

    VOLATILIDAD_BASE = 0.20
    FACTOR_SENSIBILIDAD = 0.50
    
    for ticker in tickers_temp:
        try:
            info_ticker = yf.Ticker(ticker)
            noticias_crudas = info_ticker.news
            
            textos = [n.get('title', '') for n in noticias_crudas[:5]] if noticias_crudas else []
            textos = [t for t in textos if len(t.strip()) > 10]
            
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
                
                # 1. PURIFICACIÓN DE DATOS (Anti-NaN)
                if "Close" in hist.columns:
                    hist = hist.dropna(subset=["Close"])
                    
                # Si después de limpiar no quedan al menos 2 días de datos, abortamos este activo
                if hist.empty or len(hist) < 2:
                    continue 
                
                precio_inicial = float(hist['Close'].iloc[0])
                precio_final = float(hist['Close'].iloc[-1])
                
                # 2. BLINDAJE MATEMÁTICO (División por cero o valores corruptos)
                if precio_inicial <= 0 or np.isnan(precio_inicial) or np.isnan(precio_final):
                    continue
                    
                retorno_mensual = (precio_final / precio_inicial) - 1
                
                # Normalizamos el retorno a un "score" de -1 a 1
                sentimiento_promedio = max(min(retorno_mensual * 10, 1.0), -1.0)

            # ── CÁLCULO DEL RENDIMIENTO ESPERADO (Q) ──
            rendimiento_proyectado = sentimiento_promedio * FACTOR_SENSIBILIDAD * VOLATILIDAD_BASE
            
            # 3. FILTRO FINAL: Si por alguna extraña razón el cálculo resultó en NaN, no lo guardamos
            if np.isnan(rendimiento_proyectado):
                continue
            # ── CÁLCULO DEL RENDIMIENTO ESPERADO (Q) ──
            rendimiento_proyectado = sentimiento_promedio * FACTOR_SENSIBILIDAD * VOLATILIDAD_BASE
            
            # Blindaje contra matrices singulares
            if abs(rendimiento_proyectado) < 0.001:
                rendimiento_proyectado = 0.001 if sentimiento_promedio >= 0 else -0.001
                
            # Calibración de la matriz Omega (Niveles de Confianza)
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
            continue
            
    # Paracaídas de emergencia si la bolsa de valores estuviera totalmente caída
    if not vistas_generadas:
        vistas_generadas.append({
            "activo_1": tickers_temp[0],
            "tipo": "absoluta",
            "rendimiento_esperado": 0.001,
            "confianza": "Baja"
        })

    return True, vistas_generadas
