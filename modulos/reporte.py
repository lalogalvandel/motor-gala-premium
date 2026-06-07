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

# ── Paleta institucional premium (Modo Oscuro Nivel Banca de Inversión) ──────
AZUL_NOCHE   = colors.HexColor('#0B0F19')   # Fondo profundo, elegante y frío
AZUL_OSCURO  = colors.HexColor('#111827')   # Headers y tarjetas KPI
AZUL_MEDIO   = colors.HexColor('#1F2937')   # Líneas y subtítulos
AZUL_BASE    = colors.HexColor('#2563EB')   # Elementos de marca
AZUL_ACENTO  = colors.HexColor('#3B82F6')   # Acento primario (Azul vibrante)
AZUL_BRILLO  = colors.HexColor('#93C5FD')   # Textos destacados y headers de tabla
AZUL_ICE     = colors.HexColor('#141E30')   # Notas informativas

GRIS_LINEA   = colors.HexColor('#374151')   # Rejillas súper sutiles
GRIS_FONDO   = colors.HexColor('#141C2F')   # Filas pares de tabla
GRIS_CLARO   = colors.HexColor('#1E293B')   # Filas impares de tabla
GRIS_TEXTO   = colors.HexColor('#F8FAFC')   # Texto principal de alta legibilidad
GRIS_SUAVE   = colors.HexColor('#94A3B8')   # Texto secundario / pies de figura

BLANCO       = colors.HexColor('#FFFFFF')
ROJO         = colors.HexColor('#F87171')   # Rojo coral brillante (legible en oscuro)
ROJO_SUAVE   = colors.HexColor('#2C1418')   # Fondo rojo hiper tenue
VERDE        = colors.HexColor('#34D399')   # Verde esmeralda
VERDE_SUAVE  = colors.HexColor('#132721')   # Fondo verde hiper tenue
AMBAR        = colors.HexColor('#FBBF24')   # Ámbar brillante
AMBAR_SUAVE  = colors.HexColor('#2D2413')   # Fondo ámbar hiper tenue
ORO          = colors.HexColor('#D4A017')

PAGE_W = 6.5 * inch

# ── Tipografía institucional ───────────────────────────────────────────────────
def _estilos() -> dict:
    return {
        # ── Portada ──────────────────────────────────────────────────────────
        'titulo': ParagraphStyle(
            'titulo', fontSize=32, textColor=BLANCO,
            fontName='Helvetica-Bold', alignment=TA_CENTER,
            spaceAfter=12, leading=38),
        'titulo_marca': ParagraphStyle(
            'titulo_marca', fontSize=10, textColor=AZUL_BRILLO,
            fontName='Helvetica-Bold', alignment=TA_CENTER,
            spaceAfter=6, charSpace=3, leading=14),
        'subtitulo': ParagraphStyle(
            'subtitulo', fontSize=11.5, textColor=AZUL_BRILLO,
            fontName='Helvetica', alignment=TA_CENTER,
            spaceAfter=8, leading=17),
        'portada_cuerpo': ParagraphStyle(
            'portada_cuerpo', fontSize=9.5,
            textColor=GRIS_SUAVE,
            fontName='Helvetica', alignment=TA_JUSTIFY,
            spaceAfter=8, leading=17, leftIndent=24, rightIndent=24),
        
        # ── Encabezados de sección ────────────────────────────────────────────
        'etiqueta_seccion': ParagraphStyle(
            'etiqueta_seccion', fontSize=7, textColor=AZUL_ACENTO,
            fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=2,
            charSpace=2, leading=10),
        'seccion': ParagraphStyle(
            'seccion', fontSize=14, textColor=BLANCO, 
            fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=4, leading=18),
        'subseccion': ParagraphStyle(
            'subseccion', fontSize=10.5, textColor=AZUL_BRILLO, 
            fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4, leading=14),
        
        # ── Texto corrido ─────────────────────────────────────────────────────
        'normal': ParagraphStyle(
            'normal', fontSize=9, textColor=GRIS_TEXTO,
            fontName='Helvetica', spaceAfter=5, leading=14.5),
        'justificado': ParagraphStyle(
            'justificado', fontSize=9, textColor=GRIS_TEXTO,
            fontName='Helvetica', spaceAfter=5, leading=14.5,
            alignment=TA_JUSTIFY),
        
        # ── Callouts y cajas metodológicas ────────────────────────────────────
        'metodo': ParagraphStyle(
            'metodo', fontSize=8, textColor=colors.HexColor('#CBD5E1'), 
            fontName='Helvetica-Oblique', spaceAfter=0, leading=12,
            leftIndent=10, rightIndent=10),
        'caja_titulo': ParagraphStyle(
            'caja_titulo', fontSize=8, textColor=AZUL_BRILLO, 
            fontName='Helvetica-Bold', spaceAfter=4, charSpace=1, leading=11),
        'caja_titulo_alerta': ParagraphStyle(
            'caja_titulo_alerta', fontSize=8, textColor=AMBAR,
            fontName='Helvetica-Bold', spaceAfter=4, charSpace=1, leading=11),
        'caja_cuerpo': ParagraphStyle(
            'caja_cuerpo', fontSize=8.5, textColor=GRIS_TEXTO, 
            fontName='Helvetica', leading=13.5, alignment=TA_JUSTIFY),
        'formula': ParagraphStyle(
            'formula', fontSize=8.5, textColor=AZUL_BRILLO,
            fontName='Courier-Bold', alignment=TA_CENTER,
            spaceBefore=5, spaceAfter=5),
        
        # ── KPI Cards ─────────────────────────────────────────────────────────
        'kpi_label': ParagraphStyle(
            'kpi_label', fontSize=7, textColor=GRIS_SUAVE,
            fontName='Helvetica-Bold', alignment=TA_CENTER,
            spaceAfter=2, charSpace=1, leading=10),
        'kpi_valor': ParagraphStyle(
            'kpi_valor', fontSize=22, textColor=BLANCO, 
            fontName='Helvetica-Bold', alignment=TA_CENTER,
            spaceAfter=2, leading=26),
        'kpi_sub': ParagraphStyle(
            'kpi_sub', fontSize=7, textColor=GRIS_SUAVE,
            fontName='Helvetica', alignment=TA_CENTER, leading=10),
        
        # ── Pie y disclaimers ─────────────────────────────────────────────────
        'pie': ParagraphStyle(
            'pie', fontSize=7, textColor=GRIS_SUAVE,
            fontName='Helvetica', alignment=TA_CENTER, leading=11),
        'disclaimer': ParagraphStyle(
            'disclaimer', fontSize=7.5, textColor=GRIS_SUAVE,
            fontName='Helvetica-Oblique', leading=12.5, alignment=TA_JUSTIFY),
    }

# ── Bloques de layout reutilizables ───────────────────────────────────────────

def _nota(texto: str, E: dict) -> Table:
    celda = Table([[Paragraph(texto, E['metodo'])]], colWidths=[PAGE_W - 0.1 * inch])
    celda.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0), (-1, -1), AZUL_ICE),
        ('LINEBEFORE',     (0, 0), (0, -1),  3, AZUL_ACENTO),
        ('TOPPADDING',     (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING',  (0, 0), (-1, -1), 9),
        ('LEFTPADDING',    (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',   (0, 0), (-1, -1), 12),
    ]))
    return celda

def _callout_tecnico(titulo: str, texto: str, formula: str = None) -> list:
    E = _estilos()
    encabezado = Paragraph(f"◈  METODOLOGÍA  ·  {titulo.upper()}", E['caja_titulo'])
    cuerpo = Paragraph(texto, E['caja_cuerpo'])
    elementos: list = [encabezado, cuerpo]

    if formula:
        box_formula = Table([[Paragraph(formula, E['formula'])]], colWidths=[PAGE_W - 0.7 * inch])
        box_formula.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), AZUL_OSCURO),
            ('BOX',           (0, 0), (-1, -1), 0.5, GRIS_LINEA),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elementos.append(box_formula)

    t = Table([[elementos]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRIS_FONDO),
        ('BOX',           (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('LINEBEFORE',    (0, 0), (0, -1),  4,   AZUL_ACENTO),
        ('LINEABOVE',     (0, 0), (-1, 0),  1.5, AZUL_ACENTO),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
    ]))
    return [Spacer(1, 0.12 * inch), t, Spacer(1, 0.12 * inch)]

def _callout_alerta(titulo: str, texto: str) -> list:
    E = _estilos()
    encabezado = Paragraph(f"⚑  PRESCRIPCIÓN  ·  {titulo.upper()}", E['caja_titulo_alerta'])
    cuerpo = Paragraph(texto, E['caja_cuerpo'])
    t = Table([[[encabezado, cuerpo]]], colWidths=[PAGE_W])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), AMBAR_SUAVE),
        ('BOX',           (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('LINEBEFORE',    (0, 0), (0, -1),  4,   AMBAR),
        ('LINEABOVE',     (0, 0), (-1, 0),  1.5, AMBAR),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 14),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 14),
    ]))
    return [Spacer(1, 0.10 * inch), t, Spacer(1, 0.10 * inch)]

def _fig_a_imagen(fig, width=800, height=400, scale=2, w_inch=None, h_inch=None, **kwargs):
    if fig is None: return Spacer(1, 0.1 * inch)
    
    # Inyección limpia del Modo Oscuro en Plotly
    fig.update_layout(
        paper_bgcolor='#0B0F19', 
        plot_bgcolor='#0B0F19',
        font=dict(color='#94A3B8'), 
        margin=dict(l=110, r=40, t=40, b=60)
    )
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)', zerolinecolor='rgba(255,255,255,0.08)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.04)', zerolinecolor='rgba(255,255,255,0.08)')

    img_bytes = fig.to_image(format="png", width=width * 1.5, height=height * 1.5, scale=scale)
    ancho_fisico = 6.5 * inch
    alto_fisico  = h_inch * inch if h_inch else (height / width) * ancho_fisico
    return Image(io.BytesIO(img_bytes), width=ancho_fisico, height=alto_fisico)

def _tabla_estilo(data: list, col_widths: list, header_color=None) -> Table:
    hdr = header_color or AZUL_OSCURO
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  hdr),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  AZUL_BRILLO), 
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0),  9),
        ('TOPPADDING',    (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  10),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.5, AZUL_ACENTO),
        
        ('TEXTCOLOR',     (0, 1), (-1, -1), GRIS_TEXTO),
        ('FONTSIZE',      (0, 1), (-1, -1), 9),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [GRIS_FONDO, GRIS_CLARO]),
        ('GRID',          (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('TOPPADDING',    (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    return t

def _kpi_cards(datos: list) -> Table:
    E = _estilos()
    n = len(datos)
    w_c = PAGE_W / n

    celdas = []
    for etiqueta, valor, sub in datos:
        bloque = [
            Paragraph(etiqueta.upper(), E['kpi_label']), Spacer(1, 3),
            Paragraph(valor, E['kpi_valor']), Spacer(1, 3),
            Paragraph(sub, E['kpi_sub']),
        ]
        celdas.append(bloque)

    t = Table([celdas], colWidths=[w_c] * n)
    cmds = [
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('BOX',           (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('LINEBELOW',     (0, 0), (-1, -1), 3,   AZUL_ACENTO),
    ]
    for i in range(n):
        # ── CORRECCIÓN CRÍTICA DE CONTRASTE AQUÍ ──
        bg = AZUL_OSCURO if i % 2 == 0 else GRIS_FONDO 
        cmds.append(('BACKGROUND', (i, 0), (i, 0), bg))
    t.setStyle(TableStyle(cmds))
    return t

def _seccion(titulo: str, estilo, hr_color=None, etiqueta: str = None) -> list:
    E = _estilos()
    elems = []
    if etiqueta:
        elems.append(Paragraph(f"— {etiqueta.upper()} —", E['etiqueta_seccion']))
    elems.append(Paragraph(titulo, estilo))
    elems.append(HRFlowable(width="100%", thickness=1.5, color=hr_color or AZUL_ACENTO, spaceAfter=10))
    return elems

def _on_page(canvas, doc):
    w, h = letter
    canvas.saveState()

    if doc.page == 1:
        canvas.setFillColor(AZUL_NOCHE)
        canvas.rect(0, 0, w, h, fill=True, stroke=False)

        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, h - 1.0 * inch, w, 1.0 * inch, fill=True, stroke=False)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.rect(0, h - 1.0 * inch, w, 2.5, fill=True, stroke=False)

        canvas.setFillColor(AZUL_BASE)
        path = canvas.beginPath()
        path.moveTo(w - 2.2 * inch, h)
        path.lineTo(w, h)
        path.lineTo(w, h - 2.1 * inch)
        path.close()
        canvas.drawPath(path, fill=True, stroke=False)

        canvas.setFillColor(AZUL_ACENTO)
        path = canvas.beginPath()
        path.moveTo(w - 0.72 * inch, h)
        path.lineTo(w, h)
        path.lineTo(w, h - 0.72 * inch)
        path.close()
        canvas.drawPath(path, fill=True, stroke=False)

        canvas.setFont('Helvetica-Bold', 8)
        canvas.setFillColor(AZUL_BRILLO)
        canvas.drawString(0.5 * inch, h - 0.52 * inch, "MOTOR CUANTITATIVO  ·  ANÁLISIS INSTITUCIONAL DE PORTAFOLIOS")
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(GRIS_SUAVE)
        canvas.drawRightString(w - 0.5 * inch, h - 0.52 * inch, datetime.now().strftime("%d %b %Y").upper())

        canvas.setStrokeColor(GRIS_LINEA)
        canvas.setLineWidth(0.6)
        canvas.line(0.5 * inch, h * 0.40, w - 0.5 * inch, h * 0.40)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.circle(0.5 * inch,     h * 0.40, 2.5, fill=True, stroke=False)
        canvas.circle(w - 0.5 * inch, h * 0.40, 2.5, fill=True, stroke=False)

        canvas.setStrokeColor(colors.HexColor('#0c1a3e'))
        canvas.setLineWidth(1.2)
        for i in range(7):
            d = (i + 1) * 0.22 * inch
            canvas.line(0, d, d, 0)

        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, 0.56 * inch, fill=True, stroke=False)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.rect(0, 0.56 * inch, w, 1.5, fill=True, stroke=False)
        canvas.setFont('Helvetica-Bold', 7)
        canvas.setFillColor(GRIS_SUAVE)
        canvas.drawString(0.5 * inch, 0.23 * inch, "DOCUMENTO CONFIDENCIAL  ·  DISTRIBUCIÓN RESTRINGIDA AL DESTINATARIO")
        canvas.setFont('Helvetica', 7)
        canvas.drawRightString(w - 0.5 * inch, 0.23 * inch, f"Motor GaLa ©  {datetime.now().year}  ·  Todos los derechos reservados")

    else:
        canvas.setFillColor(AZUL_NOCHE)
        canvas.rect(0, 0, w, h, fill=True, stroke=False)

        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, h - 34, w, 34, fill=True, stroke=False)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.rect(0, h - 36, w, 2, fill=True, stroke=False)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.rect(0, h - 34, 4, 34, fill=True, stroke=False)
        canvas.setFont('Helvetica-Bold', 8.5)
        canvas.setFillColor(BLANCO)
        canvas.drawString(16, h - 22, "MOTOR CUANTITATIVO  GaLa")
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(AZUL_BRILLO)
        canvas.drawRightString(w - 16, h - 22, f"Análisis Institucional  ·  p. {doc.page}")

        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, 22, fill=True, stroke=False)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.rect(0, 22, w, 1, fill=True, stroke=False)
        canvas.setFont('Helvetica', 6.5)
        canvas.setFillColor(GRIS_SUAVE)
        canvas.drawString(16, 7, "Documento confidencial — Motor GaLa  ©  2026  ·  Distribución restringida al destinatario autorizado")
        canvas.drawRightString(w - 16, 7, datetime.now().strftime("%d/%m/%Y  %H:%M"))

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
def generar_reporte(
    tickers, pesos_opt, ret_opt, vol_opt, sharpe_opt, sortino, desv_down, df_t,
    var_cvar, max_dd, duracion_dd, inicio_dd, fin_dd, df_stress, capital_riesgo,
    p5_final, p25_final, p50_final, p75_final, p95_final,
    horizonte_años, capital_inicial, aportacion_mensual, num_sims,
    metricas_bt, benchmark_ticker, df_screening=None,
    fig_markowitz=None, fig_mc=None, fig_var=None, fig_dd=None,
    fig_stress=None, fig_bt=None, fig_anuales=None, fig_corr=None,
    limite_riesgo_global=None, perfil_estrategico=None, pension_imss=None,
    brecha_pensional=None, semanas_cotizadas=None, salario_promedio=None,
    simular_m40=False
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.65 * inch, bottomMargin=0.55 * inch
    )
    E = _estilos()
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 1 — PORTADA
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("MOTOR CUANTITATIVO GaLa", E['titulo']))
    story.append(Spacer(1, 0.22 * inch))
    story.append(Paragraph("Reporte Institucional de Portafolio  ·  Metodología White-Box", E['subtitulo']))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph(datetime.now().strftime("%d de %B de %Y").upper(), E['titulo_marca']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "  ·  ".join(tickers),
        ParagraphStyle('universo_portada', fontSize=10, textColor=GRIS_SUAVE,
                       fontName='Helvetica', alignment=TA_CENTER, spaceAfter=0, leading=15)
    ))
    story.append(Spacer(1, 0.75 * inch))
    story.append(Paragraph(
        "El presente reporte expone, con transparencia metodológica íntegra, la arquitectura "
        "algorítmica empleada en la estructuración del portafolio óptimo. El universo de inversión "
        "fue procesado a través de un motor estocástico de segunda generación, calibrado con "
        "distribuciones asimétricas de cola pesada y parámetros macroeconómicos actualizados, "
        "con el propósito expreso de superar las limitaciones estadísticas inherentes a los modelos "
        "de varianza media convencionales.",
        E['portada_cuerpo']
    ))
    story.append(Paragraph(
        "Cada sección de este documento detalla el fundamento cuantitativo subyacente a las decisiones "
        "adoptadas, proveyendo al lector institucional los elementos necesarios para la auditoría, "
        "replicación y validación independiente de los resultados presentados.",
        E['portada_cuerpo']
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA CONDICIONAL — MODELADO LDI
    if pension_imss is not None:
        story.append(Spacer(1, 0.3 * inch))
        story += _seccion("Modelado Actuarial LDI y Pasivo Pensional IMSS (Ley 73)", E['seccion'], etiqueta="Análisis de Pasivos · LDI")
        story.append(Paragraph("I. Calibración de Pasivos Previsionales", E['subseccion']))
        story.append(Paragraph(
            "El modelo cuantifica el pasivo pensional individual mediante la aplicación rigurosa "
            "del régimen normativo de la Ley del Seguro Social de 1973, determinando la renta "
            "vitalicia base y evaluando la brecha de cobertura frente al nivel de consumo objetivo.", E['justificado']
        ))

        ldi_data = [
            ['Parámetro Actuarial', 'Valor Calibrado'],
            ['Semanas cotizadas al régimen obligatorio IMSS', f"{semanas_cotizadas:,}" if semanas_cotizadas else "N/D"],
            ['Salario Promedio Diario Integrado (SPDI)', f"${salario_promedio:,.2f} MXN" if salario_promedio else "N/D"],
            ['Estrategia de reconocimiento de semanas', 'Modalidad 40 — Topado a 25 UMAs' if simular_m40 else 'Evolución salarial orgánica'],
            ['Pensión vitalicia estimada (IMSS Ley 73)', f"${pension_imss:,.2f} MXN / mes"],
        ]
        if brecha_pensional is not None:
            diagnostico = "⚠  Déficit estructural de cobertura" if brecha_pensional > 0 else "✓  Superávit — Régimen de preservación patrimonial"
            ldi_data.append(['Diagnóstico de suficiencia de flujo', diagnostico])

        story.append(_tabla_estilo(ldi_data, [3.3 * inch, 3.2 * inch]))
        story.append(Spacer(1, 0.08 * inch))

        if simular_m40:
            story += _callout_tecnico(
                titulo="Estrategia de Continuación Voluntaria — Modalidad 40",
                texto="El modelo actuarial incorpora la estrategia de Continuación Voluntaria al Régimen Obligatorio durante los últimos cinco años previos al retiro. Bajo este esquema, el Salario Promedio Diario Integrado (SPDI) converge matemáticamente al tope máximo de cotización equivalente a 25 UMAs, generando una asimetría actuarial positiva de gran magnitud: el valor presente neto de los incrementos acumulados en la pensión vitalicia supera exponencialmente el costo total de las aportaciones voluntarias requeridas para sostener la Modalidad 40 durante el periodo de aplicación. Esta estrategia constituye una de las palancas de mayor impacto en la ingeniería de pasivos dentro del marco Ley 73."
            )
        else:
            story += _callout_tecnico(
                titulo="Algoritmo de Cuantificación Pensional — IMSS Ley 73 (Orgánico)",
                texto="La estimación de la pensión gubernamental se fundamenta en el marco normativo de la Ley del Seguro Social de 1973. El algoritmo calibra la Cuantía Básica en función del número de semanas cotizadas acreditadas y aplica los Incrementos Anuales correspondientes, derivados exclusivamente de la trayectoria salarial histórica del cotizante. El modelo no contempla aportaciones voluntarias ni estrategias activas de reconocimiento de semanas adicionales, reflejando la evolución orgánica del pasivo."
            )

        story.append(Paragraph("II. Prescripción Algorítmica del Presupuesto de Riesgo", E['subseccion']))
        riesgo_asignado = limite_riesgo_global * 100 if limite_riesgo_global else 80.0
        story.append(Paragraph(
            f"El Motor GaLa determinó, mediante análisis de suficiencia actuarial sobre el flujo "
            f"neto proyectado, un perfil de inversión <b>{perfil_estrategico or 'Optimizado'}</b>. "
            f"Con base en la certidumbre del diferencial entre retiros esperados y renta vitalicia "
            f"garantizada, el presupuesto máximo de exposición a activos de renta variable fue "
            f"fijado algorítmicamente en <b>{riesgo_asignado:.1f}%</b> del capital total gestionado.", E['normal']
        ))

        story += _callout_alerta(
            titulo="Inversión Basada en Pasivos (LDI — Liability-Driven Investing)",
            texto="El paradigma LDI reorienta el objetivo de optimización: en lugar de maximizar el retorno esperado en abstracto, el algoritmo subordina la construcción del portafolio al análisis del pasivo financiero individual. En presencia de superávit actuarial, el optimizador contrae el presupuesto de riesgo, incrementando la ponderación de activos de refugio (renta fija soberana, instrumentos indexados a inflación). En escenarios de déficit, el algoritmo amplía la frontera eficiente hacia mayor exposición a renta variable, buscando capturar la prima de riesgo necesaria para cerrar la brecha de cobertura en el horizonte de acumulación definido."
        )
        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — PORTAFOLIO ÓPTIMO
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Arquitectura del Portafolio Óptimo", E['seccion'], etiqueta="Optimización Cuantitativa · Frontera Eficiente")

    story += _callout_tecnico(
        titulo="Optimización SLSQP con Restricciones de Concentración y Presupuesto de Riesgo",
        texto="La distribución de pesos no responde a criterios heurísticos ni a juicios discrecionales. El Motor convergió iterativamente mediante el algoritmo SLSQP (Sequential Least Squares Programming) —programación cuadrática secuencial— operando sobre la matriz de covarianzas estimada por ventana rodante, con el propósito de mitigar el sesgo de estacionariedad implícito en las estimaciones estáticas. Las restricciones de caja aseguran que ningún instrumento individual supere el techo de concentración definido, mientras que la restricción de riesgo global garantiza que la exposición agregada a activos de renta variable no exceda el presupuesto actuarial autorizado en ningún punto del proceso de optimización.",
        formula="Max: Sharpe = ( E[Rp] − Rf ) / σp    |    Sujeto a: Σ wᵢ = 1,  Σ w_riesgo ≤ Límite Global"
    )
    story.append(Spacer(1, 0.1 * inch))

    story.append(_kpi_cards([
        ("Retorno Anual Esperado",  f"{ret_opt*100:.2f}%",  "E[Rp] histórico anualizado"),
        ("Volatilidad Anual",       f"{vol_opt*100:.2f}%",  "σp — desviación estándar"),
        ("Ratio Sharpe",            f"{sharpe_opt:.4f}",    "Prima por unidad de riesgo total"),
        ("Ratio Sortino",           f"{sortino:.4f}",       "Prima por unidad de riesgo a la baja"),
    ]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Distribución Óptima del Capital por Instrumento", E['subseccion']))
    story.append(Paragraph(
        "La siguiente tabla presenta la asignación de capital resultante del proceso de optimización, "
        "ordenada de mayor a menor ponderación. La columna de intensidad de asignación permite "
        "apreciar de forma intuitiva la concentración relativa por instrumento.", E['justificado']
    ))
    df_pesos = pd.DataFrame({'Activo': tickers, 'Peso (%)': (pesos_opt * 100).round(2)}).sort_values('Peso (%)', ascending=False)
    pesos_data = [['Instrumento / Activo', 'Ponderación (%)', 'Intensidad de asignación']]
    for _, row in df_pesos.iterrows():
        barra = '█' * max(1, int(row['Peso (%)'] / 3))
        pesos_data.append([row['Activo'], f"{row['Peso (%)']:.2f} %", barra])
    story.append(_tabla_estilo(pesos_data, [1.8 * inch, 1.4 * inch, 3.3 * inch]))

    if fig_markowitz:
        story.append(Spacer(1, 0.15 * inch))
        story.append(KeepTogether([
            Paragraph("Superficie de la Frontera Eficiente de Markowitz", E['subseccion']),
            Paragraph("Cada punto sobre la curva representa un portafolio matemáticamente inalcanzable de superar en términos de Sharpe dentro del universo analizado. El portafolio tangencial maximiza la prima de riesgo ajustada por volatilidad.", E['normal']),
            _fig_a_imagen(fig_markowitz, h_inch=2.8),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — RIESGO ESTRUCTURAL
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Análisis de Riesgo Estructural — VaR, CVaR y Drawdown", E['seccion'], etiqueta="Gestión de Riesgos · Métricas Downside")

    riesgo_data = [
        ['Métrica de Riesgo', 'Cuantía  (%)', f'Pérdida diaria estimada  (${capital_riesgo:,} USD)'],
        ['VaR 95%  — Simulación Histórica', f"{var_cvar['VaR_95_hist']*100:.2f} %", f"${abs(var_cvar['VaR_95_hist']) * capital_riesgo:,.0f}"],
        ['VaR 99%  — Simulación Histórica', f"{var_cvar['VaR_99_hist']*100:.2f} %", f"${abs(var_cvar['VaR_99_hist']) * capital_riesgo:,.0f}"],
        ['CVaR 95%  (Expected Shortfall)', f"{var_cvar['CVaR_95']*100:.2f} %", f"${abs(var_cvar['CVaR_95']) * capital_riesgo:,.0f}"],
        ['CVaR 99%  (Expected Shortfall)', f"{var_cvar['CVaR_99']*100:.2f} %", f"${abs(var_cvar['CVaR_99']) * capital_riesgo:,.0f}"],
        ['Maximum Drawdown  —  Período histórico', f"{max_dd*100:.2f} %", f"${abs(max_dd) * capital_riesgo:,.0f}"],
    ]
    t_riesgo = Table(riesgo_data, colWidths=[2.8 * inch, 1.5 * inch, 2.2 * inch])
    t_riesgo.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  AZUL_BRILLO), 
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('TOPPADDING',    (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  10),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.5, AZUL_ACENTO),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [GRIS_FONDO, GRIS_CLARO]),
        
        ('TEXTCOLOR',     (0, 1), (0, -1),  GRIS_TEXTO),
        ('TEXTCOLOR',     (1, 1), (1, -1),  ROJO),
        ('TEXTCOLOR',     (2, 1), (2, -1),  ROJO),
        
        ('GRID',          (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('TOPPADDING',    (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('FONTNAME',      (1, 1), (1, -1),  'Helvetica-Bold'),
    ]))
    story.append(t_riesgo)
    story.append(Spacer(1, 0.08 * inch))

    story += _callout_tecnico(
        titulo="Modelado de Eventos Extremos — Distribución t-Student vs. Distribución Gaussiana",
        texto=f"Los sistemas convencionales de gestión de riesgos asumen distribuciones normales en los retornos, lo que conduce a una subestimación sistemática y estructural de la frecuencia e intensidad de los eventos extremos —eventos de cola o, en la terminología popular, 'Cisnes Negros'—. El Motor GaLa calibró los retornos diarios del portafolio a una distribución t de Student empírica. Con grados de libertad estimados en gl = {df_t:.1f}, el modelo engrosa matemáticamente las colas de la distribución, produciendo un CVaR (Expected Shortfall o Déficit Esperado en Escenarios Adversos) que refleja con fidelidad estadística superior el comportamiento del portafolio bajo condiciones de estrés sistémico. Esta calibración es determinante para la cuantificación de reservas de capital y para el blindaje de la estructura patrimonial ante escenarios de crisis no anticipados."
    )

    if fig_var:
        story.append(KeepTogether([
            Paragraph("Distribución Empírica de Retornos Diarios — VaR y CVaR", E['subseccion']),
            Paragraph("La línea vertical sólida delimita el umbral del VaR; el área sombreada a su izquierda representa el Expected Shortfall (CVaR): la pérdida promedio esperada condicionada a exceder dicho umbral, con probabilidad 1 − α.", E['normal']),
            _fig_a_imagen(fig_var, h_inch=2.7),
        ]))

    if fig_dd:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Curva de Drawdown Histórico Acumulado", E['subseccion']),
            Paragraph("El Maximum Drawdown cuantifica la caída máxima observada desde un máximo histórico hasta el mínimo subsecuente. Es la métrica canónica de evaluación del Riesgo de Secuencia de Retornos y determina el capital en riesgo de no recuperación.", E['normal']),
            _fig_a_imagen(fig_dd, h_inch=2.2),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — STRESS TESTING + CORRELACIÓN DINÁMICA
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Pruebas de Estrés — Retroproyección sobre Crisis Históricas", E['seccion'], etiqueta="Análisis de Escenarios · Stress Testing")
    story.append(Paragraph(
        "El portafolio fue sometido a retroproyección sistemática (backtesting de estrés) sobre los principales episodios de dislocación sistémica registrados en los mercados financieros globales. Los factores de choque aplicados corresponden a las caídas efectivamente observadas en los activos del universo durante cada crisis, sin suavizamiento temporal ni ajuste de supervivencia.", E['justificado']
    ))
    story.append(Spacer(1, 0.08 * inch))

    stress_data = [['Escenario Histórico de Estrés', 'Impacto  (%)', 'Pérdida estimada (USD)']]
    for _, row in df_stress.iterrows():
        stress_data.append([row['Escenario'], f"{row['Pérdida (%)']:.1f} %", f"${abs(row['Pérdida (USD)']):,.0f}"])
    
    t_stress = Table(stress_data, colWidths=[3.2 * inch, 1.5 * inch, 1.8 * inch])
    t_stress.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  AZUL_BRILLO), 
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('TOPPADDING',    (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  10),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.5, AZUL_ACENTO),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [GRIS_FONDO, GRIS_CLARO]),
        
        ('TEXTCOLOR',     (0, 1), (0, -1),  GRIS_TEXTO),
        ('TEXTCOLOR',     (1, 1), (1, -1),  ROJO), 
        ('TEXTCOLOR',     (2, 1), (2, -1),  ROJO), 
        
        ('GRID',          (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('TOPPADDING',    (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('FONTNAME',      (1, 1), (1, -1),  'Helvetica-Bold'),
    ]))
    story.append(t_stress)

    if fig_stress:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Impacto por Escenario de Crisis — Comparativa Visual", E['subseccion']),
            _fig_a_imagen(fig_stress, h_inch=2.7),
        ]))

    if fig_corr:
        story.append(KeepTogether([
            Spacer(1, 0.25 * inch),
            *_seccion("Correlación Dinámica Rodante — Ventana de 60 Días", E['seccion'], etiqueta="Análisis de Dependencia · Correlación Condicional"),
            Paragraph(
                "La correlación móvil captura la dinámica de codependencia entre los activos a lo largo del tiempo, revelando regímenes de mercado en los cuales los beneficios de diversificación se comprimen o invierten —fenómeno característico durante episodios de aversión al riesgo sistémico—. Este análisis informa la robustez real de la estructura del portafolio bajo condiciones de mercado adversas, donde la correlación observada en períodos normales pierde validez predictiva.", E['justificado']
            ),
            _fig_a_imagen(fig_corr, h_inch=2.7),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 5 — PROYECCIÓN DE CAPITAL MONTE CARLO
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Proyección Estocástica de Capital — Simulación de Monte Carlo", E['seccion'], etiqueta="Proyección Financiera · Simulación Estocástica")

    story += _callout_tecnico(
        titulo="Motor de Inferencia Estocástica — Movimiento Browniano Geométrico (GBM)",
        texto="La proyección de capital no se sustenta en tasas de crecimiento lineales ni en modelos deterministas que omitan la volatilidad intrínseca del portafolio. El Motor implementa un Movimiento Browniano Geométrico (Geometric Brownian Motion) de frecuencia mensual, con shocks de distribución t-Student calibrados a la volatilidad histórica real de la cartera y ajustados por el drift esperado neto de aportaciones periódicas. El percentil Adverso (P5) proporciona un intervalo de confianza del 95% para la supervivencia financiera del portafolio, exhibiendo con rigor matemático el Riesgo de Secuencia de Retornos: el orden cronológico en que se materializan los retornos negativos puede erosionar el capital de forma irreversible, incluso cuando el retorno promedio del período completo resulte positivo."
    )

    mc_data = [
        ['Escenario  (Percentil)', 'Capital Final Proyectado', 'Crecimiento total acumulado'],
        ['Adverso extremo  — P5',         f"${p5_final:,.0f}", f"{((p5_final  / capital_inicial) - 1) * 100:.1f} %"],
        ['Moderadamente adverso  — P25',  f"${p25_final:,.0f}", f"{((p25_final / capital_inicial) - 1) * 100:.1f} %"],
        ['Escenario base  — P50',         f"${p50_final:,.0f}", f"{((p50_final / capital_inicial) - 1) * 100:.1f} %"],
        ['Moderadamente favorable  — P75', f"${p75_final:,.0f}", f"{((p75_final / capital_inicial) - 1) * 100:.1f} %"],
        ['Favorable extremo  — P95',       f"${p95_final:,.0f}", f"{((p95_final / capital_inicial) - 1) * 100:.1f} %"],
    ]
    t_mc = Table(mc_data, colWidths=[2.5 * inch, 2.2 * inch, 1.8 * inch])
    t_mc.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  AZUL_BRILLO),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9.5),
        ('TOPPADDING',    (0, 0), (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  10),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.5, AZUL_ACENTO),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        
        ('TEXTCOLOR',     (0, 1), (0, -1),  GRIS_TEXTO), 
        
        ('BACKGROUND',    (0, 1), (-1, 1),  ROJO_SUAVE),
        ('BACKGROUND',    (0, 2), (-1, 2),  AMBAR_SUAVE),
        ('BACKGROUND',    (0, 3), (-1, 3),  GRIS_FONDO),  
        ('BACKGROUND',    (0, 4), (-1, 4),  VERDE_SUAVE),
        ('BACKGROUND',    (0, 5), (-1, 5),  AZUL_ICE),
        
        ('TEXTCOLOR',     (1, 1), (-1, 1),  ROJO),
        ('TEXTCOLOR',     (1, 2), (-1, 2),  AMBAR),
        ('TEXTCOLOR',     (1, 3), (-1, 3),  GRIS_TEXTO),  
        ('TEXTCOLOR',     (1, 4), (-1, 4),  VERDE),
        ('TEXTCOLOR',     (1, 5), (-1, 5),  AZUL_BRILLO),
        
        ('FONTNAME',      (1, 1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('TOPPADDING',    (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 9),
    ]))
    story.append(t_mc)

    if fig_mc:
        story.append(KeepTogether([
            Spacer(1, 0.2 * inch),
            Paragraph(f"Distribución de Trayectorias de Capital — {num_sims:,} Simulaciones", E['subseccion']),
            Paragraph("El haz de trayectorias visualiza la dispersión probabilística de resultados posibles. Las bandas de percentiles delimitan el espacio de confianza institucional para la toma de decisiones sobre estrategias de retiro, aportaciones y rebalanceo dinámico.", E['normal']),
            _fig_a_imagen(fig_mc, h_inch=3.2),
        ]))

    # ── Disclaimer y nota legal ────────────────────────────────────────────────
    story.append(Spacer(1, 0.45 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_LINEA, spaceAfter=0))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Este documento fue generado de forma automatizada por Motor Cuantitativo GaLa. Los resultados presentados constituyen el producto de modelos matemáticos y estadísticos con fines exclusivamente informativos y analíticos; no representan asesoría de inversión, gestión patrimonial ni recomendación financiera individualizada en los términos de la legislación aplicable. Los rendimientos históricos no garantizan resultados futuros. El modelo de riesgo emplea una distribución t de Student para la captura de eventos extremos; toda interpretación debe ser realizada por un profesional calificado en el marco regulatorio pertinente.", E['disclaimer']
    ))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return buffer.getvalue()
