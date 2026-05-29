from decimal import Decimal
from apps.parsers.csv_utils import parse_date_multi, parse_number
from apps.factors.models import EmissionFactor
from apps.clients.models import ReportingPeriod
from .models import NormalizedActivity
from .flags import FLAG_MESSAGES


INDIAN_UTILITY_KEYWORDS = ['bescom', 'msedcl', 'tneb', 'mseb', 'kseb', 'tsspdcl', 'wbsedcl']
INDIAN_CITY_KEYWORDS = ['bengaluru', 'bangalore', 'pune', 'mumbai', 'chennai', 'delhi', 'kolkata', 'hyderabad']


def _guess_country(address, account_number, client):
    lower = address.lower() if address else ''
    acct_upper = account_number.upper() if account_number else ''

    if any(kw in lower for kw in ('germany', 'deutschland')) or acct_upper.startswith('DE-'):
        return 'DE'
    if any(kw in lower for kw in ('uk', 'united kingdom')):
        return 'GB'
    if any(kw in lower for kw in ('usa', 'united states')):
        return 'US'
    for kw in INDIAN_UTILITY_KEYWORDS + INDIAN_CITY_KEYWORDS:
        if kw in lower:
            return 'IN'
    return client.country_default


def _get_ef(country_code):
    ef = EmissionFactor.objects.filter(
        activity_type='GRID_ELECTRICITY', country_code=country_code
    ).order_by('-vintage_year').first()
    if ef:
        return ef, False
    ef = EmissionFactor.objects.filter(
        activity_type='GRID_ELECTRICITY', country_code__isnull=True
    ).order_by('-vintage_year').first()
    if ef:
        # Only flag fallback when a country-specific GRID_ELECTRICITY factor
        # exists — meaning a better country factor was available but not used.
        any_country_specific = EmissionFactor.objects.filter(
            activity_type='GRID_ELECTRICITY', country_code__isnull=False
        ).exists()
        return ef, any_country_specific
    return None, False


def normalize_utility_row(raw_row, client, batch_meter_periods):
    data = raw_row.raw_data
    flags = []
    na = NormalizedActivity(
        raw_row=raw_row,
        client=client,
        batch=raw_row.batch,
        source_type='UTILITY',
        scope=2,
        activity_subtype='ELECTRICITY',
    )

    # 1. Parse dates
    start_text = str(data.get('period_start', '')).strip()
    end_text = str(data.get('period_end', '')).strip()
    na.raw_date_text = start_text

    start_date, _, s_amb = parse_date_multi(start_text)
    end_date, _, e_amb = parse_date_multi(end_text)
    if s_amb or e_amb:
        flags.append('DATE_FORMAT_AMBIGUOUS')
    na.activity_period_start = start_date
    na.activity_period_end = end_date

    # 2. Reporting period
    period = None
    if start_date:
        period = ReportingPeriod.objects.filter(
            client=client,
            start_date__lte=start_date,
            end_date__gte=start_date
        ).first()
        if not period:
            flags.append('DATE_OUTSIDE_PERIOD')
    else:
        flags.append('DATE_OUTSIDE_PERIOD')
    na.reporting_period = period

    # 3. Parse usage
    usage_text = str(data.get('usage', '')).strip()
    na.raw_quantity = usage_text
    unit = str(data.get('unit', 'kWh')).strip()
    na.raw_unit = unit

    if not usage_text:
        flags.append('MISSING_QUANTITY')
        qty = None
    else:
        qty, _ = parse_number(usage_text)
        if qty is None:
            flags.append('MISSING_QUANTITY')
        elif qty == 0:
            flags.append('ZERO_QUANTITY')

    # 4. Normalize to kWh
    normalized_qty = None
    if qty is not None:
        unit_upper = unit.upper()
        if unit_upper == 'KWH':
            normalized_qty = qty
        elif unit_upper == 'MWH':
            normalized_qty = qty * 1000
        elif unit_upper == 'WH':
            normalized_qty = qty / 1000
        else:
            flags.append('UNIT_UNRECOGNIZED')

    na.normalized_quantity = Decimal(str(normalized_qty)) if normalized_qty is not None else None
    na.normalized_unit = 'kWh' if normalized_qty is not None else ''

    # 5. Read type
    read_type = str(data.get('read_type', '')).strip().lower()
    if read_type in ('estimated', 'e', 'est'):
        flags.append('READ_ESTIMATED')

    # 6. Billing period overlap detection
    meter = str(data.get('meter', '')).strip()
    meter_key = meter
    if start_date and end_date and meter_key:
        existing = batch_meter_periods.get(meter_key, [])
        for ex_start, ex_end in existing:
            if start_date <= ex_end and end_date >= ex_start:
                flags.append('BILLING_PERIOD_OVERLAP')
                break
        existing.append((start_date, end_date))
        batch_meter_periods[meter_key] = existing

    # 6a. Duplicate detection — only flag if a row with the same meter/date/qty
    # exists in a *different* batch (rows within the current batch are not duplicates)
    if normalized_qty is not None and start_date and meter:
        dup_qty = Decimal(str(normalized_qty))
        if NormalizedActivity.objects.filter(
            client=client,
            raw_location_code=meter,
            activity_period_start=start_date,
            normalized_quantity=dup_qty,
        ).exclude(batch=raw_row.batch).exists():
            flags.append('DUPLICATE_SUSPECTED')

    # 7. Country / address
    address = str(data.get('address', '')).strip()
    account_number = str(data.get('account', '')).strip()
    na.resolved_location = address
    na.resolved_country_code = _guess_country(address, account_number, client)
    na.raw_location_code = meter

    # 8. Outlier check (>200000 kWh)
    if normalized_qty and normalized_qty > 200000:
        flags.append('OUTLIER_HIGH')

    # 9. Emission factor
    ef, fallback = _get_ef(na.resolved_country_code)
    co2e_kg = None
    co2e_display = ''
    if ef and normalized_qty is not None:
        if fallback:
            flags.append('EMISSION_FACTOR_FALLBACK')
        co2e_kg = normalized_qty * float(ef.value)
        co2e_display = (
            f"{normalized_qty:,.1f} kWh × {ef.value} kgCO2e/kWh = {co2e_kg:,.1f} kgCO2e"
        )

    na.emission_factor = ef
    na.co2e_kg = Decimal(str(round(co2e_kg, 6))) if co2e_kg is not None else None
    na.co2e_display = co2e_display
    na.conversion_display = f"{normalized_qty:,.1f} kWh (already normalized)" if normalized_qty else ''

    _apply_flags(na, flags)
    na.save()
    return na


def _apply_flags(na, flags):
    from .flags import FLAG_MESSAGES
    na.flags = flags
    na.flag_summary = ' | '.join(FLAG_MESSAGES.get(f, f) for f in flags)
    na.status = 'FLAGGED' if flags else 'PENDING'
