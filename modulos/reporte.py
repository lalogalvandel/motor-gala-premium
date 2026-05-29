import io
import numpy as np
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak, Image, KeepTogether, CondPageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# ── Paleta institucional ───────────────────────────────────────────────────────
AZUL_OSCURO  = colors.HexColor('#0a0f2e')
AZUL_MEDIO   = colors.HexColor('#1a2560')
AZUL_ACENTO  = colors.HexColor('#4488ff')
GRIS_CLARO   = colors.HexColor('#e8ecf0')
GRIS_TEXTO   = colors.HexColor('#4a5568')
BLANCO       = colors.white
ROJO         = colors.HexColor('#e53e3e')
VERDE        = colors.HexColor('#38a169')

# Ancho útil de la página
PAGE_W = 6.5 * inch

def _estilos():
    return {
        'titulo': ParagraphStyle('titulo', fontSize=26, textColor=BLANCO, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=8),
        'subtitulo': ParagraphStyle('subtitulo', fontSize=11, textColor=AZUL_ACENTO, fontName='Helvetica', alignment=TA_CENTER, spaceAfter=4),
        'seccion': ParagraphStyle('seccion', fontSize=13, textColor=AZUL_OSCURO, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6),
        'subseccion': ParagraphStyle('subseccion', fontSize=10, textColor=AZUL_MEDIO, fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=4),
        'normal': ParagraphStyle('normal', fontSize=9, textColor=GRIS_TEXTO, fontName='Helvetica', spaceAfter=4, leading=14),
        'justificado': ParagraphStyle('justificado', fontSize=9, textColor=GRIS_TEXTO, fontName='Helvetica', spaceAfter=4, leading=14, alignment=TA_JUSTIFY),
        'pie': ParagraphStyle('pie', fontSize=7, textColor=GRIS_TEXTO, fontName='Helvetica', alignment=TA_CENTER),
        'tecnico_titulo': ParagraphStyle('tecnico_titulo', fontSize=9, textColor=AZUL_MEDIO, fontName='Helvetica-Bold', spaceAfter=4),
        'tecnico_cuerpo': ParagraphStyle('tecnico_cuerpo', fontSize=8, textColor=AZUL_OSCURO, fontName='Helvetica', leading=12, alignment=TA_JUSTIFY),
        'formula': ParagraphStyle('formula', fontSize=8, textColor=colors.HexColor('#2c5282'), fontName='Courier-Bold', alignment=TA_CENTER, spaceBefore=4, spaceAfter=4),
    }

def _fig_a_imagen(fig, width=800, height=400, scale=2, h_inch=None):
    fig.update_layout(margin=dict(l=110, r=40, t=40, b=60))
    img_bytes = fig.to_image(format="png", width=width*1.5, height=height*1.5, scale=scale)
    ancho_fisico = 6.5 * inch
    alto_fisico = h_inch * inch if h_inch else (height / width) * ancho_fisico
    return Image(io.BytesIO(img_bytes), width=ancho_fisico, height=alto_fisico)

def _tabla_estilo(data, col_widths, header_color=AZUL_OSCURO):
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return t

def _seccion(titulo, estilo):
    return [Paragraph(titulo, estilo), HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10)]

def _callout_tecnico(titulo, texto, formula=None):
    """Crea una tarjeta elegante para explicaciones metodológicas (Caja Blanca)"""
    E = _estilos()
    elementos = [Paragraph(f"METODOLOGÍA: {titulo}", E['tecnico_titulo']), Paragraph(texto, E['tecnico_cuerpo'])]
    if formula:
        elementos.append(Paragraph(formula, E['formula']))
    
    t = Table([[elementos]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f4f8')), # Fondo azul ultraclaro
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('LINEBEFORE', (0,0), (0,-1), 3, AZUL_ACENTO), # Borde acento a la izquierda
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    return [Spacer(1, 0.1*inch), t, Spacer(1, 0.1*inch)]

def _on_page(canvas, doc):
    w, h = letter
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, h, fill=True, stroke=False)
    else:
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, h - 40, w, 40, fill=True, stroke=False)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(BLANCO)
        canvas.drawString(30, h - 25, "MOTOR CUANTITATIVO GaLa")
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(w - 30, h - 25, f"Página {doc.page}")
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, 25, fill=True, stroke=False)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#8899bb'))
        canvas.drawString(30, 8, "Documento analítico — Confidencial")
        canvas.drawRightString(w - 30, 8, datetime.now().strftime("%d/%m/%Y %H:%M"))
    canvas.restoreState()

# ─────────────────────────────────────────────────────────────────────────────
def generar_reporte(
    tickers, pesos_opt, ret_opt, vol_opt, sharpe_opt, sortino, desv_down, df_t,
    var_cvar, max_dd, duracion_dd, inicio_dd, fin_dd, df_stress, capital_riesgo,
    p5_final, p25_final, p50_final, p75_final, p95_final,
    horizonte_años, capital_inicial, aportacion_mensual, num_sims,
    metricas_bt, benchmark_ticker, df_screening=None,
    fig_markowitz=None, fig_mc=None, fig_var=None, fig_dd=None, fig_stress=None, fig_bt=None, fig_anuales=None, fig_corr=None,
    # Parámetros Opcionales LDI
    limite_riesgo_global=None, perfil_estrategico=None, pension_imss=None, brecha_pensional=None, semanas_cotizadas=None, salario_promedio=None
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.5*inch)
    E = _estilos()
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 1 — PORTADA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph("MOTOR CUANTITATIVO GaLa", E['titulo']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Reporte Institucional y Metodología White-Box", E['subtitulo']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(datetime.now().strftime("%d de %B de %Y"), E['subtitulo']))
    story.append(Spacer(1, 0.8 * inch))

    story.append(Paragraph(
        f"Este reporte detalla la arquitectura algorítmica detrás de la estructuración del portafolio, "
        f"evitando los modelos convencionales de 'Caja Negra'. El universo de inversión ({len(tickers)} activos) ha sido procesado "
        f"mediante un motor estocástico calibrado con variables macroeconómicas reales y distribuciones asimétricas.",
        ParagraphStyle('resumen', fontSize=10, textColor=GRIS_CLARO, fontName='Helvetica', alignment=TA_CENTER, leading=16, leftIndent=40, rightIndent=40)
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # NUEVA PÁGINA (OPCIONAL) — MODELADO LDI (LEY 73)
    # ══════════════════════════════════════════════════════════════════════════
    if pension_imss is not None:
        story.append(Spacer(1, 0.3 * inch))
        story += _seccion("Modelado Actuarial LDI y Pensión IMSS (Ley 73)", E['seccion'])
        
        story.append(Paragraph("1. Calibración de Pasivos", E['subseccion']))
        ldi_data = [
            ['Semanas Cotizadas', f"{semanas_cotizadas:,}"],
            ['Salario Base de Cotización', f"${salario_promedio:,.2f} MXN/día"],
            ['Pensión Vitalicia Estimada (IMSS)', f"${pension_imss:,.2f} MXN/mes"],
        ]
        if brecha_pensional is not None:
            estado = "Déficit Estructural" if brecha_pensional > 0 else "Superávit y Preservación"
            ldi_data.append(['Diagnóstico LDI', estado])
            
        story.append(_tabla_estilo(ldi_data, [3*inch, 3.5*inch]))
        
        story += _callout_tecnico(
            titulo="Algoritmo de Pensión (IMSS Ley 73)",
            texto="La pensión gubernamental se estima aplicando el marco normativo de la Ley del Seguro Social de 1973. "
                  "La función algorítmica calcula la relación entre el salario promedio y la UMA vigente para extraer el porcentaje "
                  "de la 'Cuantía Básica' (tope legal del 13%). Posteriormente, se suma el factor de 'Incrementos Anuales' equivalente "
                  "al 2.45% por cada bloque de 52 semanas que exceda el requisito mínimo de 500 semanas, agregando una prima por asignación familiar del 15%."
        )

        story.append(Paragraph("2. Prescripción Algorítmica de Riesgo", E['subseccion']))
        riesgo_asignado = limite_riesgo_global * 100 if limite_riesgo_global else 80.0
        story.append(Paragraph(
            f"El Motor GaLa determinó matemáticamente un perfil <b>{perfil_estrategico or 'Optimizado'}</b>. "
            f"Basado en el nivel de certidumbre del flujo libre proyectado, el presupuesto de riesgo máximo (límite de "
            f"exposición a Renta Variable o *Drawdown* de alta severidad) se bloqueó algorítmicamente en el <b>{riesgo_asignado:.1f}%</b>.",
            E['normal']
        ))
        
        story += _callout_tecnico(
            titulo="Inversión Basada en Pasivos (LDI)",
            texto="El modelo LDI (Liability-Driven Investing) abandona el enfoque clásico de 'maximizar retornos' a ciegas. "
                  "En su lugar, el algoritmo analiza el pasivo futuro del individuo (sus gastos menos su pensión garantizada). "
                  "Si existe un superávit, el optimizador restringe severamente la volatilidad forzando la compra de activos de refugio "
                  "(como Mbonos o UDIBONOS). Si hay déficit, amplía la frontera eficiente permitiendo exposición controlada a renta variable."
        )
        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — PORTAFOLIO ÓPTIMO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Arquitectura del Portafolio Óptimo", E['seccion'])

    # Métricas principales (Mismo código de tu versión)
    metricas_data = [['Retorno Anual', 'Volatilidad', 'Sharpe', 'Sortino'], [f"{ret_opt*100:.2f}%", f"{vol_opt*100:.2f}%", f"{sharpe_opt:.4f}", f"{sortino:.4f}"]]
    t_met = Table(metricas_data, colWidths=[1.6 * inch] * 4)
    t_met.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), AZUL_OSCURO), ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9), ('BACKGROUND', (0, 1), (-1, 1), GRIS_CLARO), ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'), ('FONTSIZE', (0, 1), (-1, 1), 18), ('TEXTCOLOR', (0, 1), (-1, 1), AZUL_OSCURO), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    story.append(t_met)
    story.append(Spacer(1, 0.2 * inch))

    # Tarjeta Blanca Markowitz
    story += _callout_tecnico(
        titulo="Optimización SLSQP Sujeta a Restricciones",
        texto="La distribución de pesos no es heurística. El Motor iteró mediante Programación Cuadrática Secuencial (SLSQP) "
              "sobre la matriz de covarianzas histórica para encontrar el portafolio tangencial. Las restricciones implementadas "
              "aseguran que ningún activo supere el techo de concentración y que la exposición global de riesgo no cruce el umbral establecido por el módulo LDI.",
        formula="Max: Sharpe = (E[Rp] - Rf) / σp    |    Sujeto a: Σ w_i = 1,  Σ(w_riesgo) ≤ Limite"
    )

    story.append(Paragraph("Distribución de Activos", E['subseccion']))
    df_pesos = pd.DataFrame({'Activo': tickers, 'Peso (%)': (pesos_opt * 100).round(2)}).sort_values('Peso (%)', ascending=False)
    pesos_data = [['Activo', 'Peso (%)', 'Asignación visual']]
    for _, row in df_pesos.iterrows():
        pesos_data.append([row['Activo'], f"{row['Peso (%)']:.2f}%", '█' * max(1, int(row['Peso (%)'] / 3))])
    story.append(_tabla_estilo(pesos_data, [1.5 * inch, 1.2 * inch, 3.8 * inch]))

    if fig_markowitz:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Topología de la Frontera Eficiente", E['subseccion']),
            _fig_a_imagen(fig_markowitz, h_inch=2.8),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — RIESGO E INSTITUCIONALIDAD
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Análisis de Riesgo Estructural (VaR y CVaR)", E['seccion'])

    riesgo_data = [
        ['Métrica', 'Valor (%)', f'Exposición Diaria (${capital_riesgo:,})'],
        ['VaR 95%', f"{var_cvar['VaR_95_hist']*100:.2f}%", f"${abs(var_cvar['VaR_95_hist'])*capital_riesgo:,.0f}"],
        ['CVaR 99% (Expected Shortfall)', f"{var_cvar['CVaR_99']*100:.2f}%", f"${abs(var_cvar['CVaR_99'])*capital_riesgo:,.0f}"],
        ['Maximum Drawdown', f"{max_dd*100:.2f}%", f"${abs(max_dd)*capital_riesgo:,.0f}"]
    ]
    story.append(_tabla_estilo(riesgo_data, [2.8 * inch, 1.5 * inch, 2.2 * inch]))

    story += _callout_tecnico(
        titulo="Modelado de Colas Pesadas (t-Student vs Gauss)",
        texto="Los sistemas tradicionales de riesgo asumen una distribución Normal (campana de Gauss), subestimando masivamente "
              "la frecuencia de crashes del mercado (Cisnes Negros). Motor GaLa calibró los retornos a una distribución empírica t-Student. "
              f"Con grados de libertad (gl = {df_t:.1f}), el modelo engrosa matemáticamente las 'colas' de la gráfica inferior, resultando "
              "en un CVaR (Expected Shortfall) severo y realista que blinda la estructura patrimonial."
    )

    if fig_var:
        story.append(KeepTogether([
            Paragraph("Distribución de Retornos Diarios (Ajuste T-Student)", E['subseccion']),
            _fig_a_imagen(fig_var, h_inch=2.5),
        ]))
    if fig_dd:
        story.append(KeepTogether([
            Paragraph("Profundidad y Duración del Drawdown", E['subseccion']),
            _fig_a_imagen(fig_dd, h_inch=2.2),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — MONTE CARLO Y BACKTESTING
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Proyección Estocástica y Evidencia Empírica", E['seccion'])
    
    if fig_mc:
        story.append(Paragraph(f"Simulación Estocástica de Capital — {num_sims:,} trayectorias", E['subseccion']))
        story.append(_fig_a_imagen(fig_mc, h_inch=2.6))
        
    story += _callout_tecnico(
        titulo="Motor de Inferencia Monte Carlo",
        texto="La gráfica superior proyecta el Valor Futuro combinando el capital inicial y las aportaciones periódicas frente a miles "
              "de futuros posibles generados aleatoriamente. Al no utilizar una tasa de crecimiento lineal, el modelo evidencia el "
              "'Riesgo de Secuencia de Retornos'. El cuartil Adverso (P5) garantiza un intervalo de confianza del 95% para la supervivencia financiera del portafolio."
    )

    if fig_bt:
        story.append(KeepTogether([
            Paragraph(f"Backtesting Comparativo vs Benchmark ({benchmark_ticker})", E['subseccion']),
            _fig_a_imagen(fig_bt, h_inch=2.5),
        ]))

    # Disclaimer legal al final
    story.append(Spacer(1, 0.4 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_TEXTO))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Generado por Motor Cuantitativo GaLa Institutional Solutions. Las metodologías descritas son estrictamente "
        "modelos matemáticos y de probabilidad probabilística, y no constituyen garantía de rendimientos futuros.", E['pie']
    ))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return buffer.getvalue()
