import csv
import io
import re
from datetime import date


def detect_encoding(file_bytes):
    for enc in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
        try:
            file_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, AttributeError):
            continue
    return 'latin-1'


def detect_delimiter(text_sample):
    try:
        dialect = csv.Sniffer().sniff(text_sample, delimiters=',;\t|')
        return dialect.delimiter
    except csv.Error:
        pass
    first_line = text_sample.split('\n')[0]
    counts = {',': first_line.count(','), ';': first_line.count(';'), '\t': first_line.count('\t')}
    return max(counts, key=counts.get)


def parse_date_multi(text):
    if not text or not text.strip():
        return None, None, False
    text = text.strip()
    formats_to_try = [
        ('%Y%m%d', False),
        ('%d.%m.%Y', False),
        ('%Y-%m-%d', False),
        ('%d-%b-%Y', False),
        ('%d/%m/%Y', True),
    ]
    for fmt, ambiguous in formats_to_try:
        try:
            d = _strptime_date(text, fmt)
            if d:
                if ambiguous:
                    parts = text.split('/')
                    if len(parts) == 3:
                        day_candidate = int(parts[0])
                        month_candidate = int(parts[1])
                        if day_candidate > 12:
                            ambiguous = False
                        elif day_candidate == month_candidate:
                            ambiguous = False
                        elif month_candidate > 12:
                            ambiguous = False
                        else:
                            ambiguous = False  # default DD/MM/YYYY — all clients are Indian/European
                return d, fmt, ambiguous
        except (ValueError, IndexError):
            continue
    return None, None, False


def _strptime_date(text, fmt):
    from datetime import datetime
    try:
        return datetime.strptime(text, fmt).date()
    except ValueError:
        return None


def parse_number(text):
    if text is None:
        return None, False
    text = str(text).strip()
    text = re.sub(r'[^\d.,\-]', '', text)
    if not text or text in ('-', ''):
        return None, False

    ambiguous = False
    negative = text.startswith('-')
    text_abs = text.lstrip('-')

    if ',' in text_abs and '.' in text_abs:
        last_comma = text_abs.rfind(',')
        last_dot = text_abs.rfind('.')
        if last_dot > last_comma:
            cleaned = text_abs.replace(',', '')
        else:
            cleaned = text_abs.replace('.', '').replace(',', '.')
    elif ',' in text_abs:
        parts = text_abs.split(',')
        if len(parts) == 2 and len(parts[1]) == 3:
            cleaned = text_abs.replace(',', '')
        else:
            cleaned = text_abs.replace(',', '.')
    elif '.' in text_abs:
        parts = text_abs.split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            ambiguous = True
            cleaned = text_abs.replace('.', '')
        else:
            cleaned = text_abs
    else:
        cleaned = text_abs

    try:
        value = float(cleaned)
        if negative:
            value = -value
        return value, ambiguous
    except ValueError:
        return None, False


def resolve_country_code(text):
    if not text:
        return None
    text = text.strip()
    if len(text) == 2:
        return text.upper()
    mapping = {
        'india': 'IN', 'uk': 'GB', 'united kingdom': 'GB', 'great britain': 'GB',
        'uae': 'AE', 'united arab emirates': 'AE', 'dubai': 'AE',
        'usa': 'US', 'united states': 'US', 'us': 'US',
        'germany': 'DE', 'singapore': 'SG', 'australia': 'AU',
        'china': 'CN', 'japan': 'JP', 'france': 'FR',
    }
    return mapping.get(text.lower())


def normalise_headers(headers):
    SAP_MAP = {
        'budat': 'posting_date', 'posting date': 'posting_date', 'belegdatum': 'posting_date',
        'mblnr': 'document_number', 'material document': 'document_number',
        'matnr': 'material', 'material': 'material',
        'werks': 'plant', 'plant': 'plant', 'werk': 'plant',
        'bwart': 'movement_type', 'movement type': 'movement_type', 'bewegungsart': 'movement_type',
        'menge': 'quantity', 'quantity': 'quantity',
        'meins': 'unit', 'unit': 'unit', 'uom': 'unit', 'einheit': 'unit',
        'dmbtr': 'amount', 'amount': 'amount', 'betrag': 'amount',
        'waers': 'currency', 'currency': 'currency', 'währung': 'currency',
    }
    UTILITY_MAP = {
        'account number': 'account', 'account id': 'account',
        'meter id': 'meter',
        'service address': 'address', 'site': 'address', 'location': 'address',
        'period start': 'period_start', 'from date': 'period_start',
        'period end': 'period_end', 'to date': 'period_end',
        'usage (kwh)': 'usage', 'usage': 'usage', 'consumption': 'usage',
        'unit': 'unit', 'uom': 'unit',
        'read type': 'read_type',
        'amount': 'amount', 'total': 'amount',
    }
    TRAVEL_MAP = {
        'trip id': 'trip_id',
        'expense type': 'expense_type', 'category': 'expense_type',
        'date': 'date', 'transaction date': 'date',
        'employee': 'employee', 'employee id': 'employee',
        'department': 'department',
        'amount': 'amount',
        'currency': 'currency',
        'origin': 'origin', 'from airport': 'origin',
        'destination': 'destination', 'to airport': 'destination',
        'cabin class': 'cabin_class', 'class of service': 'cabin_class',
        'round trip': 'round_trip',
        'hotel city': 'hotel_city',
        'hotel country': 'hotel_country',
        'check in': 'check_in',
        'check out': 'check_out',
        'distance (km)': 'distance_km', 'distance': 'distance_km',
    }
    combined = {}
    combined.update(SAP_MAP)
    combined.update(UTILITY_MAP)
    combined.update(TRAVEL_MAP)
    result = []
    for h in headers:
        key = h.strip().lower()
        result.append(combined.get(key, key))
    return result


def read_csv_rows(file_bytes):
    encoding = detect_encoding(file_bytes)
    text = file_bytes.decode(encoding)
    delimiter = detect_delimiter(text[:2000])
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    raw_headers = reader.fieldnames or []
    normalised = normalise_headers(raw_headers)
    header_map = dict(zip(raw_headers, normalised))
    rows = []
    for row in reader:
        mapped = {header_map.get(k, k): v for k, v in row.items()}
        for overflow_key in (None, 'null', ''):
            if overflow_key in mapped:
                val = str(mapped.pop(overflow_key) or '').strip()
                if val and not str(mapped.get('distance_km', '') or '').strip():
                    mapped['distance_km'] = val
        rows.append(mapped)
    return rows
