from .csv_utils import read_csv_rows
from .models import RawActivityRow


def classify_expense_type(expense_type):
    if not expense_type:
        return 'OUT_OF_SCOPE'
    t = expense_type.strip().lower()
    if t in ('flight', 'air', 'airfare'):
        return 'TRAVEL_FLIGHT'
    if t in ('hotel', 'lodging', 'accommodation'):
        return 'TRAVEL_HOTEL'
    if t in ('taxi', 'rideshare', 'uber', 'ola', 'train', 'rail',
             'car rental', 'car_rental', 'bus', 'metro', 'ferry'):
        return 'TRAVEL_GROUND'
    return 'OUT_OF_SCOPE'


def parse_travel(batch, file_bytes):
    try:
        rows = read_csv_rows(file_bytes)
    except Exception as e:
        batch.error_log = [f"CSV parse error: {str(e)}"]
        batch.status = 'FAILED'
        batch.save()
        return False

    raw_rows = []
    for i, row in enumerate(rows, start=1):
        classification = classify_expense_type(row.get('expense_type', ''))
        raw_rows.append(RawActivityRow(
            batch=batch,
            row_number=i,
            raw_data=row,
            parse_status='OK',
            parse_error='',
            classification=classification,
        ))

    RawActivityRow.objects.bulk_create(raw_rows)
    batch.row_count = len(raw_rows)
    batch.save()
    return True
