import yfinance as yf
import numpy as np
import pandas as pd
import requests
import streamlit as st  # <-- AÑADIDO: Vital para usar st.secrets
from datetime import datetime

def cargar_datos(tickers: list, start: str = '2020-01-01', end: str = '2026-05-08') -> pd.DataFrame:
    """Descarga precios de cierre y elimina filas con NaN."""
    datos = yf.download(tickers, start=start, end=end, auto_adjust=True)['Close']
    return datos.dropna()

def calcular_retornos(datos: pd.DataFrame):
    """
    Retorna:
      - retornos_diarios  : log-retornos día a día
      - retornos_anuales  : media anualizada por activo
      - matriz_covarianza : covarianza anualizada
    """
    retornos_diarios = np.log(datos / datos.shift(1)).dropna()
    retornos_anuales = retornos_diarios.mean() * 252
    matriz_covarianza = retornos_diarios.cov() * 252
    return retornos_diarios, retornos_anuales, matriz_covarianza

def obtener_tasa_referencia_banxico() -> float:
    """
    Se conecta al Banco de México y extrae la Tasa de Referencia actual en tiempo real.
    Devuelve la tasa en formato decimal.
    """
    # 1. Extraemos directamente de la bóveda de Streamlit (Variable unificada)
    token_banxico = st.secrets["TOKEN_BANXICO"]
    
    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF61745/datos/oportuno"
    
    # 2. DISFRAZ INSTITUCIONAL (Evita que el Firewall nos bloquee)
    headers = {
        "Bmx-Token": token_banxico,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        respuesta = requests.get(url, headers=headers)
        
        # Diagnóstico: ¿Banxico nos bloqueó?
        if respuesta.status_code != 200:
            print(f"🚨 BANXICO RECHAZÓ LA CONEXIÓN. Código de error: {respuesta.status_code}")
            return 0.0650  # Fallback
            
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        tasa_str = datos['bmx']['series'][0]['datos'][0]['dato']
        tasa_decimal = float(tasa_str) / 100
        
        print(f"📡 ÉXITO: Tasa Banxico actualizada en vivo: {tasa_decimal * 100:.2f}%")
        return tasa_decimal
        
    except Exception as e:
        print(f"🚨 Falla crítica en el radar: {e}")
        return 0.0650
def obtener_uma_actual():
    """
    Devuelve la UMA diaria vigente basada en el año actual del sistema.
    La UMA entra en vigor el 1 de febrero de cada año.
    """
    hoy = datetime.now()
    anio = hoy.year
    mes = hoy.month
    
    # Si estamos en enero, todavía aplica la UMA del año anterior
    if mes == 1:
        anio -= 1
        
    # Diccionario histórico y actual de la UMA diaria (Fuente: INEGI)
    historico_uma = {
        2022: 96.22,
        2023: 103.74,
        2024: 108.57,
        2025: 112.50, # Valor de 2025
        2026: 114.00, # Valor vigente proyectado/actual para 2026
    }
    
    # Si el año no está en el diccionario (ej. 2027+ y olvidaste actualizar el código),
    # tomamos el último valor conocido sumándole una inflación estimada del 4%
    if anio not in historico_uma:
        ultimo_anio = max(historico_uma.keys())
        diferencia_anios = anio - ultimo_anio
        uma_estimada = historico_uma[ultimo_anio] * ((1 + 0.04) ** diferencia_anios)
        return round(uma_estimada, 2)
        
    return historico_uma[anio]
