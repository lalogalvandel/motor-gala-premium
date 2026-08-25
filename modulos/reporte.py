# =============================================================================
# Motor GaLa VIP - Edición Especial Consultoría
# Creado por: Eduardo Galván del Río
# =============================================================================
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
AZUL_NOCHE   = colors.HexColor('#0B0F19')   
AZUL_OSCURO  = colors.HexColor('#111827')   
AZUL_MEDIO   = colors.HexColor('#1F2937')   
AZUL_BASE    = colors.HexColor('#2563EB')   
AZUL_ACENTO  = colors.HexColor('#3B82F6')   
AZUL_BRILLO  = colors.HexColor('#93C5FD')   
AZUL_ICE     = colors.HexColor('#141E30')   

GRIS_LINEA   = colors.HexColor('#374151')   
GRIS_FONDO   = colors.HexColor('#141C2F')   
GRIS_CLARO   = colors.HexColor('#1E293B')   
GRIS_TEXTO   = colors.HexColor('#F8FAFC')   
GRIS_SUAVE   = colors.HexColor('#94A3B8')   

BLANCO       = colors.HexColor('#FFFFFF')
ROJO         = colors.HexColor('#F87171')   
ROJO_SUAVE   = colors.HexColor('#2C1418')   
VERDE        = colors.HexColor('#34D399')   
VERDE_SUAVE  = colors.HexColor('#132721')   
AMBAR        = colors.HexColor('#FBBF24')   
AMBAR_SUAVE  = colors.HexColor('#2D2413')   
ORO          = colors.HexColor('#D4A017')

PAGE_W = 6.5 * inch

# ── Tipografía institucional ───────────────────────────────────────────────────
def _estilos() -> dict:
    return {
        'titulo': ParagraphStyle('titulo', fontSize=32, textColor=BLANCO, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=12, leading=38),
        'titulo_marca': ParagraphStyle('titulo_marca', fontSize=10, textColor=AZUL_BRILLO, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=6, charSpace=3, leading=14),
        'subtitulo': ParagraphStyle('subtitulo', fontSize=11.5, textColor=AZUL_BRILLO, fontName='Helvetica', alignment=TA_CENTER, spaceAfter=8, leading=17),
        'portada_cuerpo': ParagraphStyle('portada_cuerpo', fontSize=10.5, textColor=GRIS_SUAVE, fontName='Helvetica', alignment=TA_JUSTIFY, spaceAfter=8, leading=17, leftIndent=24, rightIndent=24),
        'etiqueta_seccion': ParagraphStyle('etiqueta_seccion', fontSize=7, textColor=AZUL_ACENTO, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=2, charSpace=2, leading=10),
        'seccion': ParagraphStyle('seccion', fontSize=14, textColor=BLANCO, fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=4, leading=18),
        'subseccion': ParagraphStyle('subseccion', fontSize=10.5, textColor=AZUL_BRILLO, fontName='Helvetica-Bold', spaceBefore=10, spaceAfter=4, leading=14),
        'normal': ParagraphStyle('normal', fontSize=9, textColor=GRIS_TEXTO, fontName='Helvetica', spaceAfter=5, leading=14.5),
        'justificado': ParagraphStyle('justificado', fontSize=9, textColor=GRIS_TEXTO, fontName='Helvetica', spaceAfter=5, leading=14.5, alignment=TA_JUSTIFY),
        'metodo': ParagraphStyle('metodo', fontSize=8, textColor=colors.HexColor('#CBD5E1'), fontName='Helvetica-Oblique', spaceAfter=0, leading=12, leftIndent=10, rightIndent=10),
        'caja_titulo': ParagraphStyle('caja_titulo', fontSize=8, textColor=AZUL_BRILLO, fontName='Helvetica-Bold', spaceAfter=4, charSpace=1, leading=11),
        'caja_titulo_alerta': ParagraphStyle('caja_titulo_alerta', fontSize=8, textColor=AMBAR, fontName='Helvetica-Bold', spaceAfter=4, charSpace=1, leading=11),
        'caja_cuerpo': ParagraphStyle('caja_cuerpo', fontSize=8.5, textColor=GRIS_TEXTO, fontName='Helvetica', leading=13.5, alignment=TA_JUSTIFY),
        'formula': ParagraphStyle('formula', fontSize=8.5, textColor=AZUL_BRILLO, fontName='Courier-Bold', alignment=TA_CENTER, spaceBefore=5, spaceAfter=5),
        'kpi_label': ParagraphStyle('kpi_label', fontSize=7, textColor=GRIS_SUAVE, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=2, charSpace=1, leading=10),
        'kpi_valor': ParagraphStyle('kpi_valor', fontSize=22, textColor=BLANCO, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=2, leading=26),
        'kpi_sub': ParagraphStyle('kpi_sub', fontSize=7, textColor=GRIS_SUAVE, fontName='Helvetica', alignment=TA_CENTER, leading=10),
        'pie': ParagraphStyle('pie', fontSize=7, textColor=GRIS_SUAVE, fontName='Helvetica', alignment=TA_CENTER, leading=11),
        'disclaimer': ParagraphStyle('disclaimer', fontSize=7.5, textColor=GRIS_SUAVE, fontName='Helvetica-Oblique', leading=12.5, alignment=TA_JUSTIFY),
    }

# ── Bloques de layout reutilizables ───────────────────────────────────────────
def _callout_tecnico(titulo: str, texto: str, formula: str = None) -> list:
    E = _estilos()
    encabezado = Paragraph(f"◈  ANÁLISIS GALA  ·  {titulo.upper()}", E['caja_titulo'])
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
    encabezado = Paragraph(f"⚑  PLAN DE ACCIÓN  ·  {titulo.upper()}", E['caja_titulo_alerta'])
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
        bg = AZUL_OSCURO if i % 2 == 0 else GRIS_FONDO 
        cmds.append(('BACKGROUND', (i, 0), (i, 0), bg))
    t.setStyle(TableStyle(cmds))
    return t

def _seccion(titulo: str, estilo, hr_color=None, etiqueta: str = None) -> list:
    E = _estilos()
    elems = []
    if etiqueta: elems.append(Paragraph(f"— {etiqueta.upper()} —", E['etiqueta_seccion']))
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
        canvas.drawString(0.5 * inch, h - 0.52 * inch, "MOTOR CUANTITATIVO  ·  CONSULTORÍA PRIVADA")
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
        canvas.drawRightString(w - 0.5 * inch, 0.23 * inch, f"Motor GaLa ©  {datetime.now().year}  ·  Lalo Galván")

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
        canvas.drawRightString(w - 16, h - 22, f"Planeación Patrimonial  ·  p. {doc.page}")

        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, 22, fill=True, stroke=False)
        canvas.setFillColor(AZUL_ACENTO)
        canvas.rect(0, 22, w, 1, fill=True, stroke=False)
        canvas.setFont('Helvetica', 6.5)
        canvas.setFillColor(GRIS_SUAVE)
        canvas.drawString(16, 7, "Documento confidencial — Motor GaLa  ©  2026")
        canvas.drawRightString(w - 16, 7, datetime.now().strftime("%d/%m/%Y  %H:%M"))

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# LA FUNCIÓN MAESTRA DEL REPORTE (PULIDA PARA EL CLIENTE)
# ─────────────────────────────────────────────────────────────────────────────
def generar_reporte(
    nombre_cliente, meta_mensual, tasa_retiro_swr, regimen_pensional, 
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
    # PÁGINA 1 — PORTADA Y DIAGNÓSTICO
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("MOTOR CUANTITATIVO GaLa", E['titulo']))
    story.append(Spacer(1, 0.22 * inch))
    story.append(Paragraph("Tu Plan Patrimonial Personalizado", E['subtitulo']))
    story.append(Spacer(1, 0.12 * inch))
    story.append(Paragraph(datetime.now().strftime("%d de %B de %Y").upper(), E['titulo_marca']))
    
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph(f"Análisis preparado exclusivamente para: {nombre_cliente.upper()}", 
                 ParagraphStyle('cliente', fontSize=12, textColor=VERDE, fontName='Helvetica-Bold', alignment=TA_CENTER, charSpace=1)))
    story.append(Spacer(1, 0.5 * inch))

    story.append(Paragraph("Este plan patrimonial ha sido diseñado específicamente para ti, utilizando modelos matemáticos avanzados (Motor GaLa). El objetivo de este documento es darte claridad absoluta sobre dónde estás parado hoy, si tus ahorros serán suficientes para tu retiro, y exactamente qué debes hacer a partir de mañana para optimizar tu dinero de forma profesional.", E['portada_cuerpo']))
    
    # ── RESUMEN LDI (DIAGNÓSTICO DIRECTO) ──
    story.append(Spacer(1, 0.4 * inch))
    story += _seccion("Tu Diagnóstico Financiero de Retiro", E['seccion'], etiqueta="Paso 1: ¿Te va a alcanzar?")
    
    es_ley_73 = (pension_imss is not None and pension_imss > 0)
    
    ldi_data = [['Variable Clave', 'Tu Situación Actual']]
    ldi_data.append(['Años para tu retiro', f"{horizonte_años} años"])
    ldi_data.append(['Ingreso mensual que deseas', f"${meta_mensual:,.2f} MXN libres"])
    
    if es_ley_73:
        ldi_data.append(['Pensión del Gobierno Estimada', f"${pension_imss:,.2f} MXN / mes"])
    else:
        ldi_data.append(['Pensión del Gobierno', '$0.00 MXN (Dependes 100% de tus inversiones)'])

    diagnostico = "⚠ Necesitas ajustar tu estrategia de inversión" if brecha_pensional > 0 else "✓ Vas por excelente camino (Superávit)"
    ldi_data.append(['Diagnóstico del Motor GaLa', diagnostico])

    story.append(_tabla_estilo(ldi_data, [3.3 * inch, 3.2 * inch]))
    story.append(Spacer(1, 0.2 * inch))

    if brecha_pensional > 0:
        story += _callout_alerta(
            titulo="Atención: Existe un déficit para tu meta",
            texto=f"Si continúas invirtiendo de la misma forma, te faltarán aproximadamente ${brecha_pensional:,.0f} MXN al mes para mantener el estilo de vida que deseas en tu retiro (ajustado por inflación). Para solucionar esto, el Motor GaLa ha diseñado el portafolio de la siguiente página, el cual asume el nivel de riesgo estadístico exacto para ayudarte a cerrar esta brecha."
        )
    else:
        story += _callout_tecnico(
            titulo="Felicidades: Tu plan es financieramente sólido",
            texto=f"Tus aportaciones y capital actual son suficientes para superar tu meta mensual por ${abs(brecha_pensional):,.0f} MXN (ya descontando la inflación). El portafolio de la siguiente página fue diseñado para **preservar** tu riqueza, evitando tomar riesgos innecesarios en la bolsa de valores."
        )
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — LA RECETA (PORTAFOLIO ÓPTIMO)
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Tu Plan de Acción (Portafolio Óptimo)", E['seccion'], etiqueta="Paso 2: ¿Qué debes hacer con tu dinero?")

    story.append(Paragraph("Para alcanzar la máxima eficiencia (mayor ganancia posible con el menor riesgo matemático), tu dinero debe estar distribuido exactamente de la siguiente manera:", E['normal']))

    df_pesos = pd.DataFrame({'Activo': tickers, 'Peso (%)': (pesos_opt * 100).round(2)})
    df_pesos_reales = df_pesos[df_pesos['Peso (%)'] > 0].sort_values('Peso (%)', ascending=False)
    
    pesos_data = [['Instrumento / Activo a Comprar', 'Porcentaje de tu Capital Sugerido']]
    for _, row in df_pesos_reales.iterrows():
        pesos_data.append([row['Activo'], f"{row['Peso (%)']:.2f} %"])
    story.append(_tabla_estilo(pesos_data, [3.2 * inch, 3.3 * inch]))

    story.append(Spacer(1, 0.2 * inch))
    story.append(_kpi_cards([
        ("Rendimiento Promedio Anual",  f"{ret_opt*100:.2f}%",  "Histórico esperado"),
        ("Volatilidad de la Estrategia", f"{vol_opt*100:.2f}%",  "Nivel de fluctuación"),
        ("Calificación de Eficiencia",   f"{sharpe_opt:.2f}",    "Ratio de Sharpe (>1 es excelente)"),
    ]))

    if fig_markowitz:
        story.append(Spacer(1, 0.15 * inch))
        story.append(KeepTogether([
            Paragraph("El Mapa de tus Inversiones (Frontera Eficiente)", E['subseccion']),
            Paragraph("La estrella roja representa tu portafolio sugerido. Hemos analizado matemáticamente miles de combinaciones (los puntos de colores) para asegurarnos de que estás ubicado en la 'frontera', el borde exacto donde nadie más en el mercado puede obtener mejores rendimientos sin asumir un riesgo desproporcionado.", E['normal']),
            _fig_a_imagen(fig_markowitz, h_inch=2.8),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — RIESGO TRADUCIDO AL ESPAÑOL
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Radiografía de Riesgos", E['seccion'], etiqueta="Paso 3: ¿Qué esperar en las crisis?")
    story.append(Paragraph(f"Toda inversión conlleva riesgo. Como tu consultor, mi responsabilidad es que estés psicológicamente preparado para los movimientos naturales del mercado. Si invirtieras un portafolio de **${capital_riesgo:,.0f} MXN** con la distribución sugerida, esto es matemáticamente lo peor que podría pasar:", E['justificado']))
    story.append(Spacer(1, 0.08 * inch))

    riesgo_data = [
        ['Escenario en la Bolsa', 'Caída Máxima Esperada', f'Dinero en Riesgo (MXN)'],
        ['En un mes malo \n(1 de cada 20 meses - VaR 95%)', f"{var_cvar['VaR_95_hist']*100:.1f} %", f"${abs(var_cvar['VaR_95_hist']) * capital_riesgo:,.0f}"],
        ['En un mes catastrófico \n(1 de cada 100 meses - VaR 99%)', f"{var_cvar['VaR_99_hist']*100:.1f} %", f"${abs(var_cvar['VaR_99_hist']) * capital_riesgo:,.0f}"],
        ['En la peor crisis global de la historia \n(Maximum Drawdown)', f"{max_dd*100:.1f} %", f"${abs(max_dd) * capital_riesgo:,.0f}"],
    ]
    
    # Tabla con formato más amable
    t_riesgo = Table(riesgo_data, colWidths=[3.0 * inch, 1.5 * inch, 2.0 * inch])
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
        ('TEXTCOLOR',     (1, 1), (2, -1),  ROJO),
        ('GRID',          (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('TOPPADDING',    (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
        ('FONTNAME',      (1, 1), (2, -1),  'Helvetica-Bold'),
    ]))
    story.append(t_riesgo)
    story.append(Spacer(1, 0.2 * inch))

    story += _callout_tecnico(
        titulo="Nota sobre la Cobertura Cambiaria",
        texto="Si gran parte de tu portafolio está en dólares (Ej. S&P 500, ETFs globales), tienes un escudo natural. En la historia de México, cuando hay pánico en los mercados globales, el Peso Mexicano suele perder valor frente al Dólar. Esto hace que tus inversiones dolarizadas ganen valor en pesos, amortiguando e incluso borrando las caídas de la bolsa."
    )

    if fig_dd:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Curva de las peores caídas históricas de esta estrategia", E['subseccion']),
            _fig_a_imagen(fig_dd, h_inch=2.3),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — TU FUTURO (MONTE CARLO)
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("Proyección de tu Futuro Financiero", E['seccion'], etiqueta="Paso 4: El poder del tiempo")

    story.append(Paragraph(f"Para calcular adónde vas a llegar, el Motor GaLa corrió **2,000 líneas de tiempo alternativas** simulando todos los escenarios de suerte posibles (buenos y malos) en la bolsa durante los próximos **{horizonte_años} años**.", E['justificado']))
    story.append(Spacer(1, 0.15 * inch))

    mc_data = [
        ['Si el mundo se comporta de manera...', 'Tu Capital Acumulado será de:'],
        ['Crisis Prolongada y Mala Suerte \n(Solo pasa el 5% de las veces)', f"${p5_final:,.0f} MXN"],
        ['Crecimiento Normal y Promedio \n(El Escenario Base esperado)', f"${p50_final:,.0f} MXN"],
        ['Mercado Altamente Favorable \n(Solo pasa el 5% de las veces)', f"${p95_final:,.0f} MXN"]
    ]
    t_mc = Table(mc_data, colWidths=[3.5*inch, 3.0*inch])
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
        ('BACKGROUND',    (0, 1), (-1, 1),  ROJO_SUAVE),    # P5
        ('BACKGROUND',    (0, 2), (-1, 2),  GRIS_FONDO),    # P50
        ('BACKGROUND',    (0, 3), (-1, 3),  AZUL_ICE),      # P95
        ('TEXTCOLOR',     (1, 1), (1, 1),   ROJO),          # P5
        ('TEXTCOLOR',     (1, 2), (1, 2),   GRIS_TEXTO),    # P50
        ('TEXTCOLOR',     (1, 3), (1, 3),   AZUL_BRILLO),   # P95
        ('FONTNAME',      (1, 1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ('TOPPADDING',    (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
    ]))
    story.append(t_mc)

    if fig_mc:
        story.append(KeepTogether([
            Spacer(1, 0.2 * inch),
            Paragraph(f"Gráfica de Crecimiento Patrimonial a {horizonte_años} años", E['subseccion']),
            Paragraph("El rango entre la línea roja y azul encapsula el 90% de las probabilidades matemáticas de crecimiento de tu dinero, asumiendo que te apegas con disciplina a la estrategia trazada hoy.", E['normal']),
            _fig_a_imagen(fig_mc, h_inch=3.0),
        ]))

    # ── DISCLAIMER ──
    story.append(Spacer(1, 0.5 * inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_LINEA, spaceAfter=0))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Este documento fue diseñado exclusivamente para la sesión de consultoría privada de Motor GaLa. Los resultados presentados constituyen el producto de modelos matemáticos avanzados y no representan una garantía de rendimientos futuros. La ejecución de este plan de inversión es responsabilidad exclusiva del titular.", E['disclaimer']))

    # Construimos usando tu función de fondos oscuros (Que dejé intacta al principio del script)
    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return buffer.getvalue()
