import math
from decimal import Decimal
from apps.parsers.csv_utils import parse_date_multi, parse_number, resolve_country_code
from apps.factors.models import EmissionFactor, AirportLookup
from apps.clients.models import ReportingPeriod
from .models import NormalizedActivity
from .geo import haversine_km
from .flags import FLAG_MESSAGES


def _get_period(client, d):
    if not d:
        return None
    return ReportingPeriod.objects.filter(
        client=client, start_date__lte=d, end_date__gte=d
    ).first()


def _get_ef(activity_type, country_code=None):
    ef = EmissionFactor.objects.filter(
        activity_type=activity_type,
        country_code=country_code
    ).order_by('-vintage_year').first()
    if ef:
        return ef, False
    ef = EmissionFactor.objects.filter(
        activity_type=activity_type, country_code__isnull=True
    ).order_by('-vintage_year').first()
    return ef, True


def _apply_flags(na, flags):
    na.flags = flags
    na.flag_summary = ' | '.join(FLAG_MESSAGES.get(f, f) for f in flags)
    na.status = 'FLAGGED' if flags else 'PENDING'


def normalize_flight_row(raw_row, client):
    data = raw_row.raw_data
    flags = []
    na = NormalizedActivity(
        raw_row=raw_row, client=client, batch=raw_row.batch,
        source_type='TRAVEL', scope=3, scope_3_category=6, activity_subtype='FLIGHT',
    )

    # Date
    date_text = str(data.get('date', '')).strip()
    na.raw_date_text = date_text
    d, _, amb = parse_date_multi(date_text)
    if amb:
        flags.append('DATE_FORMAT_AMBIGUOUS')
    na.activity_period_start = d
    na.activity_period_end = d
    na.reporting_period = _get_period(client, d)
    if not na.reporting_period and d:
        flags.append('DATE_OUTSIDE_PERIOD')

    # Distance
    origin = str(data.get('origin', '')).strip().upper()
    dest = str(data.get('destination', '')).strip().upper()
    na.raw_location_code = f"{origin}-{dest}"

    dist_text = str(data.get('distance_km', '')).strip()
    dist_val, _ = parse_number(dist_text)

    distance_km = None
    if dist_val and dist_val > 0:
        distance_km = dist_val
    else:
        origin_airport = None
        dest_airport = None
        try:
            origin_airport = AirportLookup.objects.get(iata_code=origin)
        except AirportLookup.DoesNotExist:
            if origin:
                flags.append('IATA_CODE_NOT_FOUND')
        try:
            dest_airport = AirportLookup.objects.get(iata_code=dest)
        except AirportLookup.DoesNotExist:
            if dest:
                flags.append('IATA_CODE_NOT_FOUND')

        if origin_airport and dest_airport:
            distance_km = haversine_km(
                origin_airport.latitude, origin_airport.longitude,
                dest_airport.latitude, dest_airport.longitude
            ) * 1.08
        na.resolved_location = f"{origin} → {dest}"

    # Haul type
    haul = 'SHORT_HAUL' if (distance_km or 0) < 1500 else 'LONG_HAUL'

    # Cabin class
    cabin_raw = str(data.get('cabin_class', '')).strip().lower()
    cabin_map = {
        'economy': 'ECONOMY', 'y': 'ECONOMY',
        'premium economy': 'PREMIUM', 'premium': 'PREMIUM',
        'business': 'BUSINESS', 'c': 'BUSINESS', 'j': 'BUSINESS',
        'first': 'FIRST', 'f': 'FIRST',
    }
    cabin = cabin_map.get(cabin_raw, 'ECONOMY')
    if not cabin_raw:
        flags.append('CABIN_CLASS_ASSUMED')

    # Round trip
    round_trip_raw = str(data.get('round_trip', '')).strip().lower()
    is_round = round_trip_raw in ('yes', 'y', 'true', '1')

    # Passenger-km
    pkm = None
    if distance_km:
        pkm = distance_km * (2 if is_round else 1)

    na.normalized_quantity = Decimal(str(round(pkm, 2))) if pkm else None
    na.normalized_unit = 'pkm'
    na.raw_quantity = dist_text
    na.raw_unit = 'km'
    na.conversion_display = (
        f"{distance_km:,.1f} km {'× 2 (round trip) ' if is_round else ''}= {pkm:,.1f} pkm"
        if pkm else ''
    )

    # Emission factor
    activity_type = f'FLIGHT_{haul}_{cabin}'
    ef, fallback = _get_ef(activity_type)
    if not ef:
        ef, fallback = _get_ef(f'FLIGHT_{haul}_ECONOMY')
    co2e_kg = None
    co2e_display = ''
    if ef and pkm:
        if fallback:
            flags.append('EMISSION_FACTOR_FALLBACK')
        co2e_kg = pkm * float(ef.value)
        co2e_display = f"{pkm:,.1f} pkm × {ef.value} kgCO2e/pkm = {co2e_kg:,.1f} kgCO2e"

    na.emission_factor = ef
    na.co2e_kg = Decimal(str(round(co2e_kg, 6))) if co2e_kg is not None else None
    na.co2e_display = co2e_display
    _apply_flags(na, flags)
    na.save()
    return na


def normalize_hotel_row(raw_row, client):
    data = raw_row.raw_data
    flags = []
    na = NormalizedActivity(
        raw_row=raw_row, client=client, batch=raw_row.batch,
        source_type='TRAVEL', scope=3, scope_3_category=6, activity_subtype='HOTEL',
    )

    date_text = str(data.get('date', '')).strip()
    na.raw_date_text = date_text
    d, _, _ = parse_date_multi(date_text)
    na.activity_period_start = d
    na.reporting_period = _get_period(client, d)

    checkin_text = str(data.get('check_in', '')).strip()
    checkout_text = str(data.get('check_out', '')).strip()
    checkin, _, _ = parse_date_multi(checkin_text)
    checkout, _, _ = parse_date_multi(checkout_text)

    nights = None
    if checkin and checkout:
        nights = (checkout - checkin).days
        if nights <= 0:
            flags.append('NIGHTS_ZERO')
            nights = None
    na.activity_period_end = checkout

    city = str(data.get('hotel_city', '')).strip()
    country_text = str(data.get('hotel_country', '')).strip()
    country_code = resolve_country_code(country_text) or 'IN'
    na.resolved_location = city
    na.resolved_country_code = country_code
    na.raw_location_code = city

    na.normalized_quantity = Decimal(str(nights)) if nights else None
    na.normalized_unit = 'room_night'
    na.raw_quantity = str(nights or '')
    na.raw_unit = 'nights'
    na.conversion_display = f"{nights} nights" if nights else ''

    ef, fallback = _get_ef('HOTEL_NIGHT', country_code)
    co2e_kg = None
    co2e_display = ''
    if ef and nights:
        if fallback:
            flags.append('EMISSION_FACTOR_FALLBACK')
        co2e_kg = nights * float(ef.value)
        co2e_display = f"{nights} nights × {ef.value} kgCO2e/night = {co2e_kg:,.1f} kgCO2e"

    na.emission_factor = ef
    na.co2e_kg = Decimal(str(round(co2e_kg, 6))) if co2e_kg is not None else None
    na.co2e_display = co2e_display
    _apply_flags(na, flags)
    na.save()
    return na


def normalize_ground_row(raw_row, client):
    data = raw_row.raw_data
    flags = []
    expense_type = str(data.get('expense_type', '')).strip().lower()

    type_map = {
        'taxi': 'GROUND_TAXI', 'rideshare': 'GROUND_TAXI', 'uber': 'GROUND_TAXI', 'ola': 'GROUND_TAXI',
        'train': 'GROUND_RAIL', 'rail': 'GROUND_RAIL',
        'car rental': 'GROUND_CAR', 'car_rental': 'GROUND_CAR',
        'bus': 'GROUND_BUS', 'metro': 'GROUND_BUS',
    }
    subtype = type_map.get(expense_type, 'GROUND_TAXI')

    ef_type_map = {
        'GROUND_TAXI': 'GROUND_TAXI',
        'GROUND_RAIL': 'GROUND_RAIL',
        'GROUND_CAR': 'GROUND_CAR',
        'GROUND_BUS': 'GROUND_BUS',
    }

    na = NormalizedActivity(
        raw_row=raw_row, client=client, batch=raw_row.batch,
        source_type='TRAVEL', scope=3, scope_3_category=6, activity_subtype=subtype,
    )

    date_text = str(data.get('date', '')).strip()
    na.raw_date_text = date_text
    d, _, _ = parse_date_multi(date_text)
    na.activity_period_start = d
    na.activity_period_end = d
    na.reporting_period = _get_period(client, d)

    dist_text = str(data.get('distance_km', '')).strip()
    na.raw_quantity = dist_text
    na.raw_unit = 'km'

    dist_val, _ = parse_number(dist_text)
    if dist_val is None or dist_val == 0:
        flags.append('DISTANCE_UNAVAILABLE')

    na.normalized_quantity = Decimal(str(dist_val)) if dist_val else None
    na.normalized_unit = 'km'
    na.conversion_display = f"{dist_val:,.1f} km" if dist_val else ''

    ef, fallback = _get_ef(ef_type_map.get(subtype, 'GROUND_TAXI'))
    co2e_kg = None
    co2e_display = ''
    if ef and dist_val:
        if fallback:
            flags.append('EMISSION_FACTOR_FALLBACK')
        co2e_kg = dist_val * float(ef.value)
        unit_label = 'vkm' if subtype in ('GROUND_TAXI', 'GROUND_CAR') else 'pkm'
        co2e_display = f"{dist_val:,.1f} {unit_label} × {ef.value} kgCO2e/{unit_label} = {co2e_kg:,.1f} kgCO2e"

    na.emission_factor = ef
    na.co2e_kg = Decimal(str(round(co2e_kg, 6))) if co2e_kg is not None else None
    na.co2e_display = co2e_display
    _apply_flags(na, flags)
    na.save()
    return na
