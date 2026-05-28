from apps.parsers.models import RawActivityRow
from .sap_normalizer import normalize_sap_row
from .utility_normalizer import normalize_utility_row
from .travel_normalizer import normalize_flight_row, normalize_hotel_row, normalize_ground_row
from .outlier_detection import run_outlier_detection


def run_normalization(batch, client):
    rows = RawActivityRow.objects.filter(batch=batch, parse_status='OK').exclude(
        classification__in=['OUT_OF_SCOPE', 'NON_FUEL']
    )

    batch_meter_periods = {}

    for row in rows:
        try:
            cls = row.classification
            if cls == 'FUEL':
                normalize_sap_row(row, client)
            elif cls == 'ELECTRICITY':
                normalize_utility_row(row, client, batch_meter_periods)
            elif cls == 'TRAVEL_FLIGHT':
                normalize_flight_row(row, client)
            elif cls == 'TRAVEL_HOTEL':
                normalize_hotel_row(row, client)
            elif cls == 'TRAVEL_GROUND':
                normalize_ground_row(row, client)
        except Exception as e:
            batch.error_log = batch.error_log + [f"Row {row.row_number}: {str(e)}"]
            batch.save()

    run_outlier_detection(batch)
