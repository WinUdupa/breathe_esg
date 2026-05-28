from decimal import Decimal
from apps.parsers.csv_utils import parse_date_multi, parse_number
from apps.factors.models import EmissionFactor, MaterialGroupLookup, PlantLookup, UoMConversion
from apps.clients.models import ReportingPeriod
from .models import NormalizedActivity
from .flags import FLAG_MESSAGES


def _get_reporting_period(client, activity_date):
    if not activity_date:
        return None
    return ReportingPeriod.objects.filter(
        client=client,
        start_date__lte=activity_date,
        end_date__gte=activity_date
    ).first()


def _get_emission_factor(activity_type, country_code):
    ef = EmissionFactor.objects.filter(
        activity_type=activity_type, country_code=country_code
    ).order_by('-vintage_year').first()
    if ef:
        return ef, False
    ef = EmissionFactor.objects.filter(
        activity_type=activity_type, country_code__isnull=True
    ).order_by('-vintage_year').first()
    if ef:
        # Only flag fallback when a country-specific factor exists for this
        # activity type — meaning the global is a true fallback, not the
        # intended factor (e.g. fuel combustion factors are global-only).
        any_country_specific = EmissionFactor.objects.filter(
            activity_type=activity_type, country_code__isnull=False
        ).exists()
        return ef, any_country_specific
    return None, False


def normalize_sap_row(raw_row, client):
    data = raw_row.raw_data
    flags = []
    na = NormalizedActivity(
        raw_row=raw_row,
        client=client,
        batch=raw_row.batch,
        source_type='SAP',
        scope=1,
    )

    # 1. Parse date
    date_text = str(data.get('posting_date', '')).strip()
    na.raw_date_text = date_text
    activity_date, fmt, is_ambiguous = parse_date_multi(date_text)
    if is_ambiguous:
        flags.append('DATE_FORMAT_AMBIGUOUS')
    if activity_date:
        na.activity_period_start = activity_date
        na.activity_period_end = activity_date
    else:
        flags.append('MISSING_QUANTITY')  # missing date treated as data gap

    # 2. Reporting period
    period = _get_reporting_period(client, activity_date) if activity_date else None
    na.reporting_period = period
    if not period and activity_date:
        flags.append('DATE_OUTSIDE_PERIOD')

    # 3. Parse quantity
    qty_text = str(data.get('quantity', '')).strip()
    na.raw_quantity = qty_text
    unit = str(data.get('unit', '')).strip().upper()
    na.raw_unit = unit

    qty, num_ambiguous = parse_number(qty_text)
    if num_ambiguous:
        flags.append('NUMBER_FORMAT_AMBIGUOUS')
    if qty is None:
        flags.append('MISSING_QUANTITY')
    elif qty < 0:
        flags.append('NEGATIVE_QUANTITY')
    elif qty == 0:
        flags.append('ZERO_QUANTITY')

    # 4. Plant lookup
    plant_code = str(data.get('plant', '')).strip()
    na.raw_location_code = plant_code
    try:
        plant = PlantLookup.objects.get(plant_code=plant_code)
        na.resolved_location = plant.name
        na.resolved_country_code = plant.country_code
    except PlantLookup.DoesNotExist:
        flags.append('PLANT_NOT_FOUND')
        na.resolved_location = plant_code
        na.resolved_country_code = client.country_default

    # 5. Material lookup
    material_code = str(data.get('material', '')).strip()
    fuel_type = None
    try:
        mat = MaterialGroupLookup.objects.get(code=material_code)
        fuel_type = mat.fuel_type
        na.resolved_material_name = mat.description
        na.resolved_material_category = mat.classification
    except MaterialGroupLookup.DoesNotExist:
        flags.append('MATERIAL_UNCLASSIFIED')
        na.resolved_material_name = material_code
        na.resolved_material_category = 'UNKNOWN'

    # Determine activity subtype
    if fuel_type:
        na.activity_subtype = f'FUEL_{fuel_type}'
    else:
        na.activity_subtype = 'FUEL_UNKNOWN'

    # 6. Unit conversion to MJ
    normalized_qty = None
    conversion_display = ''
    if qty is not None and qty >= 0 and fuel_type:
        normalized_qty, conversion_display = _convert_to_mj(qty, unit, fuel_type, flags)

    na.normalized_quantity = Decimal(str(normalized_qty)) if normalized_qty is not None else None
    na.normalized_unit = 'MJ' if normalized_qty is not None else ''
    na.conversion_display = conversion_display

    # 7. Emission factor
    co2e_kg = None
    co2e_display = ''
    ef = None
    if fuel_type and normalized_qty is not None:
        activity_type = f'{fuel_type}_COMBUSTION'
        ef, fallback = _get_emission_factor(activity_type, na.resolved_country_code)
        if ef:
            if fallback:
                flags.append('EMISSION_FACTOR_FALLBACK')
            co2e_kg = float(normalized_qty) * float(ef.value)
            co2e_display = (
                f"{normalized_qty:,.1f} MJ × {ef.value} kgCO2e/MJ = {co2e_kg:,.1f} kgCO2e"
            )
        else:
            flags.append('CONVERSION_FACTOR_MISSING')

    na.emission_factor = ef
    na.co2e_kg = Decimal(str(round(co2e_kg, 6))) if co2e_kg is not None else None
    na.co2e_display = co2e_display

    # Final status
    _apply_flags(na, flags)
    na.save()
    return na


def _convert_to_mj(qty, unit, fuel_type, flags):
    try:
        conv = UoMConversion.objects.get(from_unit=unit, material_type=fuel_type, to_unit='MJ')
        mj = qty * float(conv.multiplier)
        display = f"{qty:,.1f} {unit} × {conv.multiplier} MJ/{unit} = {mj:,.1f} MJ"
        return mj, display
    except UoMConversion.DoesNotExist:
        pass

    # Two-step: unit → L → MJ (e.g. GAL → L → MJ)
    try:
        step1 = UoMConversion.objects.get(from_unit=unit, material_type=fuel_type, to_unit='L')
        litres = qty * float(step1.multiplier)
        step2 = UoMConversion.objects.get(from_unit='L', material_type=fuel_type, to_unit='MJ')
        mj = litres * float(step2.multiplier)
        display = (
            f"{qty:,.1f} {unit} × {step1.multiplier} L/{unit} = {litres:,.1f} L; "
            f"{litres:,.1f} L × {step2.multiplier} MJ/L = {mj:,.1f} MJ"
        )
        return mj, display
    except UoMConversion.DoesNotExist:
        pass

    # No material_type match, try generic
    try:
        conv = UoMConversion.objects.get(from_unit=unit, material_type__isnull=True, to_unit='MJ')
        mj = qty * float(conv.multiplier)
        display = f"{qty:,.1f} {unit} × {conv.multiplier} MJ/{unit} = {mj:,.1f} MJ"
        return mj, display
    except UoMConversion.DoesNotExist:
        pass

    flags.append('UNIT_UNRECOGNIZED')
    return None, ''


def _apply_flags(na, flags):
    na.flags = flags
    na.flag_summary = ' | '.join(FLAG_MESSAGES.get(f, f) for f in flags)
    na.status = 'FLAGGED' if flags else 'PENDING'
