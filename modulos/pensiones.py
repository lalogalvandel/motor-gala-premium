# modulos/pensiones.py
import numpy as np

def estimar_pension_ley73(semanas_cotizadas, salario_promedio, edad_retiro, uma_actual):
    salario_uma = salario_promedio / uma_actual
    porcentaje_edad = {60: 0.75, 61: 0.80, 62: 0.85, 63: 0.90, 64: 0.95, 65: 1.0}
    factor_edad = porcentaje_edad.get(edad_retiro, 1.0)
    
    if salario_uma > 6.0:
        cuantia_basica_pct = 0.13
    else:
        cuantia_basica_pct = 0.13 + (6.0 - salario_uma) * 0.05 
        
    cuantia_basica = salario_promedio * cuantia_basica_pct * 365
    semanas_extra = max(0, semanas_cotizadas - 500)
    anios_extra = semanas_extra / 52.0
    incrementos = salario_promedio * 0.0245 * 365 * anios_extra
    
    pension_anual = (cuantia_basica + incrementos) * factor_edad * 1.15 # 1.15 por asignación familiar
    tope_mensual = 25 * uma_actual * 30.4
    
    return min(pension_anual / 12, tope_mensual)

def calcular_brecha_pensional(meta_mensual, pension_imss, capital_acumulado, tasa_retiro):
    flujo_privado = (capital_acumulado * tasa_retiro) / 12
    ingreso_total = pension_imss + flujo_privado
    brecha = meta_mensual - ingreso_total
    return ingreso_total, brecha, flujo_privado
