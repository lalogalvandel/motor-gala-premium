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
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


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
        'titulo': ParagraphStyle(
            'titulo', fontSize=26, textColor=BLANCO,
            fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=8
        ),
        'subtitulo': ParagraphStyle(
            'subtitulo', fontSize=11, textColor=AZUL_ACENTO,
            fontName='Helvetica', alignment=TA_CENTER, spaceAfter=4
        ),
        'seccion': ParagraphStyle(
            'seccion', fontSize=13, textColor=AZUL_OSCURO,
            fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6
        ),
        'subseccion': ParagraphStyle(
            'subseccion', fontSize=10, textColor=AZUL_MEDIO,
            fontName='Helvetica-Bold', spaceBefore=8, spaceAfter=4
        ),
        'normal': ParagraphStyle(
            'normal', fontSize=9, textColor=GRIS_TEXTO,
            fontName='Helvetica', spaceAfter=4, leading=14
        ),
        'metodo': ParagraphStyle(
            'metodo', fontSize=8, textColor=colors.HexColor('#374151'),
            fontName='Helvetica-Oblique', spaceAfter=0, leading=12,
            leftIndent=10, rightIndent=10
        ),
        'pie': ParagraphStyle(
            'pie', fontSize=7, textColor=GRIS_TEXTO,
            fontName='Helvetica', alignment=TA_CENTER
        ),
    }


def _nota(texto: str, E: dict) -> Table:
    """
    Caja de nota metodológica con borde izquierdo azul.
    Visualmente diferenciada del dato, explica el método detrás del número.
    """
    celda = Table(
        [[Paragraph(texto, E['metodo'])]],
        colWidths=[PAGE_W - 0.1 * inch]
    )
    celda.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#f0f4ff')),
        ('LINEBEFOREE',   (0, 0), (0, -1),  1.5, AZUL_ACENTO),
        ('LINEBEFORE',    (0, 0), (0, -1),  2,   AZUL_ACENTO),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    return celda


def _fig_a_imagen(fig, width=800, height=400, scale=2, w_inch=None, h_inch=None, **kwargs):
    fig.update_layout(margin=dict(l=110, r=40, t=40, b=60))
    lienzo_w = width * 1.5
    lienzo_h = height * 1.5
    img_bytes = fig.to_image(format="png", width=lienzo_w, height=lienzo_h, scale=scale)
    if h_inch is not None and w_inch is None:
        alto_fisico  = h_inch * inch
        ancho_fisico = (width / height) * alto_fisico
    elif w_inch is not None and h_inch is None:
        ancho_fisico = w_inch * inch
        alto_fisico  = (height / width) * ancho_fisico
    elif w_inch is not None and h_inch is not None:
        ancho_fisico = w_inch * inch
        alto_fisico  = h_inch * inch
    else:
        ancho_fisico = 6.5 * inch
        alto_fisico  = (height / width) * ancho_fisico
    return Image(io.BytesIO(img_bytes), width=ancho_fisico, height=alto_fisico)


def _tabla_estilo(data, col_widths, header_color=None):
    header_color = header_color or AZUL_OSCURO
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  header_color),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  BLANCO),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return t


def _seccion(titulo, estilo, hr_color=None) -> list:
    return [
        Paragraph(titulo, estilo),
        HRFlowable(width="100%", thickness=1,
                   color=hr_color or AZUL_ACENTO, spaceAfter=10),
    ]


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
    tickers, pesos_opt, ret_opt, vol_opt, sharpe_opt,
    sortino, desv_down, df_t,
    var_cvar, max_dd, duracion_dd, inicio_dd, fin_dd,
    df_stress, capital_riesgo,
    p5_final, p25_final, p50_final, p75_final, p95_final,
    horizonte_años, capital_inicial, aportacion_mensual, num_sims,
    metricas_bt, benchmark_ticker,
    df_screening=None,
    fig_markowitz=None, fig_mc=None, fig_var=None,
    fig_dd=None, fig_stress=None, fig_bt=None,
    fig_anuales=None, fig_corr=None,
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.6 * inch, bottomMargin=0.5 * inch
    )
    E = _estilos()
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 1 — PORTADA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.6 * inch))
    story.append(Paragraph("MOTOR CUANTITATIVO GaLa", E['titulo']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Reporte Institucional de Gestión de Capital y Riesgo", E['subtitulo']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(datetime.now().strftime("%d de %B de %Y"), E['subtitulo']))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Universo analizado: {' | '.join(tickers)}", E['subtitulo']))
    story.append(Spacer(1, 0.8 * inch))

    veredicto_sharpe = "sólido" if sharpe_opt > 1 else "moderado" if sharpe_opt > 0.5 else "bajo"
    veredicto_dd     = "controlado" if abs(max_dd) < 0.15 else "elevado"
    story.append(Paragraph(
        f"El portafolio óptimo identificado por Motor GaLa presenta un retorno esperado anual "
        f"de {ret_opt*100:.2f}% con una volatilidad de {vol_opt*100:.2f}%, "
        f"generando un Ratio de Sharpe {veredicto_sharpe} de {sharpe_opt:.4f}. "
        f"El Maximum Drawdown histórico es {veredicto_dd} en {abs(max_dd)*100:.2f}%, "
        f"con una duración de {duracion_dd} días. "
        f"El modelo de riesgo fue calibrado con distribución t de Student "
        f"(gl={df_t:.1f}), capturando fat tails propias de mercados financieros reales.",
        ParagraphStyle(
            'resumen_portada', fontSize=10, textColor=GRIS_CLARO,
            fontName='Helvetica', alignment=TA_CENTER,
            spaceAfter=6, leading=18, leftIndent=30, rightIndent=30
        )
    ))
    story.append(Spacer(1, 0.5 * inch))

    # Nota metodológica de portada
    story.append(Paragraph(
        "METODOLOGÍA GENERAL",
        ParagraphStyle('metodo_titulo_portada', fontSize=8, textColor=AZUL_ACENTO,
                       fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4,
                       letterSpacing=1.5)
    ))
    story.append(Paragraph(
        "Este reporte fue generado por un sistema cuantitativo de cuatro etapas: "
        "(1) selección de activos mediante screening fundamental y clustering K-Means, "
        "(2) optimización de pesos por maximización del Ratio de Sharpe bajo SLSQP con restricciones de concentración y Glide Path actuarial, "
        "(3) medición del riesgo mediante VaR histórico, CVaR, Maximum Drawdown y Stress Testing sobre ventanas históricas reales, "
        "y (4) proyección estocástica de capital mediante simulación de Monte Carlo calibrada con distribución t de Student.",
        ParagraphStyle('metodo_portada', fontSize=8, textColor=GRIS_CLARO,
                       fontName='Helvetica-Oblique', alignment=TA_CENTER,
                       spaceAfter=0, leading=13, leftIndent=40, rightIndent=40)
    ))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — PORTAFOLIO ÓPTIMO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("1. Portafolio Óptimo — Max Sharpe", E['seccion'])

    story.append(_nota(
        "Método: Optimización cuadrática secuencial (SLSQP) sobre la frontera eficiente de Markowitz. "
        "El algoritmo maximiza el Ratio de Sharpe sujeto a tres restricciones: "
        "(a) suma de pesos igual a 1, (b) peso mínimo y máximo por activo para controlar concentración, "
        "y (c) límite de exposición total a renta variable según el Glide Path actuarial, "
        "que reduce gradualmente el riesgo conforme se aproxima el horizonte de liquidación. "
        "El retorno esperado y la matriz de covarianza se estiman con datos históricos anualizados a 252 días hábiles.",
        E
    ))
    story.append(Spacer(1, 0.15 * inch))

    metricas_data = [
        ['Retorno Anual', 'Volatilidad', 'Sharpe', 'Sortino'],
        [f"{ret_opt*100:.2f}%", f"{vol_opt*100:.2f}%", f"{sharpe_opt:.4f}", f"{sortino:.4f}"]
    ]
    t_met = Table(metricas_data, colWidths=[1.6 * inch] * 4)
    t_met.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANCO),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('BACKGROUND',    (0, 1), (-1, 1), GRIS_CLARO),
        ('FONTNAME',      (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 1), (-1, 1), 18),
        ('TEXTCOLOR',     (0, 1), (-1, 1), AZUL_OSCURO),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(t_met)
    story.append(Spacer(1, 0.08 * inch))

    story.append(_nota(
        f"Interpretación: el Ratio de Sharpe de {sharpe_opt:.4f} indica el exceso de retorno por unidad de riesgo total respecto a la tasa libre de riesgo. "
        f"El Ratio de Sortino de {sortino:.4f} penaliza exclusivamente la volatilidad negativa (downside), usando como MAR la tasa libre de riesgo diaria; "
        "valores superiores al Sharpe sugieren que el portafolio genera asimetrías positivas en su distribución de retornos.",
        E
    ))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Distribución Óptima del Capital", E['subseccion']))
    df_pesos = pd.DataFrame({
        'Activo':   tickers,
        'Peso (%)': (pesos_opt * 100).round(2)
    }).sort_values('Peso (%)', ascending=False)

    pesos_data = [['Activo', 'Peso (%)', 'Asignación visual']]
    for _, row in df_pesos.iterrows():
        barra = '█' * max(1, int(row['Peso (%)'] / 3))
        pesos_data.append([row['Activo'], f"{row['Peso (%)']:.2f}%", barra])
    story.append(_tabla_estilo(pesos_data, [1.5 * inch, 1.2 * inch, 4 * inch]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_nota(
        "Los pesos representan la fracción del capital total asignada a cada activo en el portafolio óptimo. "
        "Los activos clasificados como refugio (TLT, GLD, IEF, AGG, entre otros) están sujetos al límite del Glide Path: "
        "su peso combinado máximo aumenta conforme el horizonte de inversión es más largo, "
        "protegiendo el capital en la fase de acumulación tardía.",
        E
    ))

    if fig_markowitz:
        story.append(Spacer(1, 0.15 * inch))
        story.append(KeepTogether([
            Paragraph("Frontera Eficiente de Markowitz", E['subseccion']),
            Spacer(1, 0.06 * inch),
            _nota(
                f"Cada punto representa uno de los {num_sims:,} portafolios aleatorios simulados mediante Monte Carlo sobre el espacio de pesos posibles. "
                "El color codifica el Ratio de Sharpe (escala Viridis: oscuro = bajo, amarillo = alto). "
                "La estrella roja marca el portafolio óptimo identificado por SLSQP, que maximiza el Sharpe "
                "dentro de las restricciones definidas — no necesariamente coincide con el punto más alto de la nube, "
                "ya que el optimizador opera bajo las restricciones de concentración configuradas.",
                E
            ),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_markowitz, h_inch=3.0),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — BACKTESTING
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion(f"2. Backtesting Histórico — GaLa vs {benchmark_ticker}", E['seccion'])

    story.append(_nota(
        "Método: Backtesting Walk-Forward sin look-ahead bias. "
        "Los pesos se recalculan trimestralmente (cada 63 días hábiles) usando exclusivamente los datos históricos "
        "disponibles hasta la fecha de cada decisión — nunca información futura. "
        "En cada ventana de entrenamiento (252 días previos), el optimizador SLSQP reconstruye el portafolio óptimo. "
        "Si el Modelo Oculto de Markov detecta régimen de tensión en el mercado, la exposición a renta variable "
        "se reduce automáticamente a 0% hasta que el régimen se normaliza. "
        "Los retornos reportados son netos de comisiones operativas, calculadas sobre el turnover de cada rebalanceo.",
        E
    ))
    story.append(Spacer(1, 0.12 * inch))

    bt_data = [
        ['Métrica', 'GaLa', benchmark_ticker, 'Ventaja GaLa'],
        ['CAGR',
         f"{metricas_bt['cagr_port']*100:.2f}%",
         f"{metricas_bt['cagr_bench']*100:.2f}%",
         f"{(metricas_bt['cagr_port']-metricas_bt['cagr_bench'])*100:+.2f}%"],
        ['Volatilidad',
         f"{metricas_bt['vol_port']*100:.2f}%",
         f"{metricas_bt['vol_bench']*100:.2f}%",
         f"{(metricas_bt['vol_bench']-metricas_bt['vol_port'])*100:+.2f}%"],
        ['Sharpe',
         f"{metricas_bt['sharpe_port']:.4f}",
         f"{metricas_bt['sharpe_bench']:.4f}",
         f"{metricas_bt['sharpe_port']-metricas_bt['sharpe_bench']:+.4f}"],
        ['Sortino',
         f"{metricas_bt['sortino_port']:.4f}",
         f"{metricas_bt['sortino_bench']:.4f}",
         f"{metricas_bt['sortino_port']-metricas_bt['sortino_bench']:+.4f}"],
        ['Max Drawdown',
         f"{metricas_bt['mdd_port']*100:.2f}%",
         f"{metricas_bt['mdd_bench']*100:.2f}%",
         f"{(metricas_bt['mdd_bench']-metricas_bt['mdd_port'])*100:+.2f}%"],
        ['Calmar Ratio',
         f"{metricas_bt['calmar_port']:.4f}",
         f"{metricas_bt['calmar_bench']:.4f}",
         f"{metricas_bt['calmar_port']-metricas_bt['calmar_bench']:+.4f}"],
        ['Alpha (Jensen)', f"{metricas_bt['alpha']*100:.2f}%", '—', '—'],
        ['Beta',           f"{metricas_bt['beta']:.4f}", '1.0000', '—'],
    ]
    t_bt = Table(bt_data, colWidths=[1.8 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t_bt.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANCO),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TEXTCOLOR',     (3, 1), (3, -1), VERDE),
        ('FONTNAME',      (3, 1), (3, -1), 'Helvetica-Bold'),
    ]))
    story.append(t_bt)
    story.append(Spacer(1, 0.08 * inch))
    story.append(_nota(
        f"CAGR (Compound Annual Growth Rate): rendimiento anualizado compuesto del período completo. "
        f"El Alpha de Jensen de {metricas_bt['alpha']*100:.2f}% representa el retorno excedente generado "
        f"por encima de lo que predice el modelo CAPM dado un Beta de {metricas_bt['beta']:.4f} respecto a {benchmark_ticker}. "
        f"El Calmar Ratio expresa la eficiencia del retorno respecto al peor escenario histórico: "
        f"un valor superior a 1.0 indica que el CAGR supera en magnitud al Maximum Drawdown.",
        E
    ))

    if fig_bt:
        story.append(KeepTogether([
            Spacer(1, 0.2 * inch),
            Paragraph("Curva de Equity — Motor GaLa vs Benchmark", E['subseccion']),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_bt, h_inch=2.8),
        ]))

    if fig_anuales:
        story.append(KeepTogether([
            Spacer(1, 0.2 * inch),
            Paragraph("Retornos Anuales Comparativos", E['subseccion']),
            Spacer(1, 0.06 * inch),
            _nota(
                "Retorno total de cada año calendario, calculado como el producto acumulado de los retornos diarios "
                "dentro de ese período. La comparación año a año revela la consistencia de la estrategia "
                "frente al benchmark en distintos regímenes de mercado.",
                E
            ),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_anuales, h_inch=2.5),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — RIESGO INSTITUCIONAL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("3. Métricas de Riesgo Institucional", E['seccion'])

    story.append(_nota(
        "Las métricas de riesgo se calculan sobre la serie de retornos diarios del portafolio óptimo, "
        "construida como el producto punto entre los pesos SLSQP y la matriz de retornos históricos de cada activo. "
        "Esto refleja el comportamiento real que habría tenido la cartera con los pesos fijos óptimos "
        "a lo largo del período de análisis.",
        E
    ))
    story.append(Spacer(1, 0.12 * inch))

    riesgo_data = [
        ['Métrica', 'Valor (%)', f'Pérdida diaria (${capital_riesgo:,} USD)'],
        ['VaR 95% Histórico',
         f"{var_cvar['VaR_95_hist']*100:.2f}%",
         f"${abs(var_cvar['VaR_95_hist'])*capital_riesgo:,.0f}"],
        ['VaR 99% Histórico',
         f"{var_cvar['VaR_99_hist']*100:.2f}%",
         f"${abs(var_cvar['VaR_99_hist'])*capital_riesgo:,.0f}"],
        ['CVaR 95% (Expected Shortfall)',
         f"{var_cvar['CVaR_95']*100:.2f}%",
         f"${abs(var_cvar['CVaR_95'])*capital_riesgo:,.0f}"],
        ['CVaR 99%',
         f"{var_cvar['CVaR_99']*100:.2f}%",
         f"${abs(var_cvar['CVaR_99'])*capital_riesgo:,.0f}"],
        ['Maximum Drawdown',
         f"{max_dd*100:.2f}%",
         f"${abs(max_dd)*capital_riesgo:,.0f}"],
    ]
    story.append(_tabla_estilo(riesgo_data, [2.8 * inch, 1.5 * inch, 2.4 * inch]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(_nota(
        "VaR histórico: percentil empírico de la distribución de retornos diarios (no asume normalidad). "
        "El VaR 95% es el percentil 5 de la distribución — en el 95% de los días el portafolio no pierde más de esta cantidad. "
        "CVaR (Expected Shortfall): promedio de los retornos que sí superan el VaR, es decir, "
        "la pérdida esperada en el peor 5% o 1% de los días. "
        "Reguladores como Basilea III y EIOPA (Solvencia II) prefieren el CVaR por capturar "
        "el riesgo de cola que el VaR ignora.",
        E
    ))
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        f"Período del Maximum Drawdown: {inicio_dd.strftime('%b %Y')} → "
        f"{fin_dd.strftime('%b %Y')} ({duracion_dd} días / {duracion_dd//30} meses)",
        E['normal']
    ))

    if fig_var:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Distribución de Retornos Diarios — VaR y CVaR", E['subseccion']),
            Spacer(1, 0.06 * inch),
            _nota(
                "Histograma empírico de todos los retornos diarios del portafolio en el período analizado. "
                "Las líneas verticales marcan los umbrales de pérdida: roja = VaR 95%, naranja = CVaR 95%, magenta = VaR 99%. "
                "Una distribución con cola izquierda extendida (asimetría negativa) indica mayor frecuencia "
                "de pérdidas extremas de lo que predice una distribución normal.",
                E
            ),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_var, h_inch=2.7),
        ]))

    if fig_dd:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Curva de Drawdown Histórico", E['subseccion']),
            Spacer(1, 0.06 * inch),
            _nota(
                "El drawdown diario se calcula como la caída porcentual desde el máximo acumulado previo "
                "hasta el valor actual del portafolio: DD(t) = (P(t) − max P(τ≤t)) / max P(τ≤t). "
                f"El período de recuperación completa del máximo drawdown fue de {duracion_dd} días "
                f"({duracion_dd//30} meses), entre {inicio_dd.strftime('%b %Y')} y {fin_dd.strftime('%b %Y')}.",
                E
            ),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_dd, h_inch=2.5),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 5 — STRESS TESTING + CORRELACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("4. Stress Testing — Escenarios Históricos", E['seccion'])

    story.append(_nota(
        "Método: cada escenario aplica una ventana histórica real de fechas específicas sobre los retornos del portafolio. "
        "No se usan shocks estimados ni supuestos: se toman los retornos diarios reales de cada activo "
        "durante el período de la crisis y se calcula el retorno acumulado del portafolio con los pesos óptimos actuales. "
        "Los activos no presentes en los datos históricos de la crisis se excluyen y los pesos restantes "
        "se renormalizan para mantener la suma en 1. "
        "Ventanas utilizadas: COVID Crash (Feb–Mar 2020), Bear Market 2022 (Ene–Oct 2022), "
        "Crisis Financiera 2008 (Sep 2008–Mar 2009), Inflación & Subida de Tasas 2022 (Mar–Jun 2022), "
        "Corrección Post-COVID (Sep 2020).",
        E
    ))
    story.append(Spacer(1, 0.12 * inch))

    stress_data = [['Escenario', 'Impacto (%)', 'Pérdida estimada (USD)']]
    for _, row in df_stress.iterrows():
        stress_data.append([
            row['Escenario'],
            f"{row['Pérdida (%)']:.1f}%",
            f"${abs(row['Pérdida (USD)']):,.0f}"
        ])
    t_stress = Table(stress_data, colWidths=[3.2 * inch, 1.5 * inch, 2.0 * inch])
    t_stress.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANCO),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TEXTCOLOR',     (1, 1), (1, -1), ROJO),
        ('FONTNAME',      (1, 1), (1, -1), 'Helvetica-Bold'),
    ]))
    story.append(t_stress)

    if fig_stress:
        story.append(KeepTogether([
            Spacer(1, 0.15 * inch),
            Paragraph("Impacto por Escenario — Visualización", E['subseccion']),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_stress, h_inch=2.7),
        ]))

    if fig_corr:
        story.append(KeepTogether([
            Spacer(1, 0.25 * inch),
            Paragraph("5. Correlación Dinámica Rolling — 60 días", E['seccion']),
            HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=8),
            _nota(
                "La correlación rolling se calcula como el coeficiente de Pearson entre los retornos diarios "
                "de dos activos en una ventana móvil de 60 días hábiles. "
                "Valores superiores a 0.6 entre activos que deberían estar descorrelacionados (ej. renta variable vs bonos) "
                "señalan períodos de «risk-off» donde la diversificación colapsa — "
                "exactamente los momentos de mayor necesidad de protección. "
                "Valores negativos sostenidos por debajo de −0.6 confirman cobertura efectiva.",
                E
            ),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_corr, h_inch=2.7),
        ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 6 — MONTE CARLO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3 * inch))
    story += _seccion("6. Proyección de Capital — Monte Carlo", E['seccion'])

    story.append(_nota(
        f"Método: Movimiento Browniano Geométrico mensual con shocks de distribución t de Student "
        f"calibrada sobre los retornos históricos reales del portafolio (gl={df_t:.1f}). "
        f"A diferencia de la distribución normal, la t de Student con grados de libertad bajos "
        f"genera colas pesadas (fat tails) que capturan la mayor frecuencia de eventos extremos "
        f"observada en mercados financieros reales. "
        f"Se simularon {num_sims:,} trayectorias independientes durante {horizonte_años * 12} meses. "
        f"La aportación periódica de ${aportacion_mensual:,} MXN se inyecta al inicio de cada período "
        f"antes de aplicar el shock estocástico, modelando el efecto real de las aportaciones sobre la base compuesta.",
        E
    ))
    story.append(Spacer(1, 0.12 * inch))

    mc_data = [
        ['Escenario', 'Capital Final (MXN)', 'Crecimiento total'],
        ['Adverso (P5)',         f"${p5_final:,.0f}",  f"{((p5_final/capital_inicial)-1)*100:.1f}%"],
        ['Mod. Adverso (P25)',   f"${p25_final:,.0f}", f"{((p25_final/capital_inicial)-1)*100:.1f}%"],
        ['Base (P50)',           f"${p50_final:,.0f}", f"{((p50_final/capital_inicial)-1)*100:.1f}%"],
        ['Mod. Favorable (P75)', f"${p75_final:,.0f}", f"{((p75_final/capital_inicial)-1)*100:.1f}%"],
        ['Favorable (P95)',      f"${p95_final:,.0f}", f"{((p95_final/capital_inicial)-1)*100:.1f}%"],
    ]
    t_mc = Table(mc_data, colWidths=[2.0 * inch, 2.5 * inch, 2.2 * inch])
    t_mc.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0, 0), (-1, 0), BLANCO),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 10),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND',    (0, 1), (-1, 1), colors.HexColor('#fff5f5')),
        ('BACKGROUND',    (0, 2), (-1, 2), colors.HexColor('#fffaf0')),
        ('BACKGROUND',    (0, 3), (-1, 3), colors.HexColor('#f0fff4')),
        ('BACKGROUND',    (0, 4), (-1, 4), colors.HexColor('#f5faff')),
        ('BACKGROUND',    (0, 5), (-1, 5), colors.HexColor('#ebf8ff')),
        ('TEXTCOLOR',     (2, 1), (2, 1), ROJO),
        ('TEXTCOLOR',     (2, 2), (2, 2), colors.HexColor('#b45309')),
        ('TEXTCOLOR',     (2, 3), (2, 3), VERDE),
        ('TEXTCOLOR',     (2, 4), (2, 4), colors.HexColor('#1d4ed8')),
        ('TEXTCOLOR',     (2, 5), (2, 5), AZUL_ACENTO),
        ('FONTNAME',      (1, 1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_mc)
    story.append(Spacer(1, 0.08 * inch))
    story.append(_nota(
        "Los percentiles representan los valores finales de capital en los que termina ese porcentaje de simulaciones. "
        f"El escenario base (P50) es la mediana: la mitad de las {num_sims:,} trayectorias terminan por debajo y la mitad por encima. "
        "El rango P25–P75 constituye el intervalo intercuartílico — la zona de mayor probabilidad de ocurrencia. "
        "El rango P5–P95 captura el 90% central de los resultados, dejando un 5% de escenarios "
        "más adversos y 5% más favorables fuera del intervalo reportado.",
        E
    ))

    if fig_mc:
        story.append(KeepTogether([
            Spacer(1, 0.2 * inch),
            Paragraph(f"Trayectorias de Capital — {num_sims:,} simulaciones", E['subseccion']),
            Spacer(1, 0.08 * inch),
            _fig_a_imagen(fig_mc, h_inch=3.2),
        ]))

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 7 — SCREENING (OPCIONAL)
    # ══════════════════════════════════════════════════════════════════════════
    if df_screening is not None and not df_screening.empty:
        story.append(PageBreak())
        story.append(Spacer(1, 0.3 * inch))
        story += _seccion("7. Screening Fundamental — Selección de Activos", E['seccion'])

        story.append(_nota(
            "Proceso de selección en dos etapas. "
            "Etapa 1 — Filtro fundamental: se descargan métricas en tiempo real de Yahoo Finance y se aplican "
            "umbrales mínimos de capitalización de mercado, margen de beneficio y ROE, "
            "y máximos de P/E y ratio Deuda/Capital, para excluir empresas con fundamentos débiles o sobrevaloradas. "
            "Etapa 2 — Clustering K-Means: los activos filtrados se estandarizan (StandardScaler) "
            "y se agrupan por similitud de perfil cuantitativo. "
            "Se selecciona el representante de mayor Profit Margin por cada cluster, "
            "garantizando diversificación sectorial real y no solo nominal.",
            E
        ))
        story.append(Spacer(1, 0.1 * inch))

        cols_show = ['Ticker', 'Nombre', 'Sector', 'Market Cap (B)',
                     'P/E Ratio', 'Profit Margin %', 'ROE %']
        cols_disp = [c for c in cols_show if c in df_screening.columns]

        headers_cortos = {
            'Ticker':         'Ticker',
            'Nombre':         'Nombre',
            'Sector':         'Sector',
            'Market Cap (B)': 'Mkt Cap\n(B USD)',
            'P/E Ratio':      'P/E',
            'Profit Margin %':'Margen\n(%)',
            'ROE %':          'ROE\n(%)',
        }
        formatos = {
            'Market Cap (B)':  lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
            'P/E Ratio':       lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
            'Profit Margin %': lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
            'ROE %':           lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
        }

        def formatear(col, val):
            try:
                return formatos[col](val) if col in formatos else str(val)
            except (ValueError, TypeError):
                return '—'

        scr_data = [[headers_cortos[c] for c in cols_disp]] + [
            [formatear(c, str(row[c])) for c in cols_disp]
            for _, row in df_screening.iterrows()
        ]
        pesos_cols  = {'Ticker': 1.0, 'Nombre': 3.5, 'Sector': 2.5,
                       'Market Cap (B)': 1.2, 'P/E Ratio': 0.9,
                       'Profit Margin %': 1.2, 'ROE %': 0.9}
        peso_total  = sum(pesos_cols[c] for c in cols_disp)
        anchos      = [(pesos_cols[c] / peso_total) * PAGE_W for c in cols_disp]

        t_scr = Table(scr_data, colWidths=anchos)
        t_scr.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), AZUL_OSCURO),
            ('TEXTCOLOR',     (0, 0), (-1, 0), BLANCO),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, -1), 8),
            ('LEADING',       (0, 0), (-1, -1), 10),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d8e8')),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('WORDWRAP',      (0, 0), (-1, -1), True),
        ]))
        story.append(t_scr)

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
