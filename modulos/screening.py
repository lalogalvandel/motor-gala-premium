import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import concurrent.futures
import warnings
import requests 
import io

warnings.filterwarnings("ignore")

# ── 1. WEB SCRAPING DINÁMICO (MODO DISFRAZ) ──
# ── 1. WEB SCRAPING DINÁMICO (MODO DISFRAZ) ──
def obtener_sp500():
    """Descarga la lista de tickers del S&P 500 simulando ser un navegador."""
    try:
        # Disfraz de Chrome actualizado para evadir firewalls
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        respuesta = requests.get(url, headers=headers)
        respuesta.raise_for_status() # Lanza error si Wikipedia nos bloquea
        
        # LA LLAVE MAESTRA: io.StringIO
        tablas = pd.read_html(io.StringIO(respuesta.text))
        df = tablas[0]
        tickers = df['Symbol'].astype(str).str.replace('.', '-').tolist()
        return tickers
    except Exception as e:
        print(f"Error S&P500: {e}")
        # Un fallback más grande por si se cae el internet
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'BRK-B', 'JNJ', 'JPM', 'XOM', 'PG', 'CVX']

def obtener_nasdaq100():
    """Descarga la lista del NASDAQ 100 en vivo."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        respuesta = requests.get(url, headers=headers)
        respuesta.raise_for_status()
        
        tablas = pd.read_html(io.StringIO(respuesta.text))
        for tabla in tablas:
            if 'Ticker' in tabla.columns:
                return tabla['Ticker'].astype(str).str.replace('.', '-').tolist()
        return ['QQQ']
    except Exception as e:
        print(f"Error NASDAQ: {e}")
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
# Diccionario inteligente: guarda funciones en lugar de listas estáticas
UNIVERSOS = {
    '🇺🇸 S&P 500 (500 activos en vivo)': obtener_sp500,
    '🤖 NASDAQ 100 (100 activos en vivo)': obtener_nasdaq100,
    '⚡ Prueba Rápida (FAANG)': ['AAPL', 'AMZN', 'GOOGL', 'META', 'NFLX']
}

import time
import random

# ── 2. PROCESAMIENTO EN PARALELO (MODO NINJA) ──
def extraer_datos_ticker(ticker):
    """Función obrera: Extrae los datos con sigilo para evitar bloqueos de IP."""
    try:
        # Pausa aleatoria (0.1 a 0.4 segs) para engañar al firewall de Yahoo
        time.sleep(random.uniform(0.1, 0.4))
        
        info = yf.Ticker(ticker).info
        
        # Si Yahoo nos bloquea silenciosamente, el diccionario viene casi vacío
        if len(info) < 5:
            return None
            
        # Plan B: Si no hay P/E pasado, usamos el P/E futuro estimado
        pe_ratio = info.get('trailingPE', info.get('forwardPE', np.nan))
        
        return {
            'Ticker': ticker,
            'Nombre': info.get('shortName', ticker),
            'Sector': info.get('sector', 'Desconocido'),
            'Market Cap (B)': info.get('marketCap', 0) / 1e9,
            'P/E Ratio': pe_ratio,
            'Profit Margin %': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else np.nan,
            'ROE %': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else np.nan,
            'Beta': info.get('beta', np.nan),
            'Deuda/Capital': info.get('debtToEquity', np.nan),
            'Div Yield %': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0.0
        }
    except Exception:
        return None 

def descargar_fundamentales_paralelo(tickers, max_workers=10): # <-- Bajamos los hilos a 10
    """Motor maestro: Descarga en paralelo pero respetando los límites de la API."""
    resultados = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = [executor.submit(extraer_datos_ticker, t) for t in tickers]
        
        for futuro in concurrent.futures.as_completed(futuros):
            res = futuro.result()
            if res is not None:
                resultados.append(res)
                
    return pd.DataFrame(resultados)

# ── 3. FILTROS Y MACHINE LEARNING ──
def filtrar_candidatos(
    df: pd.DataFrame, min_market_cap: float = 10.0, min_profit_margin: float = 5.0,
    max_pe: float = 50.0, max_deuda: float = 200.0, exigir_dividendos: bool = True
) -> pd.DataFrame:
    
    df_filtrado = df.copy()
    df_filtrado = df_filtrado[df_filtrado['Market Cap (B)']  >= min_market_cap]
    df_filtrado = df_filtrado[df_filtrado['Profit Margin %'] >= min_profit_margin]
    df_filtrado = df_filtrado[
        (df_filtrado['P/E Ratio'].isna()) | (df_filtrado['P/E Ratio'] <= max_pe)
    ]
    df_filtrado = df_filtrado[
        (df_filtrado['Deuda/Capital'].isna()) | (df_filtrado['Deuda/Capital'] <= max_deuda)
    ]

    if exigir_dividendos:
        df_filtrado = df_filtrado[df_filtrado['Div Yield %'] > 0.0]

    return df_filtrado.reset_index(drop=True)

def clustering_activos(df_filtrado: pd.DataFrame, n_clusters: int = 4) -> tuple:
    features = ['Market Cap (B)', 'P/E Ratio', 'Profit Margin %', 'ROE %', 'Beta', 'Deuda/Capital']
    df_clean = df_filtrado[features].copy()
    
    # Seguro matemático contra NaNs absolutos
    df_clean = df_clean.fillna(df_clean.median(numeric_only=True)).fillna(0)

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean)

    # Autocorrección si hay muy pocas empresas que pasaron la guillotina
    n_clusters = min(n_clusters, len(df_clean))
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_filtrado = df_filtrado.copy()
    df_filtrado['Cluster'] = kmeans.fit_predict(X_scaled)

    mejores = (
        df_filtrado
        .sort_values('Profit Margin %', ascending=False)
        .groupby('Cluster')
        .first()
        .reset_index()
    )
    return df_filtrado, mejores
