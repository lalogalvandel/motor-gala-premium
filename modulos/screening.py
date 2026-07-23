# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import concurrent.futures
import warnings
import requests 
import io
import time
import random

warnings.filterwarnings("ignore")

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
    'S&P 500 (500 activos en vivo)': obtener_sp500,
    'NASDAQ 100 (100 activos en vivo)': obtener_nasdaq100,
    'Prueba Rápida (FAANG)': ['AAPL', 'AMZN', 'GOOGL', 'META', 'NFLX']
}

# ── 2. PROCESAMIENTO EN PARALELO (MODO INSTITUCIONAL) ──
def extraer_datos_ticker(ticker):
    """Función obrera: Extrae los datos con sigilo y métricas avanzadas (Value/Growth)."""
    try:
        # Pausa aleatoria (0.1 a 0.4 segs) para engañar al firewall de Yahoo
        time.sleep(random.uniform(0.1, 0.4))
        
        info = yf.Ticker(ticker).info
        
        # Si Yahoo nos bloquea silenciosamente, el diccionario viene casi vacío
        if len(info) < 5:
            return None
            
        # Cálculo manual de métricas clave si están disponibles
        market_cap = info.get('marketCap', 0)
        fcf = info.get('freeCashflow', 0)
        fcf_yield = (fcf / market_cap * 100) if market_cap > 0 and fcf else np.nan
        
        return {
            'Ticker': ticker,
            'Nombre': info.get('shortName', ticker),
            'Sector': info.get('sector', 'Desconocido'),
            'Market Cap (B)': market_cap / 1e9,
            
            # --- VALORACIÓN ---
            'P/E Ratio': info.get('trailingPE', info.get('forwardPE', np.nan)),
            'EV/EBITDA': info.get('enterpriseToEbitda', np.nan),
            'PEG Ratio': info.get('pegRatio', np.nan),
            'FCF Yield %': fcf_yield,
            
            # --- CALIDAD ---
            'Profit Margin %': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else np.nan,
            'ROE %': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else np.nan,
            'ROIC %': info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else np.nan, # Proxy de ROA a ROIC
            
            # --- SALUD FINANCIERA ---
            'Current Ratio': info.get('currentRatio', np.nan),
            'Deuda/Capital': info.get('debtToEquity', np.nan),
            
            # --- CRECIMIENTO & MERCADO ---
            'Revenue Growth %': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else np.nan,
            'Beta': info.get('beta', np.nan),
            'Div Yield %': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0.0
        }
    except Exception:
        return None 

def descargar_fundamentales_paralelo(tickers, max_workers=10):
    """Motor maestro: Descarga en paralelo respetando los límites de la API."""
    resultados = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = [executor.submit(extraer_datos_ticker, t) for t in tickers]
        
        for futuro in concurrent.futures.as_completed(futuros):
            res = futuro.result()
            if res is not None:
                resultados.append(res)
                
    return pd.DataFrame(resultados)

# ── 3. FILTROS POR TESIS Y MACHINE LEARNING ──
def filtrar_candidatos(
    df: pd.DataFrame, 
    estilo: str = "GARP", 
    min_market_cap: float = 10.0, 
    min_profit_margin: float = 5.0, 
    max_deuda: float = 200.0
) -> pd.DataFrame:
    """Aplica la guillotina heurística dependiendo si el gestor es Value, Growth o GARP."""
    
    df_filtrado = df.copy()
    
    # 1. Guillotina Base (Salud financiera mínima innegociable)
    df_filtrado = df_filtrado[df_filtrado['Market Cap (B)'] >= min_market_cap]
    df_filtrado = df_filtrado[
        (df_filtrado['Deuda/Capital'].isna()) | (df_filtrado['Deuda/Capital'] <= max_deuda)
    ]
    
    # 2. Filtros Dinámicos de Tesis de Inversión
    if "Value" in estilo:
        # Perfil Cazador de Gangas (Alta generación de caja y baratos)
        df_filtrado = df_filtrado[df_filtrado['FCF Yield %'] > 3.0] 
        df_filtrado = df_filtrado[
            (df_filtrado['EV/EBITDA'].isna()) | (df_filtrado['EV/EBITDA'] < 15.0)
        ] 
        df_filtrado = df_filtrado[df_filtrado['Profit Margin %'] >= min_profit_margin]
        df_filtrado = df_filtrado[df_filtrado['ROE %'] >= 10.0]
        
    elif "Growth" in estilo:
        # Perfil Hipercrecimiento (Escalabilidad por encima de rentabilidad inmediata)
        df_filtrado = df_filtrado[df_filtrado['Revenue Growth %'] > 12.0]
        df_filtrado = df_filtrado[
            (df_filtrado['ROE %'] > 15.0) | (df_filtrado['Profit Margin %'] >= min_profit_margin)
        ]
        
    else: 
        # Perfil GARP (Growth At a Reasonable Price - Crecimiento a precio razonable)
        df_filtrado = df_filtrado[df_filtrado['Profit Margin %'] >= min_profit_margin]
        df_filtrado = df_filtrado[df_filtrado['ROE %'] >= 15.0]
        df_filtrado = df_filtrado[
            (df_filtrado['PEG Ratio'].isna()) | ((df_filtrado['PEG Ratio'] > 0) & (df_filtrado['PEG Ratio'] <= 2.5))
        ]

    # Limpieza matemática final
    df_filtrado = df_filtrado.replace([np.inf, -np.inf], np.nan).dropna(subset=['Ticker'])
    
    return df_filtrado.reset_index(drop=True)

def clustering_activos(df_filtrado: pd.DataFrame, n_clusters: int = 4) -> tuple:
    """Agrupa activos similares usando IA para garantizar diversificación real."""
    
    # Usamos las nuevas features institucionales
    features = [
        'EV/EBITDA', 'PEG Ratio', 'FCF Yield %', 
        'ROE %', 'Revenue Growth %', 'Current Ratio'
    ]
    
    df_clean = df_filtrado[features].copy()
    
    # Rellenamos NaNs con la mediana sectorial/global para no perder data valiosa
    for col in features:
        df_clean[col] = df_clean[col].fillna(df_clean[col].median())
    df_clean = df_clean.fillna(0) # Seguro anti-fallos

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean)

    # Seguro si la guillotina cortó demasiadas empresas
    n_clusters = min(n_clusters, len(df_clean))
    
    # Si por algún motivo nos quedamos con 1 o 0 empresas, devolvemos sin aplicar KMeans
    if n_clusters < 2:
        df_filtrado = df_filtrado.copy()
        df_filtrado['Cluster'] = 0
        return df_filtrado, df_filtrado
        
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df_filtrado = df_filtrado.copy()
    df_filtrado['Cluster'] = kmeans.fit_predict(X_scaled)

    # Ordenamos a los campeones de cada cluster por Flujo de Caja Libre en lugar de solo Margen
    mejores = (
        df_filtrado
        .sort_values('FCF Yield %', ascending=False)
        .groupby('Cluster')
        .first()
        .reset_index()
    )
    
    return df_filtrado, mejores
