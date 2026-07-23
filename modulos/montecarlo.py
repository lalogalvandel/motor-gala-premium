# =============================================================================
# Copyright (c) 2026 Eduardo Galván del Rio. Todos los derechos reservados.
# 
# Este código fuente es propiedad exclusiva y confidencial. Queda estrictamente
# prohibida su reproducción, distribución, comercialización o modificación
# sin autorización expresa y por escrito del autor.
# =============================================================================
import numpy as np
import pandas as pd
from scipy.stats import t

def simular_tasas_cir(r0, tasa_neutral, velocidad_reversion, volatilidad_tasa, meses, num_simulaciones):
    """
    Modelo de Cox-Ingersoll-Ross (CIR) para proyección estocástica de tasas de interés.
    """
    dt = 1 / 12  # Paso mensual
    tasas = np.zeros((meses, num_simulaciones))
    tasas[0] = r0
    
    for t_step in range(1, meses):
        # Ecuación diferencial estocástica CIR
        dr = (velocidad_reversion * (tasa_neutral - tasas[t_step-1]) * dt + 
              volatilidad_tasa * np.sqrt(tasas[t_step-1]) * np.random.normal(0, np.sqrt(dt), num_simulaciones))
        
        # Piso de 0.1% para evitar tasas negativas o colapsos
        tasas[t_step] = np.maximum(tasas[t_step-1] + dr, 0.001)
        
    return tasas

def simular_capital(capital_inicial, aportacion_periodica, rendimiento_anual, volatilidad_anual, 
                    meses, frecuencia_aportacion, tasa_benchmark, num_simulaciones, 
                    retornos_diarios=None, cir_params=None, peso_rf=0.0):
    
    # ── 1. CALIBRACIÓN DE T-STUDENT (Fat Tails) ──
    df_t = 4.0
    if retornos_diarios is not None and len(retornos_diarios) > 30:
        try:
            df_t, _, _ = t.fit(retornos_diarios)
            df_t = max(2.1, min(df_t, 30.0))
        except:
            df_t = 4.0

    # ── 2. INYECCIÓN DEL MODELO CIR ──
    if cir_params and cir_params.get("activo", False):
        tasas_dinamicas = simular_tasas_cir(
            r0=tasa_benchmark,
            tasa_neutral=cir_params["tasa_neutral"],
            velocidad_reversion=cir_params["velocidad"],
            volatilidad_tasa=0.015, # Volatilidad histórica de Banxico (150 bps)
            meses=meses,
            num_simulaciones=num_simulaciones
        )
    else:
        # Si CIR está apagado, proyectamos una línea recta constante
        tasas_dinamicas = np.full((meses, num_simulaciones), tasa_benchmark)

    # ── 3. PREPARACIÓN DE MATRICES ──
    escenarios = np.zeros((meses, num_simulaciones))
    escenarios[0] = capital_inicial
    benchmark_fijo = np.zeros(meses)
    benchmark_fijo[0] = capital_inicial

    vol_mensual = volatilidad_anual / np.sqrt(12)

    # ── 4. SIMULACIÓN ESTOCÁSTICA DE CAPITAL ──
    for m in range(1, meses):
        # El Alpha Dinámico
        delta_tasa = tasas_dinamicas[m-1] - tasa_benchmark
        rendimiento_mensual_ajustado = (rendimiento_anual + (delta_tasa * peso_rf)) / 12
        
        # Generamos los shocks aleatorios
        shocks = t.rvs(df=df_t, loc=0, scale=1, size=num_simulaciones)
        retornos_sim = rendimiento_mensual_ajustado + (vol_mensual * shocks)
        
        # ── 🛡️ EL ESCUDO ANTI-BANCARROTA ──
        # Regla financiera #1: Una cartera no puede perder más del 100% de su valor
        retornos_sim = np.maximum(retornos_sim, -1.0)
        
        # Crecimiento compuesto
        escenarios[m] = escenarios[m-1] * (1 + retornos_sim)
        
        # Regla financiera #2: El saldo en efectivo jamás puede cruzar a cero (no hay margen/deuda)
        escenarios[m] = np.maximum(escenarios[m], 0.0)
        
        # El Benchmark también acumula la tasa CIR dinámica
        tasa_bench_mensual = np.mean(tasas_dinamicas[m-1]) / 12
        benchmark_fijo[m] = benchmark_fijo[m-1] * (1 + tasa_bench_mensual)

        # Inyección de aportaciones
        es_mes_aportacion = False
        if frecuencia_aportacion == "Mensual": es_mes_aportacion = True
        elif frecuencia_aportacion == "Trimestral" and m % 3 == 0: es_mes_aportacion = True
        elif frecuencia_aportacion == "Anual" and m % 12 == 0: es_mes_aportacion = True

        if es_mes_aportacion:
            # Solo sumamos la aportación si la cuenta no está en ceros (Opcional: puedes quitar este if si quieres 
            # simular que sigues aportando incluso después de que la bolsa colapse a cero).
            escenarios[m] += aportacion_periodica
            benchmark_fijo[m] += aportacion_periodica

    # ── 5. CÁLCULO DE PERCENTILES ──
    p5  = np.percentile(escenarios, 5, axis=1)
    p25 = np.percentile(escenarios, 25, axis=1)
    p50 = np.percentile(escenarios, 50, axis=1)
    p75 = np.percentile(escenarios, 75, axis=1)
    p95 = np.percentile(escenarios, 95, axis=1)

    return escenarios, p5, p25, p50, p75, p95, benchmark_fijo, df_t
