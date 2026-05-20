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
    TableStyle, HRFlowable, PageBreak, Image, CondPageBreak
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


def _estilos():
    estilos = {
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
        'resumen': ParagraphStyle(
            'resumen', fontSize=10, textColor=AZUL_OSCURO,
            fontName='Helvetica', spaceAfter=6, leading=16,
            leftIndent=10, rightIndent=10
        ),
        'pie': ParagraphStyle(
            'pie', fontSize=7, textColor=GRIS_TEXTO,
            fontName='Helvetica', alignment=TA_CENTER
        ),
    }
    return estilos

import plotly.io as pio

import io
from reportlab.platypus import Image

def _fig_a_imagen(fig, width=500, height=300):
    """
    Exporta la figura de Plotly a PNG y la convierte en un 
    objeto 'Image' (Flowable) compatible con ReportLab.
    """
    # 1. Tomamos la captura de la gráfica
    img_bytes = fig.to_image(format="png")
    
    # 2. La guardamos en la memoria temporal
    buffer = io.BytesIO(img_bytes)
    
    # 3. ¡LA CLAVE! Envolvemos la memoria en un elemento visual de ReportLab
    return Image(buffer, width=width, height=height)


def _tabla_estilo(data, col_widths, header_color=None):
    """Genera tabla con estilo institucional estándar."""
    header_color = header_color or AZUL_OSCURO
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), header_color),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ALIGN',         (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [BLANCO, GRIS_CLARO]),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
    ]))
    return t


def _on_page(canvas, doc):
    w, h = letter
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, h, fill=True, stroke=False)
    else:
        # Header
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, h-40, w, 40, fill=True, stroke=False)
        canvas.setFont('Helvetica-Bold', 9)
        canvas.setFillColor(BLANCO)
        canvas.drawString(30, h-25, "🛡️  MOTOR CUANTITATIVO GaLa")
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(w-30, h-25, f"Página {doc.page}")
        # Footer
        canvas.setFillColor(AZUL_OSCURO)
        canvas.rect(0, 0, w, 25, fill=True, stroke=False)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#8899bb'))
        canvas.drawString(30, 8, "Documento confidencial — Motor GaLa © 2026")
        canvas.drawRightString(w-30, 8, datetime.now().strftime("%d/%m/%Y %H:%M"))
    canvas.restoreState()


def generar_reporte(
    # Portafolio
    tickers, pesos_opt, ret_opt, vol_opt, sharpe_opt,
    sortino, desv_down, df_t,
    # Riesgo
    var_cvar, max_dd, duracion_dd, inicio_dd, fin_dd,
    df_stress, capital_riesgo,
    # Monte Carlo
    p5_final, p50_final, p95_final,
    horizonte_años, capital_inicial, aportacion_mensual,
    # Backtesting
    metricas_bt, benchmark_ticker,
    # Screening (opcional)
    df_screening=None,
    # Figuras
    fig_markowitz=None, fig_mc=None, fig_var=None,
    fig_dd=None, fig_stress=None, fig_bt=None,
    fig_anuales=None, fig_corr=None,
) -> bytes:

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.6*inch, bottomMargin=0.5*inch
    )
    E = _estilos()
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 1 — PORTADA
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 1.6*inch))
    story.append(Paragraph("MOTOR CUANTITATIVO GaLa", E['titulo']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        
        "Reporte Institucional de Gestión de Capital y Riesgo",
        E['subtitulo']
    ))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        datetime.now().strftime("%d de %B de %Y"),
        E['subtitulo']
    ))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        f"Universo analizado: {' | '.join(tickers)}",
        E['subtitulo']
    ))
    story.append(Spacer(1, 0.8*inch))

    # Resumen ejecutivo en portada
    veredicto_sharpe = "sólido" if sharpe_opt > 1 else "moderado" if sharpe_opt > 0.5 else "bajo"
    veredicto_dd = "controlado" if abs(max_dd) < 0.15 else "elevado"
    resumen_ejecutivo = (
        f"El portafolio óptimo identificado por Motor GaLa presenta un retorno esperado anual "
        f"de {ret_opt*100:.2f}% con una volatilidad de {vol_opt*100:.2f}%, "
        f"generando un Ratio de Sharpe {veredicto_sharpe} de {sharpe_opt:.4f}. "
        f"El Maximum Drawdown histórico es {veredicto_dd} en {abs(max_dd)*100:.2f}%, "
        f"con una duración de {duracion_dd} días. "
        f"El modelo de riesgo fue calibrado con distribución t de Student "
        f"(gl={df_t:.1f}), capturando fat tails propias de mercados financieros reales."
    )
    story.append(Paragraph(resumen_ejecutivo, ParagraphStyle(
        'resumen_portada', fontSize=10, textColor=GRIS_CLARO,
        fontName='Helvetica', alignment=TA_CENTER,
        spaceAfter=6, leading=18,
        leftIndent=30, rightIndent=30
    )))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 2 — PORTAFOLIO ÓPTIMO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("1. Portafolio Óptimo — Max Sharpe", E['seccion']))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10))

    # Métricas principales
    metricas_data = [
        ['Retorno Anual', 'Volatilidad', 'Sharpe', 'Sortino'],
        [f"{ret_opt*100:.2f}%", f"{vol_opt*100:.2f}%",
         f"{sharpe_opt:.4f}", f"{sortino:.4f}"]
    ]
    t_met = Table(metricas_data, colWidths=[1.6*inch]*4)
    t_met.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0), 9),
        ('BACKGROUND',    (0,1), (-1,1), GRIS_CLARO),
        ('FONTNAME',      (0,1), (-1,1), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,1), (-1,1), 18),
        ('TEXTCOLOR',     (0,1), (-1,1), AZUL_OSCURO),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_met)
    story.append(Spacer(1, 0.15*inch))

    # Tabla de pesos
    story.append(Paragraph("Distribución Óptima del Capital", E['subseccion']))
    df_pesos = pd.DataFrame({
        'Activo': tickers,
        'Peso (%)': (pesos_opt * 100).round(2)
    }).sort_values('Peso (%)', ascending=False)

    pesos_data = [['Activo', 'Peso (%)', 'Asignación visual']]
    for _, row in df_pesos.iterrows():
        barra = '█' * max(1, int(row['Peso (%)'] / 3))
        pesos_data.append([row['Activo'], f"{row['Peso (%)']:.2f}%", barra])

    story.append(_tabla_estilo(pesos_data, [1.5*inch, 1.2*inch, 4*inch]))

    # Frontera eficiente
    story.append(Spacer(1, 0.3*inch))
    if fig_markowitz:
        story.append(Spacer(1, 0.1*inch))
        story.append(_fig_a_imagen(fig_markowitz, height=300))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 3 — BACKTESTING
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        f"2. Backtesting Histórico — GaLa vs {benchmark_ticker}",
        E['seccion']
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10))

    bt_data = [
        ['Métrica', f'GaLa', f'{benchmark_ticker}', 'Ventaja GaLa'],
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
        ['Alpha (Jensen)',
         f"{metricas_bt['alpha']*100:.2f}%", '—', '—'],
        ['Beta',
         f"{metricas_bt['beta']:.4f}", '1.0000', '—'],
    ]

    t_bt = Table(bt_data, colWidths=[1.8*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    t_bt.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ALIGN',         (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [BLANCO, GRIS_CLARO]),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('TEXTCOLOR',     (3,1), (3,-1), VERDE),
        ('FONTNAME',      (3,1), (3,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_bt)

    if fig_bt:
        story.append(Spacer(1, 0.1*inch))
        story.append(_fig_a_imagen(fig_bt, height=280))

    if fig_anuales:
        # El radar: Le exige al PDF 4 pulgadas libres. Si no las hay, corta la página aquí mismo.
        story.append(PageBreak())
        
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("Retornos Anuales Comparativos", E['subseccion']))
        story.append(_fig_a_imagen(fig_anuales, height=240))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 4 — RIESGO INSTITUCIONAL
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("3. Métricas de Riesgo Institucional", E['seccion']))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10))

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
    story.append(_tabla_estilo(riesgo_data, [2.8*inch, 1.5*inch, 2.4*inch]))
    story.append(Spacer(1, 0.08*inch))
    story.append(Paragraph(
        f"Período del Maximum Drawdown: {inicio_dd.strftime('%b %Y')} → "
        f"{fin_dd.strftime('%b %Y')} ({duracion_dd} días / {duracion_dd//30} meses)",
        E['normal']
    ))

    if fig_var:
        story.append(_fig_a_imagen(fig_var, height=260))

    if fig_dd:
        story.append(Paragraph("Curva de Drawdown Histórico", E['subseccion']))
        story.append(_fig_a_imagen(fig_dd, height=240))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 5 — STRESS TESTING + CORRELACIÓN
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("4. Stress Testing — Escenarios Históricos", E['seccion']))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10))

    stress_data = [['Escenario', 'Impacto (%)', 'Pérdida estimada (USD)']]
    for _, row in df_stress.iterrows():
        stress_data.append([
            row['Escenario'],
            f"{row['Pérdida (%)']:.1f}%",
            f"${abs(row['Pérdida (USD)']):,.0f}"
        ])

    t_stress = Table(stress_data, colWidths=[3.2*inch, 1.5*inch, 2*inch])
    t_stress.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('ALIGN',         (1,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [BLANCO, GRIS_CLARO]),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('TEXTCOLOR',     (1,1), (1,-1), ROJO),
        ('FONTNAME',      (1,1), (1,-1), 'Helvetica-Bold'),
    ]))
    story.append(t_stress)
    story.append(Spacer(1, 0.3*inch))
    if fig_stress:
        story.append(_fig_a_imagen(fig_stress, height=260))

    if fig_corr:
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("5. Correlación Dinámica Rolling 60 días", E['seccion']))
        story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=8))
        story.append(Paragraph(
            "La correlación dinámica permite identificar períodos donde los activos "
            "se mueven en conjunto, reduciendo los beneficios de diversificación. "
            "Valores superiores a 0.6 indican zona de riesgo de concentración.",
            E['normal']
        ))
        story.append(_fig_a_imagen(fig_corr, height=260))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 6 — PROYECCIÓN MONTE CARLO
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("6. Proyección de Capital — Monte Carlo", E['seccion']))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10))

    story.append(Paragraph(
        f"Horizonte: {horizonte_años} años  |  Capital inicial: ${capital_inicial:,} MXN  |  "
        f"Aportación periódica: ${aportacion_mensual:,} MXN  |  "
        f"Modelo: t de Student (gl={df_t:.1f})",
        E['normal']
    ))
    story.append(Spacer(1, 0.1*inch))

    mc_data = [
        ['Escenario', 'Capital Final (MXN)', 'Crecimiento total'],
        ['Pesimista (P5)',   f"${p5_final:,.0f}",
         f"{((p5_final/capital_inicial)-1)*100:.1f}%"],
        ['Base (P50)',       f"${p50_final:,.0f}",
         f"{((p50_final/capital_inicial)-1)*100:.1f}%"],
        ['Optimista (P95)', f"${p95_final:,.0f}",
         f"{((p95_final/capital_inicial)-1)*100:.1f}%"],
    ]

    t_mc = Table(mc_data, colWidths=[2*inch, 2.5*inch, 2.2*inch])
    t_mc.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), AZUL_OSCURO),
        ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 10),
        ('ALIGN',         (1,0), (-1,-1), 'CENTER'),
        ('BACKGROUND',    (0,1), (-1,1), colors.HexColor('#fff5f5')),
        ('BACKGROUND',    (0,2), (-1,2), colors.HexColor('#f0fff4')),
        ('BACKGROUND',    (0,3), (-1,3), colors.HexColor('#ebf8ff')),
        ('TEXTCOLOR',     (2,1), (2,1), ROJO),
        ('TEXTCOLOR',     (2,2), (2,2), VERDE),
        ('TEXTCOLOR',     (2,3), (2,3), AZUL_ACENTO),
        ('FONTNAME',      (1,1), (-1,-1), 'Helvetica-Bold'),
        ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#d0d8e8')),
        ('TOPPADDING',    (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_mc)

    if fig_mc:
        story.append(Spacer(1, 0.4*inch))
        story.append(_fig_a_imagen(fig_mc, height=300))

    # ══════════════════════════════════════════════════════════════════════════
    # PÁGINA 7 — SCREENING (OPCIONAL)
    # ══════════════════════════════════════════════════════════════════════════
    if df_screening is not None and not df_screening.empty:
        story.append(PageBreak())
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("7. Screening Fundamental — Selección de Activos", E['seccion']))
        story.append(HRFlowable(width="100%", thickness=1, color=AZUL_ACENTO, spaceAfter=10))
        story.append(Paragraph(
            "Los activos del portafolio fueron seleccionados mediante un proceso cuantitativo "
            "de dos etapas: filtro fundamental (Market Cap, Profit Margin, P/E, Deuda/Capital) "
            "seguido de clustering K-Means para garantizar diversificación por perfil.",
            E['normal']
        ))
        story.append(Spacer(1, 0.1*inch))

        cols_show = ['Ticker', 'Nombre', 'Sector', 'Market Cap (B)',
                     'P/E Ratio', 'Profit Margin %', 'ROE %']
        cols_disp = [c for c in cols_show if c in df_screening.columns]

        # Headers abreviados para evitar desbordamiento
        headers_cortos = {
            'Ticker': 'Ticker',
            'Nombre': 'Nombre',
            'Sector': 'Sector',
            'Market Cap (B)': 'Mkt Cap\n(B USD)',
            'P/E Ratio': 'P/E',
            'Profit Margin %': 'Margen\n(%)',
            'ROE %': 'ROE\n(%)'
        }

        # Formatos numéricos por columna
        formatos = {
            'Market Cap (B)': lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
            'P/E Ratio':      lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
            'Profit Margin %':lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
            'ROE %':          lambda v: f"{float(v):.1f}" if v not in ('nan', '', 'None') else '—',
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

        pesos_cols = {
            'Ticker': 1.0,
            'Nombre': 3.5,
            'Sector': 2.5,
            'Market Cap (B)': 1.2,
            'P/E Ratio': 0.9,
            'Profit Margin %': 1.2,
            'ROE %': 0.9
        }

        peso_total = sum(pesos_cols[c] for c in cols_disp)
        anchos = [(pesos_cols[c] / peso_total) * 6.5 * inch for c in cols_disp]

        t_scr = Table(scr_data, colWidths=anchos)
        t_scr.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), AZUL_OSCURO),
            ('TEXTCOLOR',     (0,0), (-1,0), BLANCO),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,-1), 8),       # fuente más pequeña
            ('LEADING',       (0,0), (-1,-1), 10),       # interlineado ajustado
            ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),   # Nombre y Sector alineados a la izquierda
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [BLANCO, GRIS_CLARO]),
            ('GRID',          (0,0), (-1,-1), 0.5, colors.HexColor('#d0d8e8')),
            ('TOPPADDING',    (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('WORDWRAP',      (0,0), (-1,-1), True),
        ]))
        story.append(t_scr)

    # ── Nota legal ─────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4*inch))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS_TEXTO))
    story.append(Spacer(1, 0.1*inch))
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
