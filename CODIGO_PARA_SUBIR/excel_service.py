import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def generate_excel_cartera(data: dict):
    """
    Generates a professionally styled Excel file containing summary and detailed invoice tables,
    strictly formatted in the 3 designated colors: Red, Yellow, Green.
    """
    wb = Workbook()
    
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    title_font = Font(name='Calibri', size=14, bold=True, color='1E293B')
    subtitle_font = Font(name='Calibri', size=10, italic=True, color='64748B')
    bold_font = Font(name='Calibri', size=11, bold=True)
    
    header_fill = PatternFill(start_color='1E293B', end_color='1E293B', fill_type='solid')
    alt_row_fill = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')
    total_fill = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')
    
    # 3 Designated Alert Fills & Fonts
    red_fill = PatternFill(start_color='FEE2E2', end_color='FEE2E2', fill_type='solid')
    yellow_fill = PatternFill(start_color='FEF3C7', end_color='FEF3C7', fill_type='solid')
    green_fill = PatternFill(start_color='DCFCE7', end_color='DCFCE7', fill_type='solid')

    red_text = Font(name='Calibri', size=11, color='991B1B', bold=True)
    yellow_text = Font(name='Calibri', size=11, color='854D0E', bold=True)
    green_text = Font(name='Calibri', size=11, color='166534', bold=True)
    
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # -------------------------------------------------------------
    # SHEET 1: Resumen por Cliente
    # -------------------------------------------------------------
    ws1 = wb.active
    ws1.title = "Resumen por Cliente"
    ws1.views.sheetView[0].showGridLines = True

    ws1['A1'] = f"{data['metadata']['company']} - CONTROL DE CARTERA"
    ws1['A1'].font = title_font
    ws1['A2'] = f"Fecha de Revisión: {data['summary']['review_date']} | Archivo: {data['metadata']['file_name']}"
    ws1['A2'].font = subtitle_font

    headers1 = [
        "NIT", "Razón Social / Cliente", "Teléfono", "Ciudad", "Cupo Crédito",
        "Saldo Total", "Alerta >90 Días (ROJO)", "Alerta 61-89 Días (AMARILLO)",
        "Alerta 1-59 Días (VERDE)", "N° Facturas"
    ]
    
    ws1.row_dimensions[4].height = 26
    for col_idx, h in enumerate(headers1, 1):
        cell = ws1.cell(row=4, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    row_num = 5
    for idx, cli in enumerate(data['clients']):
        ws1.row_dimensions[row_num].height = 20
        fill = alt_row_fill if idx % 2 == 1 else None
        
        ws1.cell(row=row_num, column=1, value=cli['nit']).alignment = Alignment(horizontal='center')
        ws1.cell(row=row_num, column=2, value=cli['name'])
        ws1.cell(row=row_num, column=3, value=cli['phone']).alignment = Alignment(horizontal='center')
        ws1.cell(row=row_num, column=4, value=cli['city'])
        
        c_cupo = ws1.cell(row=row_num, column=5, value=cli['credit_limit'])
        c_cupo.number_format = '$#,##0'
        
        c_tot = ws1.cell(row=row_num, column=6, value=cli['total_saldo'])
        c_tot.number_format = '$#,##0'
        c_tot.font = bold_font
        
        c_red = ws1.cell(row=row_num, column=7, value=cli['red_saldo'])
        c_red.number_format = '$#,##0'
        if cli['red_saldo'] > 0:
            c_red.fill = red_fill
            c_red.font = red_text
            
        c_yel = ws1.cell(row=row_num, column=8, value=cli['yellow_saldo'])
        c_yel.number_format = '$#,##0'
        if cli['yellow_saldo'] > 0:
            c_yel.fill = yellow_fill
            c_yel.font = yellow_text

        c_grn = ws1.cell(row=row_num, column=9, value=cli['green_saldo'])
        c_grn.number_format = '$#,##0'
        if cli['green_saldo'] > 0:
            c_grn.fill = green_fill
            c_grn.font = green_text

        c_cnt = ws1.cell(row=row_num, column=10, value=len(cli['invoices']))
        c_cnt.alignment = Alignment(horizontal='center')

        for col_idx in range(1, 11):
            c = ws1.cell(row=row_num, column=col_idx)
            c.border = thin_border
            if fill and c.fill == PatternFill():
                c.fill = fill

        row_num += 1

    # Totals Row
    ws1.row_dimensions[row_num].height = 24
    ws1.cell(row=row_num, column=2, value="TOTAL GENERAL CARTERA").font = bold_font
    ws1.cell(row=row_num, column=2).alignment = Alignment(horizontal='right')
    
    tot_col_mapping = {
        5: sum(c['credit_limit'] for c in data['clients']),
        6: data['summary']['total_cartera'],
        7: data['summary']['total_red_90'],
        8: data['summary']['total_yellow_60'],
        9: data['summary']['total_green_30'],
        10: data['summary']['total_invoices']
    }
    for col_idx, total_val in tot_col_mapping.items():
        cell = ws1.cell(row=row_num, column=col_idx, value=total_val)
        cell.font = bold_font
        if col_idx < 10:
            cell.number_format = '$#,##0'
        else:
            cell.alignment = Alignment(horizontal='center')
        cell.fill = total_fill

    for col_idx in range(1, 11):
        ws1.cell(row=row_num, column=col_idx).border = thin_border

    # -------------------------------------------------------------
    # SHEET 2: Detalle de Facturas
    # -------------------------------------------------------------
    ws2 = wb.create_sheet(title="Detalle Facturas por Pagar")
    ws2.views.sheetView[0].showGridLines = True

    ws2['A1'] = f"{data['metadata']['company']} - DETALLE FACTURAS PENDIENTES"
    ws2['A1'].font = title_font
    ws2['A2'] = f"Fecha de Corte: {data['summary']['review_date']} | Ordenadas: ROJAS (>90d), AMARILLAS (61-89d), VERDES (1-59d)"
    ws2['A2'].font = subtitle_font

    headers2 = [
        "NIT Cliente", "Nombre Cliente", "N° Documento", "Fec. Emisión", "Fec. Vencimiento",
        "Días Vencida", "Nivel Alerta", "Plazo (Días)", "Valor Documento", "Saldo Pendiente", "Observaciones"
    ]

    ws2.row_dimensions[4].height = 26
    for col_idx, h in enumerate(headers2, 1):
        cell = ws2.cell(row=4, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    row2 = 5
    for cli in data['clients']:
        for inv in cli['invoices']:
            ws2.row_dimensions[row2].height = 19
            ws2.cell(row=row2, column=1, value=cli['nit']).alignment = Alignment(horizontal='center')
            ws2.cell(row=row2, column=2, value=cli['name'])
            ws2.cell(row=row2, column=3, value=inv['doc_no']).alignment = Alignment(horizontal='center')
            ws2.cell(row=row2, column=4, value=inv['fec_doc']).alignment = Alignment(horizontal='center')
            ws2.cell(row=row2, column=5, value=inv['fec_vcto']).alignment = Alignment(horizontal='center')
            
            c_dias = ws2.cell(row=row2, column=6, value=inv['dias_vencida'])
            c_dias.alignment = Alignment(horizontal='center')
            c_dias.font = bold_font

            c_alerta = ws2.cell(row=row2, column=7, value=inv['alert_label'])
            c_alerta.alignment = Alignment(horizontal='center')
            
            if inv['alert_level'] == 'red':
                c_dias.fill = red_fill
                c_alerta.fill = red_fill
                c_alerta.font = red_text
            elif inv['alert_level'] == 'yellow':
                c_dias.fill = yellow_fill
                c_alerta.fill = yellow_fill
                c_alerta.font = yellow_text
            else:
                c_dias.fill = green_fill
                c_alerta.fill = green_fill
                c_alerta.font = green_text

            ws2.cell(row=row2, column=8, value=inv['plazo']).alignment = Alignment(horizontal='center')

            c_vlr = ws2.cell(row=row2, column=9, value=inv['vlr_doc'])
            c_vlr.number_format = '$#,##0'

            c_sal = ws2.cell(row=row2, column=10, value=inv['saldo'])
            c_sal.number_format = '$#,##0'
            c_sal.font = bold_font

            ws2.cell(row=row2, column=11, value=inv['observaciones'])

            for c_idx in range(1, 12):
                ws2.cell(row=row2, column=c_idx).border = thin_border

            row2 += 1

    for sheet in [ws1, ws2]:
        for col in sheet.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = str(cell.value or '')
                if cell.row < 4:
                    continue
                max_len = max(max_len, len(val))
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
