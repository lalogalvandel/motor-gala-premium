# modulos/pensiones.py
import numpy as np

def estimar_pension_ley73(semanas_cotizadas, salario_promedio_5_anios, edad_retiro):
    """
    Estimación simplificada de Pensión IMSS Ley 73.
    """
    # 1. Penalización por edad (de 60 a 65 años)
    porcentaje_edad = {60: 0.75, 61: 0.80, 62: 0.85, 63: 0.90, 64: 0.95, 65: 1.0}
    factor_edad = porcentaje_edad.get(edad_retiro, 1.0)
    
    # 2. Factor de actualización y cuantías (Simplificado para el MVP)
    # UMA 2026 (Proyectada aprox 114 MXN)
    uma_actual = 114.0 
    salario_uma = salario_promedio_5_anios / uma_actual
    
    # Si el salario promedio es muy alto (topado), la cuantía básica es aprox 13% y el incremento anual 2.45%
    if salario_uma > 6.0:
        cuantia_basica_pct = 0.13
        incremento_anual_pct = 0.0245
    else:
        # Para salarios bajos el porcentaje de cuantía básica es mayor (hasta 80%)
        cuantia_basica_pct = 0.13 + (6.0 - salario_uma) * 0.05 
        incremento_anual_pct = 0.0245
        
    cuantia_basica = salario_promedio_5_anios * cuantia_basica_pct * 365
    
    # 3. Incrementos por semanas extra (después de las primeras 500)
    semanas_extra = max(0, semanas_cotizadas - 500)
    anios_extra = semanas_extra / 52.0
    incrementos = salario_promedio_5_anios * incremento_anual_pct * 365 * anios_extra
    
    # 4. Cálculo final anual y mensual
    pension_anual = (cuantia_basica + incrementos) * factor_edad
    
    # Se añade asignación familiar (15% por esposa o soledad)
    pension_anual *= 1.15
    
    # Tope legal de 25 UMAs
    tope_mensual = 25 * uma_actual * 30.4
    
    pension_mensual = min(pension_anual / 12, tope_mensual)
    
    return pension_mensual

def calcular_brecha_pensional(meta_mensual, pension_imss, capital_acumulado, tasa_retiro_segura=0.04):
    """
    Calcula si el portafolio privado cubre el faltante del IMSS usando la regla del 4%.
    """
    flujo_portafolio = (capital_acumulado * tasa_retiro_segura) / 12
    ingreso_total = pension_imss + flujo_portafolio
    brecha = meta_mensual - ingreso_total
    
    return ingreso_total, brecha, flujo_portafolio
