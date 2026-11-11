import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def format_currency(val):
    if val is None:
        return "$0"
    return f"${val:,.0f}".replace(",", ".")

def generate_client_pdf(
    client: dict, 
    review_date_str: str, 
    color_filter: str = 'all', 
    company_name: str = "AGROINDUSTRIALES CAÑAVERALEJO S.A.S"
) -> bytes:
    """
    Generates a PDF account statement for a specific client,
    optionally filtered by color ('all', 'red', 'yellow', 'green').
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        alignment=1 # Center
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#16A34A'),
        alignment=1
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#475569')
    )
    meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )
    cell_style = ParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )
    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )
    cell_center = ParagraphStyle(
        'CellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.HexColor('#1E293B')
    )
    cell_right = ParagraphStyle(
        'CellRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        alignment=2,
        textColor=colors.HexColor('#1E293B')
    )
    cell_right_bold = ParagraphStyle(
        'CellRightBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=colors.HexColor('#0F172A')
    )

    try:
        f_date = datetime.strptime(review_date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        f_date = review_date_str

    # Determine filter title and subset
    invoices = client.get('invoices', [])
    if color_filter == 'red':
        target_invoices = [inv for inv in invoices if inv.get('alert_level') == 'red']
        filter_badge = "FACTURAS MAYOR A 60 DÍAS (ROJO)"
        badge_bg = colors.HexColor('#FEE2E2')
        badge_txt = colors.HexColor('#991B1B')
    elif color_filter == 'yellow':
        target_invoices = [inv for inv in invoices if inv.get('alert_level') == 'yellow']
        filter_badge = "FACTURAS DE 31 A 60 DÍAS (AMARILLO)"
        badge_bg = colors.HexColor('#FEF3C7')
        badge_txt = colors.HexColor('#854D0E')
    elif color_filter == 'green':
        target_invoices = [inv for inv in invoices if inv.get('alert_level') == 'green']
        filter_badge = "FACTURAS DE 1 A 30 DÍAS (VERDE)"
        badge_bg = colors.HexColor('#DCFCE7')
        badge_txt = colors.HexColor('#166534')
    else:
        target_invoices = invoices
        filter_badge = "TODAS LAS FACTURAS PENDIENTES"
        badge_bg = colors.HexColor('#E2E8F0')
        badge_txt = colors.HexColor('#1E293B')

    story = []

    # 1. Company Header
    story.append(Paragraph(company_name, title_style))
    story.append(Paragraph("ESTADO DE CUENTA DE CARTERA", subtitle_style))
    story.append(Spacer(1, 10))

    # 2. Client Metadata Box Table
    meta_data = [
        [
            Paragraph("<b>Cliente:</b>", meta_label),
            Paragraph(client.get('name', ''), meta_val),
            Paragraph("<b>Fecha de Corte:</b>", meta_label),
            Paragraph(f_date, meta_val)
        ],
        [
            Paragraph("<b>NIT:</b>", meta_label),
            Paragraph(client.get('nit', ''), meta_val),
            Paragraph("<b>Ciudad:</b>", meta_label),
            Paragraph(client.get('city', 'Bogotá'), meta_val)
        ],
        [
            Paragraph("<b>Teléfono:</b>", meta_label),
            Paragraph(client.get('phone', 'N/A'), meta_val),
            Paragraph("<b>Filtro Reporte:</b>", meta_label),
            Paragraph(f"<b>{filter_badge}</b>", ParagraphStyle('Filt', parent=meta_val, textColor=badge_txt))
        ]
    ]
    meta_table = Table(meta_data, colWidths=[65, 220, 85, 170])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Invoices Table
    table_headers = [
        Paragraph("<b>N° Factura</b>", cell_bold),
        Paragraph("<b>Fec. Emisión</b>", cell_center),
        Paragraph("<b>Fec. Vencimiento</b>", cell_center),
        Paragraph("<b>Días Mora</b>", cell_center),
        Paragraph("<b>Rango / Alerta</b>", cell_center),
        Paragraph("<b>Plazo</b>", cell_center),
        Paragraph("<b>Vlr. Factura</b>", cell_right_bold),
        Paragraph("<b>Saldo a Pagar</b>", cell_right_bold)
    ]

    table_rows = [table_headers]
    shown_total = 0.0

    for inv in target_invoices:
        dias = inv.get('dias_vencida', 0)
        level = inv.get('alert_level', 'green')
        saldo = inv.get('saldo', 0.0)
        shown_total += saldo

        if level == 'red':
            alerta_text = "Mayor a 90d (ROJO)"
        elif level == 'yellow':
            alerta_text = "61 a 89d (AMARILLO)"
        else:
            alerta_text = "1 a 59d (VERDE)"

        row = [
            Paragraph(inv.get('doc_no', ''), cell_bold),
            Paragraph(inv.get('fec_doc', ''), cell_center),
            Paragraph(inv.get('fec_vcto', ''), cell_center),
            Paragraph(f"<b>{dias} d</b>", cell_center),
            Paragraph(alerta_text, cell_center),
            Paragraph(f"{inv.get('plazo', 1)} d", cell_center),
            Paragraph(format_currency(inv.get('vlr_doc', 0)), cell_right),
            Paragraph(format_currency(saldo), cell_right_bold)
        ]
        table_rows.append(row)

    if not target_invoices:
        table_rows.append([
            Paragraph("No registra facturas pendientes en este rango de vencimiento.", cell_style),
            "", "", "", "", "", "", ""
        ])

    # Footer total row
    total_row = [
        Paragraph("<b>TOTAL MOSTRADO EN ESTE REPORTE:</b>", cell_bold),
        "", "", "", "", "", "",
        Paragraph(f"<b>{format_currency(shown_total)}</b>", ParagraphStyle('TotG', parent=cell_right_bold, textColor=colors.HexColor('#0F172A'), fontSize=9.5))
    ]
    table_rows.append(total_row)

    col_widths = [80, 60, 65, 50, 95, 40, 75, 75]
    inv_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
    
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ('SPAN', (0, -1), (6, -1)), # Span total label
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
        ('TOPPADDING', (0, -1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
    ]

    # Style header text to white
    for c_idx in range(len(table_headers)):
        table_styles.append(('TEXTCOLOR', (c_idx, 0), (c_idx, 0), colors.white))

    # Row colors based on alert level
    for idx, inv in enumerate(target_invoices, 1):
        level = inv.get('alert_level', 'green')
        if level == 'red':
            table_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#FFF5F5')))
        elif level == 'yellow':
            table_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#FFFBEB')))
        else:
            table_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#F0FDF4')))
        table_styles.append(('TOPPADDING', (0, idx), (-1, idx), 3))
        table_styles.append(('BOTTOMPADDING', (0, idx), (-1, idx), 3))

    inv_table.setStyle(TableStyle(table_styles))
    story.append(inv_table)
    story.append(Spacer(1, 14))

    # 4. Mandatory Total Portfolio Breakdown Box
    tot_general = client.get('total_saldo', 0.0)
    red_tot = client.get('red_saldo', 0.0)
    red_cnt = client.get('red_count', 0)
    yel_tot = client.get('yellow_saldo', 0.0)
    yel_cnt = client.get('yellow_count', 0)
    grn_tot = client.get('green_saldo', 0.0)
    grn_cnt = client.get('green_count', 0)

    summary_box_data = [
        [
            Paragraph("<b>RESUMEN TOTAL DE LA CARTERA DEL CLIENTE</b>", section_title),
            Paragraph(f"<b>SALDO TOTAL GENERAL: {format_currency(tot_general)}</b>", ParagraphStyle('TotB', parent=section_title, alignment=2, textColor=colors.HexColor('#0F172A')))
        ],
        [
            Paragraph(f"• Facturas mayor a 60 días: <b>{format_currency(red_tot)}</b> ({red_cnt} facturas)", cell_style),
            Paragraph(f"• Facturas de 31 a 60 días: <b>{format_currency(yel_tot)}</b> ({yel_cnt} facturas)", cell_style)
        ],
        [
            Paragraph(f"• Facturas de 1 a 30 días: <b>{format_currency(grn_tot)}</b> ({grn_cnt} facturas)", cell_style),
            Paragraph("Cupo asignado: " + format_currency(client.get('credit_limit', 0)), cell_style)
        ]
    ]
    summary_table = Table(summary_box_data, colWidths=[270, 270])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#0F172A')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # 5. Formal closing note
    closing_text = Paragraph(
        "Por favor envíenos el soporte de pago o la fecha programada al número de contacto respectivo. "
        "Agradecemos su puntualidad y confianza en nuestros servicios.",
        ParagraphStyle('Close', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, leading=11, textColor=colors.HexColor('#475569'), alignment=1)
    )
    story.append(closing_text)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
