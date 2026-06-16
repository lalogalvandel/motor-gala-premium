import numpy as np
import pandas as pd
from scipy.linalg import inv
from scipy.linalg import pinv  # Importamos la pseudoinversa

def calcular_black_litterman(
    retornos_anuales: pd.Series,
    matriz_cov: pd.DataFrame,
    pesos_mercado: pd.Series,
    vistas_usuario: list,
    tasa_rf: float,
    tau: float = 0.05
):
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
    # BLINDAJE 1: Filtrar vistas inválidas ANTES de dimensionar las matrices
    vistas_validas = []
    for vista in vistas_usuario:
        activo_1 = vista.get("activo_1")
        if activo_1 not in activos:
            continue
        if vista.get("tipo") == "relativa" and vista.get("activo_2") not in activos:
            continue
        vistas_validas.append(vista)
        
    K = len(vistas_validas)
    
    # Si no quedan vistas válidas, el modelo colapsa de forma natural al equilibrio
    if K == 0:
        return pd.Series(Pi, index=activos), matriz_cov
        
    P = np.zeros((K, N))
    Q = np.zeros(K)
    C = np.zeros(K) # Vector de niveles de confianza
    
    mapa_confianza = {"Baja": 0.1, "Media": 0.5, "Alta": 0.9}
    
    for k, vista in enumerate(vistas_validas):
        tipo = vista.get("tipo", "absoluta")
        idx_1 = activos.get_loc(vista["activo_1"])
        
        if tipo == "absoluta":
            # "El activo 1 tendrá un retorno X"
            P[k, idx_1] = 1.0
        elif tipo == "relativa":
            # "El activo 1 superará al activo 2 por X"
            idx_2 = activos.get_loc(vista["activo_2"])
            P[k, idx_1] = 1.0
            P[k, idx_2] = -1.0
            
        Q[k] = vista["rendimiento_esperado"]
        C[k] = mapa_confianza.get(vista.get("confianza", "Media"), 0.5)

    # ── 3. MATRIZ DE INCERTIDUMBRE (Omega) ──
    Omega = np.zeros((K, K))
    for k in range(K):
        incertidumbre_base = np.dot(P[k], np.dot(tau * Sigma, P[k].T))
        
        # BLINDAJE 2: Prevención de Matrices Singulares (Épsilon)
        # Si un activo tiene volatilidad CERO (ej. CASH) o datos planos,
        # forzamos un valor minúsculo (1e-6) para permitir la inversión de la matriz
        # sin alterar matemáticamente el resultado final del portafolio.
        if incertidumbre_base <= 1e-8:
            incertidumbre_base = 1e-6
            
        Omega[k, k] = (incertidumbre_base / C[k]) if C[k] > 0 else (incertidumbre_base * 10)
        
    # ── 4. ÁLGEBRA DE BLACK-LITTERMAN (Teorema de Bayes) ──
    tau_Sigma = tau * Sigma
    
    # Limpieza de datos (agrégalo antes de calcular tau_Sigma)
    tau_Sigma = np.nan_to_num(tau_Sigma, nan=0.0, posinf=0.0, neginf=0.0)
    
    # 1. Regularización: Añadimos una cantidad minúscula a la diagonal 
    # para asegurar que sea positiva definida (Tikhonov regularization)
    tau_Sigma += np.eye(tau_Sigma.shape[0]) * 1e-6
    
    # 2. Inversión Robusta: Usamos pinv (pseudoinversa) en lugar de inv
    # Esto evita el ValueError incluso si hay activos altamente correlacionados
    try:
        tau_Sigma_inv = pinv(tau_Sigma)
    except Exception as e:
        # Si todo falla, forzamos una matriz identidad para no detener la app
        tau_Sigma_inv = np.eye(tau_Sigma.shape[0])
    # ── BLINDAJE PARA LA MATRIZ OMEGA ──
    # 1. Limpiamos cualquier NaN o Inf que haya escupido el cálculo previo
    Omega = np.nan_to_num(Omega, nan=0.0, posinf=0.0, neginf=0.0)
    
    # 2. Regularización de Tikhonov: inyectamos un micro-ruido en la diagonal para evitar ceros absolutos
    Omega += np.eye(Omega.shape[0]) * 1e-6
    
    # 3. Inversión robusta
    try:
        from scipy.linalg import pinv
        Omega_inv = pinv(Omega)
    except Exception:
        Omega_inv = np.eye(Omega.shape[0])
    
    # Término central común: [(tau * Sigma)^-1 + P^T * Omega^-1 * P]^-1
    term_central = inv(tau_Sigma_inv + np.dot(P.T, np.dot(Omega_inv, P)))
    
    # Nuevos Retornos Esperados (E[R])
    term_derecho = np.dot(tau_Sigma_inv, Pi) + np.dot(P.T, np.dot(Omega_inv, Q))
    E_R = np.dot(term_central, term_derecho)
    
    # Nueva Matriz de Covarianza (Sigma_BL)
    Sigma_BL = Sigma + term_central
    
    return pd.Series(E_R, index=activos), pd.DataFrame(Sigma_BL, index=activos, columns=activos)
