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
    TableStyle, HRFlowable, PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

# ── Paleta Institucional (GaLa ALM) ────────────────────────────────────────────
AZUL_OSCURO  = colors.HexColor('#0a0f2e')
AZUL_MEDIO   = colors.HexColor('#1a2560')
AZUL_ACENTO  = colors.HexColor('#4488ff')
GRIS_CLARO   = colors.HexColor('#e8ecf0')
GRIS_TEXTO   = colors.HexColor('#4a5568')
BLANCO       = colors.white
ROJO         = colors.HexColor('#e53e3e')
VERDE        = colors.HexColor('#38a169')

PAGE_W = 6.5 * inch

def _estilos():
    return {
        'titulo': ParagraphStyle('titulo', fontSize=24, textColor=BLANCO, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=8),
        'subtitulo': ParagraphStyle('subtitulo', fontSize=11, textColor=AZUL_ACENTO, fontName='Helvetica', alignment=TA_CENTER, spaceAfter=4),
        'seccion': ParagraphStyle('seccion', fontSize=13, textColor=AZUL_OSCURO, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6),
        'subseccion': ParagraphStyle('subseccion', fontSize=10, textColor=AZUL_MEDIO, fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=4),
        'normal': ParagraphStyle('normal', fontSize=9, textColor=GRIS_TEXTO, fontName='Helvetica', spaceAfter=4, leading=14),
        'pie': ParagraphStyle('pie', fontSize=7, textColor=GRIS_TEXTO, fontName='Helvetica', alignment=TA_CENTER),
        'tecnico_titulo': ParagraphStyle('tecnico_titulo', fontSize=9, textColor=AZUL_MEDIO, fontName='Helvetica-Bold', spaceAfter=4),
        'tecnico_cuerpo': ParagraphStyle('tecnico_cuerpo', fontSize=8, textColor=AZUL_OSCURO, fontName='Helvetica', leading=12, alignment=TA_JUSTIFY),
        'formula': ParagraphStyle('formula', fontSize=8, textColor=colors.HexColor('#2c5282'), fontName='Courier-Bold', alignment=TA_CENTER, spaceBefore=4, spaceAfter=4),
        'resumen': ParagraphStyle('resumen', fontSize=10, textColor=GRIS_CLARO, fontName='Helvetica', alignment=TA_CENTER, leading=16, leftIndent=40, rightIndent=40)
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
    E = _estilos()
    elementos = [Paragraph(f"NOTA TÉCNICA: {titulo}", E['tecnico_titulo']), Paragraph(texto, E['tecnico_cuerpo'])]
    if formula: elementos.append(Paragraph(formula, E['formula']))
    t = Table([[elementos]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f4f8')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('LINEBEFORE', (0,0), (0,-1), 3, AZUL_ACENTO),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12), ('RIGHTPADDING', (0,0), (-1,-1), 12),
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
        canvas.drawString(30, h - 25, "MOTOR GaLa - INSTITUTIONAL ALM")
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(w - 30, h - 25, f"Página {doc.page}")
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, 25, fill=True, stroke=False)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#8899bb'))
        canvas.drawString(30, 8, "Documento confidencial — Auditoría Solvencia II / CUSF")
        canvas.drawRightString(w - 30, 8, datetime.now().strftime("%d/%m/%Y %H:%M"))
    canvas.restoreState()

# ─────────────────────────────────────────────────────────────────────────────
def generar_reporte_alm_integral(
    institucion, valor_activos, valor_pasivos, ratio_inicial,
    dur_activos_ini, dur_pasivos, shock_bps, scr_tasa, scr_spread, 
    beneficio_div, scr_total, ratio_estresado,
    tickers_activos, pesos_opt, yield_opt, dur_opt, conv_opt,
    fig_gap=None, fig_waterfall=None, fig_frontera=None, fig_mc_surplus=None
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.6*inch, rightMargin=0.6*inch, topMargin=0.6*inch, bottomMargin=0.5*inch)
    E = _estilos()
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 1 — PORTADA ALM
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph("MOTOR GaLa — QUANT SOLUTIONS", E['titulo']))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Evaluación Propia de Riesgos y Solvencia (ORSA)", E['subtitulo']))
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(f"Institución: {institucion}", E['subtitulo']))
    story.append(Paragraph(f"Fecha de emisión: {datetime.now().strftime('%d de %B de %Y')}", E['subtitulo']))
    story.append(Spacer(1, 0.8 * inch))

    veredicto = "CUMPLE" if (valor_activos - valor_pasivos) >= scr_total else "NO CUMPLE"
    color_v = "#38a169" if (valor_activos - valor_pasivos) >= scr_total else "#e53e3e"
    
    story.append(Paragraph(
        f"Este documento evalúa la brecha estructural de duración y liquidez entre los activos y pasivos de la institución. "
        f"Al consolidar los requerimientos de capital (SCR) bajo normativas análogas a Solvencia II / CUSF, "
        f"el portafolio actual presenta un requerimiento agregado de mercado de <b>${scr_total:,.2f} M</b>, "
        f"obteniendo un dictamen regulatorio global de <b><font color='{color_v}'>{veredicto}</font></b>.",
        E['resumen']
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — BALANCE Y REQUERIMIENTO CUSF
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("1. Auditoría de Balance y Riesgo de Mercado", E['seccion'])

    # Balance Status Quo
    story.append(Paragraph("Fotografía del Balance", E['subseccion']))
    balance_data = [
        ['Métrica', 'Valor'],
        ['Valor Total Activos', f"${valor_activos:,.2f} M"],
        ['Valor Total Pasivos (Valor Presente)', f"${valor_pasivos:,.2f} M"],
        ['Capital Disponible (Excedente)', f"${(valor_activos - valor_pasivos):,.2f} M"],
        ['Ratio de Cobertura Base', f"{ratio_inicial*100:.2f}%"]
    ]
    story.append(_tabla_estilo(balance_data, [3.5 * inch, 2.5 * inch]))
    story.append(Spacer(1, 0.2 * inch))
    
    # Pruebas de Estrés (Solvencia II)
    story.append(Paragraph("2. Requerimiento de Capital Estándar (CUSF)", E['subseccion']))
    scr_data = [
        ['Componente de Riesgo', 'Impacto en Capital'],
        ['SCR Tasa de Interés', f"${scr_tasa:,.2f} M"],
        ['SCR Riesgo de Spread (Crédito)', f"${scr_spread:,.2f} M"],
        ['Beneficio por Diversificación', f"-${beneficio_div:,.2f} M"],
        ['SCR MERCADO TOTAL AGREGADO', f"${scr_total:,.2f} M"]
    ]
    
    t_scr = _tabla_estilo(scr_data, [3.5*inch, 2.5*inch])
    t_scr.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 3), (1, 3), VERDE),
        ('FONTNAME', (0, 4), (1, 4), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 4), (1, 4), colors.HexColor('#f0f4f8')),
        ('TEXTCOLOR', (0, 4), (1, 4), AZUL_OSCURO),
    ]))
    story.append(t_scr)

    if fig_waterfall:
        story.append(Spacer(1, 0.2 * inch))
        story.append(_fig_a_imagen(fig_waterfall, h_inch=2.8))

    story += _callout_tecnico(
        titulo="Agregación de Capital (Fórmula Estándar)",
        texto="La consolidación de los requerimientos de capital asume una correlación imperfecta entre el riesgo de "
              "tasa y el riesgo de crédito (spread). El beneficio de diversificación reduce el requerimiento bruto, "
              "optimizando la exigencia patrimonial según la Circular Única de Seguros y Fianzas."
    )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — LIQUIDEZ Y REESTRUCTURACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("3. Análisis de Brecha de Liquidez", E['seccion'])
    
    story.append(Paragraph(
        "El análisis dinámico proyecta los ingresos por cupones y amortizaciones frente a las salidas por "
        "obligaciones técnicas. La trayectoria de liquidez acumulada determina la capacidad técnica de "
        "absorción sin forzar liquidación de activos a descuento.", E['normal']
    ))
    
    if fig_gap:
        story.append(Spacer(1, 0.1 * inch))
        story.append(_fig_a_imagen(fig_gap, h_inch=3.0))

    story += _seccion("4. Reestructuración y Calce (Inmunización)", E['seccion'])
    story.append(Paragraph(
        f"Se ejecutó un algoritmo de optimización (SLSQP) para emparejar la sensibilidad de las carteras. "
        f"El portafolio sugerido alcanza un Calce de Duración de <b>{dur_opt:.2f} años</b> y una cobertura de "
        f"convexidad de <b>{conv_opt:.2f}</b>, preservando un Yield esperado del <b>{yield_opt*100:.2f}%</b>.",
        E['normal']
    ))

    df_pesos = pd.DataFrame({'Instrumento': tickers_activos, 'Peso (%)': (pesos_opt * 100).round(2)}).sort_values('Peso (%)', ascending=False)
    pesos_data = [['Instrumento', 'Asignación Sugerida (%)', 'Ejecución Target']]
    for _, row in df_pesos.iterrows():
        if row['Peso (%)'] > 0.01:
            pesos_data.append([row['Instrumento'], f"{row['Peso (%)']:.2f}%", '█' * max(1, int(row['Peso (%)'] / 3))])
    
    story.append(Spacer(1, 0.1 * inch))
    story.append(_tabla_estilo(pesos_data, [1.5 * inch, 1.5 * inch, 3.0 * inch]))

    if fig_frontera:
        story.append(PageBreak())
        story.append(Spacer(1, 0.3 * inch))
        story += _seccion("5. Frontera Eficiente ALM", E['seccion'])
        story.append(_fig_a_imagen(fig_frontera, h_inch=3.5))

    if fig_mc_surplus:
        story.append(PageBreak())
        story.append(Spacer(1, 0.3 * inch))
        story += _seccion("6. Simulación Estocástica del Excedente", E['seccion'])
        story.append(_fig_a_imagen(fig_mc_surplus, h_inch=3.5))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return buffer.getvalue()
