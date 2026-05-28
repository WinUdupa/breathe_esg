from .csv_utils import read_csv_rows
from .models import RawActivityRow


def parse_utility(batch, file_bytes):
    try:
        rows = read_csv_rows(file_bytes)
    except Exception as e:
        batch.error_log = [f"CSV parse error: {str(e)}"]
        batch.status = 'FAILED'
        batch.save()
        return False

    raw_rows = []
    for i, row in enumerate(rows, start=1):
        raw_rows.append(RawActivityRow(
            batch=batch,
            row_number=i,
            raw_data=row,
            parse_status='OK',
            parse_error='',
            classification='ELECTRICITY',
        ))

    RawActivityRow.objects.bulk_create(raw_rows)
    batch.row_count = len(raw_rows)
    batch.save()
    return True
