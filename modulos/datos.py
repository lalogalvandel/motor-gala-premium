import yfinance as yf
import numpy as np
import pandas as pd
import os

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
  
import requests

# 1. RUTA ABSOLUTA A PRUEBA DE BALAS
# Esto le dice a Python exactamente dónde está tu carpeta motor_gala, estés donde estés.
directorio_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ruta_env = os.path.join(directorio_base, 'apiky.env')

# Forzamos la carga desde esa ruta exacta
load_dotenv(dotenv_path=ruta_env)

def obtener_tasa_referencia_banxico() -> float:
    """
    Se conecta al Banco de México y extrae la Tasa de Referencia actual en tiempo real.
    Devuelve la tasa en formato decimal.
    """
    token = st.secrets["TOKEN_BANXICO"]
    
    # Diagnóstico 1: ¿Leyó el archivo?
    if not token_banxico:
        print(f"🚨 ERROR FATAL: No se encontró BANXICO_TOKEN. Python buscó en: {ruta_env}")
        return 0.0650
        
    url = "https://www.banxico.org.mx/SieAPIRest/service/v1/series/SF61745/datos/oportuno"
    
    # 2. DISFRAZ INSTITUCIONAL (Evita que el Firewall de Banxico nos bloquee por ser un bot de Python)
    headers = {
        "Bmx-Token": token_banxico,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        respuesta = requests.get(url, headers=headers)
        
        # Diagnóstico 2: ¿Banxico nos bloqueó?
        if respuesta.status_code != 200:
            print(f"🚨 BANXICO RECHAZÓ LA CONEXIÓN. Código de error: {respuesta.status_code}")
            print(f"Mensaje del banco: {respuesta.text}")
            return 0.0650
            
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        tasa_str = datos['bmx']['series'][0]['datos'][0]['dato']
        tasa_decimal = float(tasa_str) / 100
        
        print(f"📡 ÉXITO: Tasa Banxico actualizada en vivo: {tasa_decimal * 100:.2f}%")
        return tasa_decimal
        
    except Exception as e:
        print(f"🚨 Falla crítica en el radar: {e}")
        return 0.0650
