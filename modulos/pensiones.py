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
    def proyeccion_ppr_real(capital_inicial: float, aportacion_mensual: float, anios: int, 
                            tasa_anual: float, inflacion: float, 
                            ingreso_mensual: float = 0.0, aplicar_beneficio_fiscal: bool = False,
                            uma_actual: float = 108.57) -> float:
        """
        Proyecta el capital acumulado en términos reales (descontando inflación).
        Incluye el módulo de Alpha Fiscal (Art. 151 LISR): Calcula la devolución anual del SAT
        y la reinvierte en el portafolio cada mes de abril.
        """
        # Tasa real mensual usando la ecuación de Fisher
        tasa_real_anual = ((1 + tasa_anual) / (1 + inflacion)) - 1
        tasa_real_mensual = (1 + tasa_real_anual) ** (1/12) - 1
        
        capital = capital_inicial
        meses = anios * 12
        
        # ── CÁLCULO DEL BENEFICIO FISCAL (Art. 151) ──
        devolucion_anual = 0.0
        if aplicar_beneficio_fiscal and ingreso_mensual > 0:
            ingreso_anual = ingreso_mensual * 12
            aportacion_anual = aportacion_mensual * 12
            
            # Limite 1: 10% del ingreso anual
            limite_10_pct = ingreso_anual * 0.10
            # Limite 2: 5 UMAs anualizadas (UMA diaria * 365 * 5)
            limite_5_umas = uma_actual * 365 * 5
            
            # El monto máximo que el SAT permite deducir
            monto_deducible = min(aportacion_anual, limite_10_pct, limite_5_umas)
            
            # Estimación del bracket de ISR (simplificación dinámica)
            if ingreso_mensual > 100000: tasa_isr = 0.34
            elif ingreso_mensual > 50000: tasa_isr = 0.30
            elif ingreso_mensual > 25000: tasa_isr = 0.23
            else: tasa_isr = 0.15
                
            devolucion_anual = monto_deducible * tasa_isr

        # ── MOTOR ESTOCÁSTICO DE INTERÉS COMPUESTO ──
        for mes in range(1, meses + 1):
            capital = capital * (1 + tasa_real_mensual) + aportacion_mensual
            
            # Efecto Abril: Reinversión de la devolución de impuestos del SAT cada 12 meses
            if aplicar_beneficio_fiscal and mes % 12 == 4:
                capital += devolucion_anual
                
        return capital

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
