import os
import re
from datetime import datetime, date
import pymupdf

def parse_num(s):
    if not s:
        return 0.0
    s = s.strip()
    is_neg = s.endswith('-')
    if is_neg:
        s = s[:-1]
    s = s.replace(',', '')
    try:
        val = float(s)
        return -val if is_neg else val
    except:
        return 0.0

def parse_cartera_pdf(pdf_path: str):
    """
    Parses a Siesa Enterprise Uno aging report PDF into structured data.
    """
    doc = pymupdf.open(pdf_path)
    metadata = {
        'company': 'AGROINDUSTRIALES CANAVERALEJO S.A.S',
        'report_date': None,
        'report_time': None,
        'c_o': '002 BOGOTA',
        'file_name': os.path.basename(pdf_path),
        'total_pages': len(doc)
    }

    clients = {}
    current_client = None

    for pno in range(len(doc)):
        page = doc[pno]
        text = page.get_text('text')
        lines = text.splitlines()

        for line in lines:
            if 'FECHA :' in line and not metadata['report_date']:
                m_date = re.search(r'FECHA\s*:\s*(\d{4})/(\d{2})/(\d{2})', line)
                if m_date:
                    metadata['report_date'] = f"{m_date.group(1)}-{m_date.group(2)}-{m_date.group(3)}"
            if 'HORA  :' in line and not metadata['report_time']:
                m_time = re.search(r'HORA\s*:\s*([\d:\sAPMapm]+)', line)
                if m_time:
                    metadata['report_time'] = m_time.group(1).strip()
            if 'Empresa :' in line:
                m_emp = re.search(r'Empresa\s*:\s*(\S+)\s+([^\|]+)', line)
                if m_emp:
                    metadata['company'] = m_emp.group(2).strip()

            if '* R E S U M E N *' in line:
                break

            m_cli = re.match(
                r'^\s*(\d{7,11})\s{2,}(.+?)\s{2,}(.*?)\s+Tel:\s*([\d\s\-EXex/]+?)\s+Ciud:\s*(.+?)\s+Cupo:\s*([\d,]+)',
                line
            )
            if m_cli:
                nit = m_cli.group(1).strip()
                name = m_cli.group(2).strip()
                addr = m_cli.group(3).strip()
                tel = m_cli.group(4).strip()
                city = m_cli.group(5).strip()
                cupo = parse_num(m_cli.group(6))

                if nit not in clients:
                    clients[nit] = {
                        'nit': nit,
                        'name': name,
                        'address': addr,
                        'phone': tel,
                        'city': city,
                        'credit_limit': cupo,
                        'invoices': []
                    }
                current_client = clients[nit]
                continue

            m_doc = re.match(
                r'^\s*(\*?[A-Z]{2}-[\d\-]+)\s+(\d{8})\s+(\d{8})\s+(\d+)\s+([\d,]+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,\-]+)(.*)',
                line
            )
            if m_doc and current_client:
                doc_no = m_doc.group(1).strip()
                raw_fec_doc = m_doc.group(2).strip()
                raw_fec_vcto = m_doc.group(3).strip()
                dias_pdf = int(m_doc.group(4).strip())
                vlr_doc = parse_num(m_doc.group(5))
                plazo = int(m_doc.group(6).strip())
                corriente = parse_num(m_doc.group(7))
                v_1_30 = parse_num(m_doc.group(8))
                v_31_60 = parse_num(m_doc.group(9))
                v_61_90 = parse_num(m_doc.group(10))
                v_90_plus = parse_num(m_doc.group(11))
                obs = m_doc.group(12).strip()

                fec_doc_iso = f"{raw_fec_doc[0:4]}-{raw_fec_doc[4:6]}-{raw_fec_doc[6:8]}"
                fec_vcto_iso = f"{raw_fec_vcto[0:4]}-{raw_fec_vcto[4:6]}-{raw_fec_vcto[6:8]}"

                saldo = corriente + v_1_30 + v_31_60 + v_61_90 + v_90_plus

                existing = [x['doc_no'] for x in current_client['invoices']]
                if doc_no not in existing:
                    current_client['invoices'].append({
                        'doc_no': doc_no,
                        'is_partial': doc_no.startswith('*'),
                        'fec_doc': fec_doc_iso,
                        'fec_vcto': fec_vcto_iso,
                        'dias_pdf': dias_pdf,
                        'vlr_doc': vlr_doc,
                        'plazo': plazo,
                        'corriente': corriente,
                        'v_1_30': v_1_30,
                        'v_31_60': v_31_60,
                        'v_61_90': v_61_90,
                        'v_90_plus': v_90_plus,
                        'saldo': saldo,
                        'observaciones': obs
                    })

    if not metadata['report_date']:
        metadata['report_date'] = datetime.today().strftime('%Y-%m-%d')

    return {
        'metadata': metadata,
        'clients': list(clients.values())
    }

def calculate_aging_for_date(data: dict, review_date_str: str):
    """
    Recalculates days overdue and assigns strictly the 3 designated alert colors:
    - ROJO: > 90 Días
    - AMARILLO: 61 a 89 / 90 Días
    - VERDE: 1 a 59 / 60 Días (y al día)
    Invoices inside each client are sorted: ROJOS first, then AMARILLOS, then VERDES.
    Clients are sorted: Clients with ROJAS first, then AMARILLAS, then VERDES.
    """
    try:
        review_date = datetime.strptime(review_date_str, '%Y-%m-%d').date()
    except Exception:
        review_date = date.today()

    summary = {
        'review_date': review_date.strftime('%Y-%m-%d'),
        'total_cartera': 0.0,
        'total_clients': len(data['clients']),
        'total_invoices': 0,
        'total_red_90': 0.0,
        'count_red_90': 0,
        'total_yellow_60': 0.0,
        'count_yellow_60': 0,
        'total_green_30': 0.0,
        'count_green_30': 0
    }

    enriched_clients = []

    for client in data['clients']:
        cli_copy = {
            'nit': client['nit'],
            'name': client['name'],
            'address': client['address'],
            'phone': client['phone'],
            'city': client['city'],
            'credit_limit': client['credit_limit'],
            'total_saldo': 0.0,
            'red_saldo': 0.0,
            'yellow_saldo': 0.0,
            'green_saldo': 0.0,
            'red_count': 0,
            'yellow_count': 0,
            'green_count': 0,
            'highest_alert': 'green',
            'invoices': []
        }

        temp_invoices = []

        for inv in client['invoices']:
            vcto_date = datetime.strptime(inv['fec_vcto'], '%Y-%m-%d').date()
            dias_vencida = (review_date - vcto_date).days

            # Exactly the 3 requested tiers:
            # 1. ROJO: > 90 días
            # 2. AMARILLO: 61 - 89 / 90 días
            # 3. VERDE: 1 - 59 / 60 días
            if dias_vencida > 90:
                alert_level = 'red'
                alert_label = '> 90 Días'
                alert_badge_class = 'badge-red'
                order_priority = 1
                cli_copy['red_saldo'] += inv['saldo']
                cli_copy['red_count'] += 1
                summary['total_red_90'] += inv['saldo']
                summary['count_red_90'] += 1
            elif dias_vencida >= 60:
                alert_level = 'yellow'
                alert_label = '61 - 89 Días'
                alert_badge_class = 'badge-yellow'
                order_priority = 2
                cli_copy['yellow_saldo'] += inv['saldo']
                cli_copy['yellow_count'] += 1
                summary['total_yellow_60'] += inv['saldo']
                summary['count_yellow_60'] += 1
            else:
                alert_level = 'green'
                alert_label = '1 - 59 Días' if dias_vencida > 0 else 'Al Día'
                alert_badge_class = 'badge-green'
                order_priority = 3
                cli_copy['green_saldo'] += inv['saldo']
                cli_copy['green_count'] += 1
                summary['total_green_30'] += inv['saldo']
                summary['count_green_30'] += 1

            cli_copy['total_saldo'] += inv['saldo']
            summary['total_cartera'] += inv['saldo']
            summary['total_invoices'] += 1

            enriched_inv = dict(inv)
            enriched_inv['dias_vencida'] = dias_vencida
            enriched_inv['alert_level'] = alert_level
            enriched_inv['alert_label'] = alert_label
            enriched_inv['alert_badge_class'] = alert_badge_class
            enriched_inv['order_priority'] = order_priority
            temp_invoices.append(enriched_inv)

        # Sort invoices strictly as requested:
        # First ROJOS (> 90 dias), then AMARILLOS (61-89 dias), then VERDES (1-59 dias)
        # Inside same tier, sort by dias_vencida descending
        temp_invoices.sort(key=lambda x: (x['order_priority'], -x['dias_vencida']))
        cli_copy['invoices'] = temp_invoices

        # Set highest alert for the client
        if cli_copy['red_count'] > 0:
            cli_copy['highest_alert'] = 'red'
            cli_copy['client_priority'] = 1
        elif cli_copy['yellow_count'] > 0:
            cli_copy['highest_alert'] = 'yellow'
            cli_copy['client_priority'] = 2
        else:
            cli_copy['highest_alert'] = 'green'
            cli_copy['client_priority'] = 3

        # Clean Colombian phone number for WhatsApp
        raw_phone = re.sub(r'[^\d]', '', cli_copy['phone'])
        if len(raw_phone) == 10 and raw_phone.startswith('3'):
            cli_copy['whatsapp_phone'] = f"+57{raw_phone}"
            cli_copy['is_mobile'] = True
        elif len(raw_phone) == 12 and raw_phone.startswith('573'):
            cli_copy['whatsapp_phone'] = f"+{raw_phone}"
            cli_copy['is_mobile'] = True
        else:
            cli_copy['whatsapp_phone'] = ""
            cli_copy['is_mobile'] = False

        enriched_clients.append(cli_copy)

    # Sort clients:
    # 1. First clients with Red invoices (priority 1), ordered by red_saldo descending
    # 2. Then clients with Yellow invoices (priority 2), ordered by yellow_saldo descending
    # 3. Then clients with Green invoices (priority 3), ordered by green_saldo descending
    enriched_clients.sort(key=lambda x: (x['client_priority'], -x['total_saldo']))

    return {
        'metadata': data['metadata'],
        'summary': summary,
        'clients': enriched_clients
    }
