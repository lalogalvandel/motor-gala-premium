# modulos/pensiones.py
import numpy as np

class MotorActuarial:
    @staticmethod
    def estimar_pension_ley73(semanas_cotizadas, salario_promedio, edad_retiro, uma_actual, tiene_pareja=False):
        """Calcula la pensión IMSS bajo régimen 73, devolviendo el monto mensual."""
        salario_uma = salario_promedio / uma_actual
        porcentaje_edad = {60: 0.75, 61: 0.80, 62: 0.85, 63: 0.90, 64: 0.95, 65: 1.0}
        factor_edad = porcentaje_edad.get(edad_retiro, 1.0)
        
        # Asignación de Cuantía Básica (Aproximación por tramos de Ley)
        if salario_uma > 6.0:
            cuantia_basica_pct = 0.13
        else:
            cuantia_basica_pct = 0.13 + (6.0 - salario_uma) * 0.05 
            
        cuantia_basica = salario_promedio * cuantia_basica_pct * 365
        semanas_extra = max(0, semanas_cotizadas - 500)
        anios_extra = semanas_extra / 52.0
        incrementos = salario_promedio * 0.0245 * 365 * anios_extra
        
        # Asignación familiar (15% solo si tiene cónyuge/concubina o aplica ayuda asistencial)
        factor_familiar = 1.15 if tiene_pareja else 1.0 
        pension_anual = (cuantia_basica + incrementos) * factor_edad * factor_familiar
        
        # Tope de ley: 25 UMAs
        tope_mensual = 25 * uma_actual * 30.4
        return min(pension_anual / 12, tope_mensual)

    @staticmethod
    def proyeccion_ppr_real(capital_inicial, aportacion_mensual, anios_horizonte, tasa_nominal_anual, inflacion_anual):
        """
        Proyecta el capital acumulado en un PPR (Contribución Definida) 
        expresado en PODER ADQUISITIVO ACTUAL (Pesos de Hoy) usando la Ecuación de Fisher.
        """
        # Ecuación de Fisher para Tasa Real
        tasa_real_anual = ((1 + tasa_nominal_anual) / (1 + inflacion_anual)) - 1
        tasa_real_mensual = tasa_real_anual / 12
        meses = anios_horizonte * 12
        
        # Valor Futuro de una anualidad con tasa real
        if tasa_real_mensual == 0:
            capital_futuro_real = capital_inicial + (aportacion_mensual * meses)
        else:
            vf_inicial = capital_inicial * (1 + tasa_real_mensual)**meses
            vf_aportaciones = aportacion_mensual * (((1 + tasa_real_mensual)**meses - 1) / tasa_real_mensual)
            capital_futuro_real = vf_inicial + vf_aportaciones
            
        return capital_futuro_real

    @staticmethod
    def calcular_brecha_pensional_real(meta_mensual_hoy, pension_mensual_real, capital_acumulado_real, tasa_retiro_segura):
        """
        Calcula si el capital real acumulado y la pensión cubren la meta de vida.
        Todos los inputs deben estar en poder adquisitivo actual (reales).
        """
        flujo_privado_mensual = (capital_acumulado_real * tasa_retiro_segura) / 12
        ingreso_total = pension_mensual_real + flujo_privado_mensual
        brecha = meta_mensual_hoy - ingreso_total
        return ingreso_total, brecha, flujo_privado_mensual
