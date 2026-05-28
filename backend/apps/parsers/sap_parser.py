from .csv_utils import read_csv_rows
from .models import RawActivityRow


CONSUMPTION_MOVEMENT_TYPES = {'201', '261'}


def classify_sap_row(row):
    movement_type = str(row.get('movement_type', '')).strip()
    material = str(row.get('material', '')).strip()

    if movement_type not in CONSUMPTION_MOVEMENT_TYPES:
        return 'OUT_OF_SCOPE'

    from apps.factors.models import MaterialGroupLookup
    try:
        mat = MaterialGroupLookup.objects.get(code=material)
        if mat.classification == 'FUEL':
            return 'FUEL'
        else:
            return 'OUT_OF_SCOPE'
    except MaterialGroupLookup.DoesNotExist:
        return 'FUEL'


def parse_sap(batch, file_bytes):
    try:
        rows = read_csv_rows(file_bytes)
    except Exception as e:
        batch.error_log = [f"CSV parse error: {str(e)}"]
        batch.status = 'FAILED'
        batch.save()
        return False

    raw_rows = []
    for i, row in enumerate(rows, start=1):
        classification = 'PENDING'
        parse_status = 'OK'
        parse_error = ''
        try:
            classification = classify_sap_row(row)
        except Exception as e:
            parse_status = 'PARSE_ERROR'
            parse_error = str(e)

        raw_rows.append(RawActivityRow(
            batch=batch,
            row_number=i,
            raw_data=row,
            parse_status=parse_status,
            parse_error=parse_error,
            classification=classification,
        ))

    RawActivityRow.objects.bulk_create(raw_rows)
    batch.row_count = len(raw_rows)
    batch.save()
    return True
