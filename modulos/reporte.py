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
ORO          = colors.HexColor('#d4a017')

PAGE_W = 6.5 * inch

def _estilos():
    return {
        'titulo': ParagraphStyle('titulo', fontSize=26, textColor=BLANCO, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=8),
        'subtitulo': ParagraphStyle('subtitulo', fontSize=11, textColor=AZUL_ACENTO, fontName='Helvetica', alignment=TA_CENTER, spaceAfter=4),
        'seccion': ParagraphStyle('seccion', fontSize=13, textColor=AZUL_OSCURO, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6),
        'subseccion': ParagraphStyle('subseccion', fontSize=10, textColor=AZUL_MEDIO, fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=4),
        'normal': ParagraphStyle('normal', fontSize=9, textColor=GRIS_TEXTO, fontName='Helvetica', spaceAfter=4, leading=14),
        'metodo': ParagraphStyle('metodo', fontSize=8, textColor=colors.HexColor('#374151'), fontName='Helvetica-Oblique', spaceAfter=0, leading=12, leftIndent=10, rightIndent=10),
        'pie': ParagraphStyle('pie', fontSize=7, textColor=GRIS_TEXTO, fontName='Helvetica', alignment=TA_CENTER),
        'tecnico_titulo': ParagraphStyle('tecnico_titulo', fontSize=9, textColor=AZUL_MEDIO, fontName='Helvetica-Bold', spaceAfter=4),
        'tecnico_cuerpo': ParagraphStyle('tecnico_cuerpo', fontSize=8, textColor=AZUL_OSCURO, fontName='Helvetica', leading=12, alignment=TA_JUSTIFY),
        'formula': ParagraphStyle('formula', fontSize=8, textColor=colors.HexColor('#2c5282'), fontName='Courier-Bold', alignment=TA_CENTER, spaceBefore=4, spaceAfter=4),
    }

def _nota(texto: str, E: dict) -> Table:
    """Caja de nota metodológica simple"""
    celda = Table([[Paragraph(texto, E['metodo'])]], colWidths=[PAGE_W - 0.1 * inch])
    celda.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4ff')),
        ('LINEBEFORE', (0, 0), (0, -1),  2,   AZUL_ACENTO),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return celda

def _callout_tecnico(titulo, texto, formula=None):
    """Caja Blanca (White-Box) Institucional con borde grueso y título"""
    E = _estilos()
    elementos = [Paragraph(f"METODOLOGÍA: {titulo}", E['tecnico_titulo']), Paragraph(texto, E['tecnico_cuerpo'])]
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

def _fig_a_imagen(fig, width=800, height=400, scale=2, w_inch=None, h_inch=None, **kwargs):
    if fig is None: return Spacer(1, 0.1*inch)
    fig.update_layout(margin=dict(l=110, r=40, t=40, b=60))
    img_bytes = fig.to_image(format="png", width=width * 1.5, height=height * 1.5, scale=scale)
    ancho_fisico = 6.5 * inch
    alto_fisico = h_inch * inch if h_inch else (height / width) * ancho_fisico
    return Image(io.BytesIO(img_bytes), width=ancho_fisico, height=alto_fisico)

def _tabla_estilo(data, col_widths, header_color=None):
    header_color = header_color or AZUL_OSCURO
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0),  header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0),  BLANCO),
        ('FONTNAME', (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return t

def _seccion(titulo, estilo, hr_color=None) -> list:
    return [Paragraph(titulo, estilo), HRFlowable(width="100%", thickness=1, color=hr_color or AZUL_ACENTO, spaceAfter=10)]

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
        canvas.drawString(30, 8, "Documento confidencial — Motor GaLa © 2026")
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
    # Parámetros LDI White-Box
    limite_riesgo_global=None, perfil_estrategico=None, pension_imss=None, brecha_pensional=None, semanas_cotizadas=None, salario_promedio=None
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch, topMargin=0.6 * inch, bottomMargin=0.5 * inch)
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
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Universo analizado: {' | '.join(tickers)}", E['subtitulo']))
    story.append(Spacer(1, 0.8 * inch))

    story.append(Paragraph(
        f"Este reporte detalla la arquitectura algorítmica detrás de la estructuración del portafolio. "
        f"El universo de inversión ha sido procesado mediante un motor estocástico calibrado con variables macroeconómicas "
        f"y distribuciones asimétricas para evitar los sesgos de los modelos tradicionales.",
        ParagraphStyle('resumen_portada', fontSize=10, textColor=GRIS_CLARO, fontName='Helvetica', alignment=TA_CENTER, spaceAfter=6, leading=18, leftIndent=30, rightIndent=30)
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
            ['Semanas Cotizadas', f"{semanas_cotizadas:,}" if semanas_cotizadas else "N/A"],
            ['Salario Promedio Diario', f"${salario_promedio:,.2f} MXN" if salario_promedio else "N/A"],
            ['Pensión Vitalicia Estimada (IMSS)', f"${pension_imss:,.2f} MXN/mes"],
        ]
        if brecha_pensional is not None:
            estado = "Déficit Estructural" if brecha_pensional > 0 else "Superávit (Preservación)"
            ldi_data.append(['Diagnóstico de Flujo', estado])
            
        story.append(_tabla_estilo(ldi_data, [3*inch, 3.5*inch]))
        
        story += _callout_tecnico(
            titulo="Algoritmo de Pensión (IMSS Ley 73)",
            texto="La pensión gubernamental se estima aplicando el marco normativo de la Ley del Seguro Social de 1973. "
                  "La función algorítmica calcula la relación entre el salario promedio y la UMA vigente para extraer el porcentaje "
                  "de la 'Cuantía Básica' (tope legal del 13%). Posteriormente, se suma el factor de 'Incrementos Anuales' equivalente "
                  "al 2.45% por cada bloque de 52 semanas que exceda el requisito mínimo de 500 semanas."
        )

        story.append(Paragraph("2. Prescripción Algorítmica de Riesgo", E['subseccion']))
        riesgo_asignado = limite_riesgo_global * 100 if limite_riesgo_global else 80.0
        story.append(Paragraph(
            f"El Motor GaLa determinó matemáticamente un perfil <b>{perfil_estrategico or 'Optimizado'}</b>. "
            f"Basado en el nivel de certidumbre del flujo proyectado, el presupuesto de riesgo máximo (límite de "
            f"exposición a Renta Variable) se bloqueó algorítmicamente en el <b>{riesgo_asignado:.1f}%</b>.",
            E['normal']
        ))
        
        story += _callout_tecnico(
            titulo="Inversión Basada en Pasivos (LDI)",
            texto="El modelo LDI (Liability-Driven Investing) abandona el enfoque clásico de 'maximizar retornos' a ciegas. "
                  "En su lugar, el algoritmo analiza el pasivo futuro del individuo. "
                  "Si existe un superávit, el optimizador restringe la volatilidad forzando la compra de activos de refugio. "
                  "Si hay déficit, amplía la frontera eficiente permitiendo exposición controlada a renta variable."
        )
        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — PORTAFOLIO ÓPTIMO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Arquitectura del Portafolio Óptimo", E['seccion'])

    story += _callout_tecnico(
        titulo="Optimización SLSQP Sujeta a Restricciones",
        texto="La distribución de pesos no es heurística. El Motor iteró mediante Programación Cuadrática Secuencial (SLSQP) "
              "sobre la matriz de covarianzas histórica para encontrar el portafolio tangencial. Las restricciones "
              "aseguran que ningún activo supere el techo de concentración y que la exposición global de riesgo no cruce el umbral establecido.",
        formula="Max: Sharpe = (E[Rp] - Rf) / σp    |    Sujeto a: Σ w_i = 1,  Σ(w_riesgo) ≤ Límite"
    )
    story.append(Spacer(1, 0.15 * inch))

    metricas_data = [['Retorno Anual', 'Volatilidad', 'Sharpe', 'Sortino'], [f"{ret_opt*100:.2f}%", f"{vol_opt*100:.2f}%", f"{sharpe_opt:.4f}", f"{sortino:.4f}"]]
    t_met = Table(metricas_data, colWidths=[1.6 * inch] * 4)
    t_met.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), AZUL_OSCURO), ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, 0), 9), ('BACKGROUND', (0, 1), (-1, 1), GRIS_CLARO), ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'), ('FONTSIZE', (0, 1), (-1, 1), 18), ('TEXTCOLOR', (0, 1), (-1, 1), AZUL_OSCURO), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10)]))
    story.append(t_met)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Distribución Óptima del Capital", E['subseccion']))
    df_pesos = pd.DataFrame({'Activo': tickers, 'Peso (%)': (pesos_opt * 100).round(2)}).sort_values('Peso (%)', ascending=False)
    pesos_data = [['Activo', 'Peso (%)', 'Asignación visual']]
    for _, row in df_pesos.iterrows():
        pesos_data.append([row['Activo'], f"{row['Peso (%)']:.2f}%", '█' * max(1, int(row['Peso (%)'] / 3))])
    story.append(_tabla_estilo(pesos_data, [1.5 * inch, 1.2 * inch, 3.8 * inch]))

    if fig_markowitz:
        story.append(Spacer(1, 0.15 * inch))
        story.append(KeepTogether([
            Paragraph("Topología de la Frontera Eficiente", E['subseccion']),
            _fig_a_imagen(fig_markowitz, h_inch=2.8),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — RIESGO INSTITUCIONAL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Análisis de Riesgo Estructural (VaR y CVaR)", E['seccion'])

    riesgo_data = [
        ['Métrica', 'Valor (%)', f'Pérdida diaria (${capital_riesgo:,} USD)'],
        ['VaR 95% Histórico', f"{var_cvar['VaR_95_hist']*100:.2f}%", f"${abs(var_cvar['VaR_95_hist'])*capital_riesgo:,.0f}"],
        ['VaR 99% Histórico', f"{var_cvar['VaR_99_hist']*100:.2f}%", f"${abs(var_cvar['VaR_99_hist'])*capital_riesgo:,.0f}"],
        ['CVaR 95% (Expected Shortfall)', f"{var_cvar['CVaR_95']*100:.2f}%", f"${abs(var_cvar['CVaR_95'])*capital_riesgo:,.0f}"],
        ['CVaR 99%', f"{var_cvar['CVaR_99']*100:.2f}%", f"${abs(var_cvar['CVaR_99'])*capital_riesgo:,.0f}"],
        ['Maximum Drawdown', f"{max_dd*100:.2f}%", f"${abs(max_dd)*capital_riesgo:,.0f}"],
    ]
    story.append(_tabla_estilo(riesgo_data, [2.8 * inch, 1.5 * inch, 2.2 * inch]))
    story.append(Spacer(1, 0.08 * inch))

    story += _callout_tecnico(
        titulo="Modelado de Colas Pesadas (t-Student vs Gauss)",
        texto="Los sistemas tradicionales asumen una distribución Normal (campana de Gauss), subestimando masivamente "
              "la frecuencia de crashes del mercado (Cisnes Negros). Motor GaLa calibró los retornos a una distribución empírica t-Student. "
              f"Con grados de libertad (gl = {df_t:.1f}), el modelo engrosa matemáticamente las 'colas', resultando "
              "en un CVaR (Expected Shortfall) realista que blinda la estructura patrimonial."
    )

    if fig_var:
        story.append(KeepTogether([
            Paragraph("Distribución de Retornos Diarios — VaR y CVaR", E['subseccion']),
            _fig_a_imagen(fig_var, h_inch=2.7),
        ]))
    if fig_dd:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Curva de Drawdown Histórico", E['subseccion']),
            _fig_a_imagen(fig_dd, h_inch=2.2),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — STRESS TESTING + CORRELACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Stress Testing — Escenarios Históricos", E['seccion'])

    stress_data = [['Escenario', 'Impacto (%)', 'Pérdida estimada (USD)']]
    for _, row in df_stress.iterrows():
        stress_data.append([row['Escenario'], f"{row['Pérdida (%)']:.1f}%", f"${abs(row['Pérdida (USD)']):,.0f}"])
    t_stress = Table(stress_data, colWidths=[3.2 * inch, 1.5 * inch, 1.8 * inch])
    t_stress.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_OSCURO), ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TEXTCOLOR', (1, 1), (1, -1), ROJO), ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
    ]))
    story.append(t_stress)

    if fig_stress:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Impacto por Escenario — Visualización", E['subseccion']),
            _fig_a_imagen(fig_stress, h_inch=2.7),
        ]))

    if fig_corr:
        story.append(KeepTogether([
            Spacer(1, 0.25 * inch),
            Paragraph("Correlación Dinámica Rolling — 60 días", E['seccion']),
            HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=8),
            _fig_a_imagen(fig_corr, h_inch=2.7),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 5 — MONTE CARLO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Proyección de Capital — Monte Carlo", E['seccion'])
    
    story += _callout_tecnico(
        titulo="Motor de Inferencia Estocástica",
        texto="La proyección no utiliza una tasa de crecimiento lineal engañosa. Se implementó un Movimiento Browniano "
              "Geométrico mensual con shocks de distribución t-Student calibrados a la volatilidad histórica real de la cartera. "
              "El cuartil Adverso (P5) garantiza un intervalo de confianza del 95% para la supervivencia financiera del portafolio, "
              "evidenciando el Riesgo de Secuencia de Retornos."
    )

    mc_data = [
        ['Escenario', 'Capital Final (MXN)', 'Crecimiento total'],
        ['Adverso (P5)',         f"${p5_final:,.0f}",  f"{((p5_final/capital_inicial)-1)*100:.1f}%"],
        ['Mod. Adverso (P25)',   f"${p25_final:,.0f}", f"{((p25_final/capital_inicial)-1)*100:.1f}%"],
        ['Base (P50)',           f"${p50_final:,.0f}", f"{((p50_final/capital_inicial)-1)*100:.1f}%"],
        ['Mod. Favorable (P75)', f"${p75_final:,.0f}", f"{((p75_final/capital_inicial)-1)*100:.1f}%"],
        ['Favorable (P95)',      f"${p95_final:,.0f}", f"{((p95_final/capital_inicial)-1)*100:.1f}%"],
    ]
    t_mc = Table(mc_data, colWidths=[2.0 * inch, 2.5 * inch, 2.0 * inch])
    t_mc.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_OSCURO), ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fff5f5')), ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fffaf0')),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f0fff4')), ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f5faff')), ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor('#ebf8ff')),
        ('TEXTCOLOR', (2, 1), (2, 1), ROJO), ('TEXTCOLOR', (2, 2), (2, 2), colors.HexColor('#b45309')), ('TEXTCOLOR', (2, 3), (2, 3), VERDE), ('TEXTCOLOR', (2, 4), (2, 4), colors.HexColor('#1d4ed8')), ('TEXTCOLOR', (2, 5), (2, 5), AZUL_ACENTO),
        ('FONTNAME', (1, 1), (-1, -1), 'Helvetica-Bold'), ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')), ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_mc)

    if fig_mc:
        story.append(KeepTogether([
            Spacer(1, 0.2 * inch),
            Paragraph(f"Trayectorias de Capital — {num_sims:,} simulaciones", E['subseccion']),
            _fig_a_imagen(fig_mc, h_inch=3.2),
        ]))

    # ── Nota legal ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_TEXTO))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Este reporte fue generado automáticamente por Motor Cuantitativo GaLa. "
        "Los resultados son producto de modelos matemáticos con fines informativos "
        "y no constituyen asesoría de inversión. Rendimientos pasados no garantizan resultados futuros. "
        "Modelo de riesgo calibrado con distribución t de Student para captura de eventos extremos.",
        E['pie']
    ))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return buffer.getvalue()
