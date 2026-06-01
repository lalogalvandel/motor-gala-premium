import numpy as np
import pandas as pd
from scipy.linalg import inv

def calcular_black_litterman(retornos_anuales: pd.Series, 
                             matriz_cov: pd.DataFrame, 
                             pesos_mercado: pd.Series, 
                             vistas_usuario: list, 
                             tasa_rf: float, 
                             tau: float = 0.05):
    """
    Motor Black-Litterman para integrar retornos de equilibrio con proyecciones del gestor.
    
    Parámetros:
    - retornos_anuales: pd.Series con los rendimientos históricos medios.
    - matriz_cov: pd.DataFrame con la matriz de covarianza (N x N).
    - pesos_mercado: pd.Series con los pesos de capitalización bursátil de los activos.
    - vistas_usuario: Lista de diccionarios con las proyecciones (Views).
    - tasa_rf: Tasa libre de riesgo (Banxico).
    - tau: Escalar que indica la incertidumbre del CAPM (estándar de la industria: 0.05).
    
    Retorna:
    - retornos_bl: pd.Series con los nuevos rendimientos esperados.
    - cov_bl: pd.DataFrame con la nueva matriz de covarianza ajustada.
    """
    activos = retornos_anuales.index
    N = len(activos)
    
    # Aseguramos que todo sea un array de numpy (álgebra lineal pura)
    Sigma = matriz_cov.values
    W_mkt = pesos_mercado.reindex(activos).fillna(0).values
    
    # ── 1. CALIBRACIÓN DEL MERCADO (Equilibrio) ──
    # Retorno y Varianza del portafolio de mercado implicito
    retorno_mkt = np.dot(W_mkt.T, retornos_anuales.values)
    var_mkt = np.dot(W_mkt.T, np.dot(Sigma, W_mkt))
    
    # Coeficiente de Aversión al Riesgo de Arrow-Pratt (Delta)
    delta = (retorno_mkt - tasa_rf) / var_mkt if var_mkt > 0 else 2.5
    
    # Retornos Implícitos de Equilibrio (Pi)
    Pi = delta * np.dot(Sigma, W_mkt)
    
    # ── 2. PROCESAMIENTO DE VISTAS (Views) ──
    K = len(vistas_usuario)
    
    # Si no hay vistas, el modelo colapsa de forma natural al equilibrio del mercado
    if K == 0:
        return pd.Series(Pi, index=activos), matriz_cov
        
    P = np.zeros((K, N))
    Q = np.zeros(K)
    C = np.zeros(K) # Vector de niveles de confianza
    
    # Mapeo de niveles de confianza a porcentajes (heuristicos)
    mapa_confianza = {"Alta": 0.9, "Media": 0.5, "Baja": 0.1}
    
    for k, vista in enumerate(vistas_usuario):
        tipo = vista.get("tipo", "absoluta") # 'absoluta' o 'relativa'
        activo_1 = vista["activo_1"]
        
        # ── BLINDAJE: Si el activo ya no existe en la matriz, ignoramos la vista ──
        if activo_1 not in activos:
            continue
            
        idx_1 = activos.get_loc(activo_1)
        
        if tipo == "absoluta":
            # "El activo 1 tendrá un retorno X"
            P[k, idx_1] = 1.0
        elif tipo == "relativa":
            # "El activo 1 superará al activo 2 por X"
            activo_2 = vista["activo_2"]
            if activo_2 not in activos:
                continue
            idx_2 = activos.get_loc(activo_2)
            P[k, idx_1] = 1.0
            P[k, idx_2] = -1.0
            
        Q[k] = vista["rendimiento_esperado"]
        C[k] = mapa_confianza.get(vista.get("confianza", "Media"), 0.5)

    # ── 3. MATRIZ DE INCERTIDUMBRE (Omega) ──
    # Usamos el método de varianzas proporcionales ajustadas por confianza
    Omega = np.zeros((K, K))
    for k in range(K):
        # La incertidumbre base es P * (tau * Sigma) * P^T
        incertidumbre_base = np.dot(P[k], np.dot(tau * Sigma, P[k].T))
        # Ajustamos: Mayor confianza -> Menor incertidumbre
        Omega[k, k] = incertidumbre_base / C[k] if C[k] > 0 else incertidumbre_base * 10
        
    # ── 4. ÁLGEBRA DE BLACK-LITTERMAN (Teorema de Bayes) ──
    tau_Sigma = tau * Sigma
    tau_Sigma_inv = inv(tau_Sigma)
    Omega_inv = inv(Omega)
    
    # Término central común: [(tau * Sigma)^-1 + P^T * Omega^-1 * P]^-1
    term_central = inv(tau_Sigma_inv + np.dot(P.T, np.dot(Omega_inv, P)))
    
    # Nuevos Retornos Esperados (E[R])
    term_derecho = np.dot(tau_Sigma_inv, Pi) + np.dot(P.T, np.dot(Omega_inv, Q))
    E_R = np.dot(term_central, term_derecho)
    
    # Nueva Matriz de Covarianza (Sigma_BL)
    Sigma_BL = Sigma + term_central
    
    return pd.Series(E_R, index=activos), pd.DataFrame(Sigma_BL, index=activos, columns=activos)
