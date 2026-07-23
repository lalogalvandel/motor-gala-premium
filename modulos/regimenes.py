# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import warnings

# Ocultamos warnings de convergencia para mantener la terminal limpia
warnings.filterwarnings("ignore")

def entrenar_modelo_markov(datos, ticker_ref='SPY'):
    """
    Entrena un Modelo Oculto de Markov para detectar regímenes de mercado.
    Incluye blindaje contra valores infinitos o datos insuficientes.
    """
    try:
        # Si el SPY no está, usamos el primer activo como referencia del mercado
        ticker = ticker_ref if ticker_ref in datos.columns else datos.columns[0]
        precios = datos[[ticker]].dropna()
        
        # Si hay muy pocos datos, abortamos el cálculo complejo
        if len(precios) < 20:
            raise ValueError("Datos insuficientes para converger el modelo de Markov.")

        # 1. Cálculos limpios (reemplazando Infinitos por NaNs para que dropna() los elimine)
        retornos = np.log(precios / precios.shift(1))
        retornos = retornos.replace([np.inf, -np.inf], np.nan).dropna()
        
        volatilidad = retornos.rolling(window=10).std()
        volatilidad = volatilidad.replace([np.inf, -np.inf], np.nan).dropna()
        
        # Alineamos los datos
        df_hmm = pd.DataFrame({'Retornos': retornos[ticker], 'Volatilidad': volatilidad[ticker]}).dropna()
        X = df_hmm.values
        
        # Verificación de seguridad de sklearn
        if len(X) < 10:
            raise ValueError("Matriz X demasiado pequeña tras la limpieza de Infinitos.")

        # 2. Entrenamos el Modelo Oculto de Markov
        modelo_hmm = GaussianHMM(n_components=2, covariance_type="full", n_iter=1000, random_state=42)
        modelo_hmm.fit(X)
        
        # 3. Predecimos en qué estado estaba el mercado cada día
        estados_ocultos = modelo_hmm.predict(X)
        
        # 4. Inteligencia: El pánico siempre tiene mayor varianza
        var_estado_0 = np.var(X[estados_ocultos == 0, 0]) if len(X[estados_ocultos == 0, 0]) > 0 else 0
        var_estado_1 = np.var(X[estados_ocultos == 1, 0]) if len(X[estados_ocultos == 1, 0]) > 0 else 0
        
        estado_panico = 1 if var_estado_1 > var_estado_0 else 0
        
        regimenes_limpios = np.array([1 if estado == estado_panico else 0 for estado in estados_ocultos])
        
        df_resultados = pd.DataFrame(index=df_hmm.index)
        df_resultados['Precio'] = precios.loc[df_hmm.index, ticker]
        df_resultados['Regimen'] = regimenes_limpios
        
        return df_resultados

    except Exception as e:
        print(f"🚨 HMM Evadido: {e}. Activando protocolo de régimen neutral.")
        # FALLBACK INSTITUCIONAL: Si el modelo matemático choca, 
        # devolvemos un régimen de calma (0) para que la app principal siga operando.
        ticker_fallback = ticker_ref if ticker_ref in datos.columns else datos.columns[0]
        precios_fallback = datos[[ticker_fallback]].dropna()
        
        df_resultados = pd.DataFrame(index=precios_fallback.index)
        df_resultados['Precio'] = precios_fallback[ticker_fallback]
        df_resultados['Regimen'] = 0  
        return df_resultados
