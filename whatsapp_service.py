import urllib.parse
from datetime import datetime

# Exactly 22 dashes as requested by the user
DASH_LINE = "----------------------"
assert len(DASH_LINE) == 22

def format_currency(val):
    if val is None:
        return "$0"
    return f"${val:,.0f}".replace(",", ".")

def generate_whatsapp_message_by_color(
    client: dict, 
    review_date_str: str, 
    color_filter: str = None, 
    company_name: str = "AGROINDUSTRIALES CAÑAVERALEJO S.A.S"
):
    """
    Generates an organized, clean WhatsApp message for a client without problematic
    icons before words, using 'Facturas mayor a...', exactly 22 dashes per separator line,
    and without double lines or smiley faces.
    MANDATORILY includes the total balance, breakdown by days, and the formal closing text.
    """
    nit = client.get('nit', '')
    name = client.get('name', '')
    total = client.get('total_saldo', 0.0)
    invoices = client.get('invoices', [])
    phone = client.get('whatsapp_phone', '')

    red_total = client.get('red_saldo', 0.0)
    red_count = client.get('red_count', 0)
    yellow_total = client.get('yellow_saldo', 0.0)
    yellow_count = client.get('yellow_count', 0)
    green_total = client.get('green_saldo', 0.0)
    green_count = client.get('green_count', 0)

    try:
        f_date = datetime.strptime(review_date_str, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        f_date = review_date_str

    if color_filter == 'red':
        target_invoices = [inv for inv in invoices if inv.get('alert_level') == 'red']
        filter_title = "FACTURAS MAYOR A 60 DÍAS"
    elif color_filter == 'yellow':
        target_invoices = [inv for inv in invoices if inv.get('alert_level') == 'yellow']
        filter_title = "FACTURAS DE 31 A 60 DÍAS"
    elif color_filter == 'green':
        target_invoices = [inv for inv in invoices if inv.get('alert_level') == 'green']
        filter_title = "FACTURAS DE 1 A 30 DÍAS"
    else:
        target_invoices = invoices
        filter_title = "DETALLE DE FACTURAS PENDIENTES"

    # Build clean invoice items separated by EXACTLY ONE line of 22 dashes (no double line, no 44 dashes)
    inv_items = []
    for inv in target_invoices:
        dias = inv.get('dias_vencida', 0)
        saldo_fmt = format_currency(inv.get('saldo', 0.0))
        doc_no = inv.get('doc_no', '')
        vcto = inv.get('fec_vcto', '')
        try:
            vcto_fmt = datetime.strptime(vcto, '%Y-%m-%d').strftime('%d/%m/%Y')
        except:
            vcto_fmt = vcto

        if dias > 60:
            mora_tag = f"{dias} días vencida (Facturas mayor a 60 días)"
        elif dias >= 31:
            mora_tag = f"{dias} días vencida (Facturas de 31 a 60 días)"
        elif dias > 0:
            mora_tag = f"{dias} días vencida (Facturas de 1 a 30 días)"
        else:
            mora_tag = f"Al día (Vence {vcto_fmt})"

        obs_line = f"\n- Observación: {inv['observaciones']}" if inv.get('observaciones') else ""

        item = (
            f"*FACTURA: {doc_no}*\n"
            f"- Fecha Vencimiento: {vcto_fmt}\n"
            f"- Estado: {mora_tag}\n"
            f"- Saldo a Pagar: *{saldo_fmt}*{obs_line}"
        )
        inv_items.append(item)

    if inv_items:
        # Exactly one single line of 22 dashes between invoices, and top/bottom
        invoices_block = f"{DASH_LINE}\n" + f"\n{DASH_LINE}\n".join(inv_items) + f"\n{DASH_LINE}"
    else:
        invoices_block = "(No presenta facturas en este rango)"

    # Mandatory Aging Breakdown by Days without icons before words
    aging_breakdown = (
        f"- Facturas mayor a 60 días: {format_currency(red_total)} ({red_count} facturas)\n"
        f"- Facturas de 31 a 60 días: {format_currency(yellow_total)} ({yellow_count} facturas)\n"
        f"- Facturas de 1 a 30 días: {format_currency(green_total)} ({green_count} facturas)"
    )

    # Full structured WhatsApp message with single 22-dash separators
    message_text = (
        f"*{company_name}*\n"
        f"*ESTADO DE CUENTA DE CARTERA*\n"
        f"{DASH_LINE}\n"
        f"*Cliente:* *{name}*\n"
        f"*NIT:* *{nit}*\n"
        f"*Fecha de Corte:* {f_date}\n\n"
        f"Estimado cliente, presentamos la relación de sus facturas ({filter_title}):\n\n"
        f"{invoices_block}\n\n"
        f"*SALDO TOTAL PENDIENTE: {format_currency(total)}*\n\n"
        f"*Desglose por Vencimientos:*\n"
        f"{aging_breakdown}\n"
        f"{DASH_LINE}\n\n"
        f"Por favor envíenos el soporte de pago o la fecha programada al presente número. ¡Muchas gracias por su confianza y puntualidad!"
    )

    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "") if phone else ""
    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message_text)}" if clean_phone else f"https://wa.me/?text={urllib.parse.quote(message_text)}"

    return {
        'filter': color_filter or 'all',
        'title': filter_title,
        'text': message_text,
        'url': wa_url,
        'target_count': len(target_invoices),
        'phone': phone
    }

def generate_all_whatsapp_options(client: dict, review_date_str: str, company_name: str = "AGROINDUSTRIALES CAÑAVERALEJO S.A.S"):
    """
    Generates all options:
    - 'all': All invoices
    - 'red': Only red invoices (>90 days)
    - 'yellow': Only yellow invoices (61-89 days)
    - 'green': Only green invoices (1-59 days)
    """
    return {
        'all': generate_whatsapp_message_by_color(client, review_date_str, None, company_name),
        'red': generate_whatsapp_message_by_color(client, review_date_str, 'red', company_name),
        'yellow': generate_whatsapp_message_by_color(client, review_date_str, 'yellow', company_name),
        'green': generate_whatsapp_message_by_color(client, review_date_str, 'green', company_name)
    }
