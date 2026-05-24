from fpdf import FPDF
from datetime import datetime

def generar_pdf_inmunizacion(empresa, val_activos, val_pasivos, ratio, dur_lograda, yield_opt, conv_lograda, nombres_inst, pesos_inst, shock):
    pdf = FPDF()
    pdf.add_page()
    
    # Colores corporativos (RGB)
    azul_gala = (68, 136, 255)
    gris_texto = (90, 103, 128)
    
    # ── ENCABEZADO ──
    pdf.set_font('Arial', 'B', 16)
    pdf.set_text_color(*azul_gala)
    pdf.cell(0, 10, 'MOTOR GALA - QUANT SOLUTIONS', ln=True, align='L')
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(*gris_texto)
    pdf.cell(0, 6, f'Reporte de Auditoria ALM y Reestructuracion de Cartera', ln=True, align='L')
    pdf.cell(0, 6, f'Fecha de emision: {datetime.now().strftime("%Y-%m-%d %H:%M")}', ln=True, align='L')
    pdf.line(10, 35, 200, 35)
    pdf.ln(10)
    
    # ── DATOS DE LA INSTITUCIÓN ──
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f'Institucion: {empresa}', ln=True)
    
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 6, f'Valor Total Activos: ${val_activos:,.2f} M', ln=True)
    pdf.cell(0, 6, f'Valor Total Pasivos: ${val_pasivos:,.2f} M', ln=True)
    pdf.cell(0, 6, f'Ratio de Cobertura Inicial: {ratio*100:.1f}%', ln=True)
    
    if shock != 0:
        pdf.set_text_color(255, 75, 75)
        pdf.cell(0, 6, f'Escenario de Estres Aplicado: Shock de {shock} bps en la curva de tasas', ln=True)
        pdf.set_text_color(0, 0, 0)
        
    pdf.ln(5)
    
    # ── RESULTADOS DE OPTIMIZACIÓN ──
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*azul_gala)
    pdf.cell(0, 8, 'Resultados del Optimizador SLSQP (Inmunizacion Estocastica)', ln=True)
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, f'Calce de Duracion Logrado: {dur_lograda:.2f} anos', ln=True)
    pdf.cell(0, 6, f'Cobertura de Convexidad Lograda: {conv_lograda:.2f}', ln=True)
    pdf.cell(0, 6, f'Yield de Cartera Optimizado: {yield_opt*100:.2f}%', ln=True)
    pdf.ln(5)
    
    # ── NUEVA ESTRUCTURA (PESOS) ──
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, 'Instruccion de Rebalanceo (Nueva Estructura de Inversion):', ln=True)
    
    pdf.set_font('Arial', '', 10)
    for nombre, peso in zip(nombres_inst, pesos_inst):
        if peso > 0.01:
            pdf.cell(0, 6, f'- {nombre}: {peso*100:.1f}%', ln=True)
            
    # ── FOOTER REGULATORIO ──
    pdf.ln(15)
    pdf.set_font('Arial', 'I', 8)
    pdf.set_text_color(*gris_texto)
    pdf.multi_cell(0, 4, "Aviso Legal: Este documento es generado por el motor cuantitativo GaLa Institutional Solutions. Las recomendaciones de rebalanceo estan calculadas mediante metodos numericos de optimizacion restringida (SLSQP) para cumplir con requerimientos de Solvencia II. La ejecucion en mercado queda a discrecion de la mesa de dinero de la institucion.")
    
    # Retornar el PDF en formato de bytes para que Streamlit lo pueda descargar
    return pdf.output(dest='S').encode('latin-1')
