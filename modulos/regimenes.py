import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import warnings

# Ocultamos warnings de convergencia para mantener la terminal limpia
warnings.filterwarnings("ignore")

def entrenar_modelo_markov(datos, ticker_ref='SPY'):
    """
    Entrena un Modelo Oculto de Markov para detectar regímenes de mercado.
    """
    # Si el SPY no está, usamos el primer activo como referencia del mercado
    ticker = ticker_ref if ticker_ref in datos.columns else datos.columns[0]
    
    precios = datos[[ticker]].dropna()
    
    # 1. Extraemos las "señales" para el modelo (Retornos y Volatilidad de corto plazo)
    retornos = np.log(precios / precios.shift(1)).dropna()
    volatilidad = retornos.rolling(window=10).std().dropna()
    
    # Alineamos los datos
    df_hmm = pd.DataFrame({'Retornos': retornos[ticker], 'Volatilidad': volatilidad[ticker]}).dropna()
    X = df_hmm.values
    
    # 2. Entrenamos el Modelo Oculto de Markov (2 estados: Calma vs Pánico)
    modelo_hmm = GaussianHMM(n_components=2, covariance_type="full", n_iter=1000, random_state=42)
    modelo_hmm.fit(X)
    
    # 3. Predecimos en qué estado estaba el mercado cada día
    estados_ocultos = modelo_hmm.predict(X)
    
    # 4. Inteligencia: ¿Cuál es el estado de pánico? 
    # El pánico siempre tiene mayor varianza (volatilidad)
    var_estado_0 = np.var(X[estados_ocultos == 0, 0])
    var_estado_1 = np.var(X[estados_ocultos == 1, 0])
    
    estado_panico = 1 if var_estado_1 > var_estado_0 else 0
    
    # Mapeamos a 1 (Pánico) y 0 (Calma) de forma estandarizada
    regimenes_limpios = np.array([1 if estado == estado_panico else 0 for estado in estados_ocultos])
    
    # Reconstruimos el DataFrame con fechas
    df_resultados = pd.DataFrame(index=df_hmm.index)
    df_resultados['Precio'] = precios.loc[df_hmm.index, ticker]
    df_resultados['Regimen'] = regimenes_limpios
    
    return df_resultados