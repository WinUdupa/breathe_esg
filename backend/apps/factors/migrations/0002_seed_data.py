from django.db import migrations


EMISSION_FACTORS = [
    ('DIESEL_COMBUSTION', None, 0.0741, 'MJ', 'DEFRA'),
    ('PETROL_COMBUSTION', None, 0.0712, 'MJ', 'DEFRA'),
    ('NATURAL_GAS_COMBUSTION', None, 0.0562, 'MJ', 'DEFRA'),
    ('LPG_COMBUSTION', None, 0.0658, 'MJ', 'DEFRA'),
    ('GRID_ELECTRICITY', 'IN', 0.708, 'kWh', 'CEA'),
    ('GRID_ELECTRICITY', 'GB', 0.20705, 'kWh', 'DEFRA'),
    ('GRID_ELECTRICITY', 'US', 0.386, 'kWh', 'EPA'),
    ('GRID_ELECTRICITY', 'DE', 0.380, 'kWh', 'DEFRA'),
    ('GRID_ELECTRICITY', None, 0.475, 'kWh', 'DEFRA'),
    ('FLIGHT_SHORT_HAUL_ECONOMY', None, 0.15101, 'pkm', 'DEFRA'),
    ('FLIGHT_SHORT_HAUL_BUSINESS', None, 0.22652, 'pkm', 'DEFRA'),
    ('FLIGHT_LONG_HAUL_ECONOMY', None, 0.14787, 'pkm', 'DEFRA'),
    ('FLIGHT_LONG_HAUL_PREMIUM', None, 0.23659, 'pkm', 'DEFRA'),
    ('FLIGHT_LONG_HAUL_BUSINESS', None, 0.42939, 'pkm', 'DEFRA'),
    ('FLIGHT_LONG_HAUL_FIRST', None, 0.59148, 'pkm', 'DEFRA'),
    ('HOTEL_NIGHT', None, 10.4, 'room_night', 'DEFRA'),
    ('HOTEL_NIGHT', 'GB', 6.2, 'room_night', 'DEFRA'),
    ('HOTEL_NIGHT', 'IN', 38.8, 'room_night', 'CUSTOM'),
    ('GROUND_TAXI', None, 0.14876, 'vkm', 'DEFRA'),
    ('GROUND_CAR', None, 0.17073, 'vkm', 'DEFRA'),
    ('GROUND_RAIL', None, 0.03546, 'pkm', 'DEFRA'),
    ('GROUND_BUS', None, 0.10312, 'pkm', 'DEFRA'),
]

PLANTS = [
    ('1100', 'Mumbai Manufacturing', 'Mumbai', 'IN'),
    ('1200', 'Hamburg Plant', 'Hamburg', 'DE'),
    ('1300', 'London Warehouse', 'London', 'GB'),
    ('1400', 'Bangalore Manufacturing', 'Bangalore', 'IN'),
    ('1500', 'Delhi Warehouse', 'Delhi', 'IN'),
]

MATERIALS = [
    ('HSD-DIESEL-001', 'High Speed Diesel', 'FUEL', 'DIESEL'),
    ('HSD-DIESEL-002', 'Diesel Industrial Grade', 'FUEL', 'DIESEL'),
    ('HSD-DIESEL-003', 'Diesel Automotive', 'FUEL', 'DIESEL'),
    ('MS-PETROL-001', 'Motor Spirit Petrol', 'FUEL', 'PETROL'),
    ('MS-PETROL-002', 'Petrol Regular', 'FUEL', 'PETROL'),
    ('NATGAS-PIPE-001', 'Natural Gas Pipeline', 'FUEL', 'NATURAL_GAS'),
    ('NATGAS-PIPE-004', 'Natural Gas Industrial', 'FUEL', 'NATURAL_GAS'),
    ('LPG-BULK-001', 'LPG Bulk Industrial', 'FUEL', 'LPG'),
    ('LPG-BULK-003', 'LPG Bulk Supply', 'FUEL', 'LPG'),
    ('CHEM-SOLV-001', 'Chemical Solvent', 'NON_FUEL', None),
    ('CHEM-LUBR-002', 'Lubricating Oil', 'NON_FUEL', None),
    ('PACK-CARD-001', 'Cardboard Packaging', 'NON_FUEL', None),
]

UOM_CONVERSIONS = [
    ('L', 'DIESEL', 'MJ', 38.6),
    ('L', 'PETROL', 'MJ', 34.2),
    ('L', 'LPG', 'MJ', 26.0),
    ('L', 'NATURAL_GAS', 'MJ', 39.0),
    ('GAL', 'DIESEL', 'L', 3.785),
    ('GAL', 'PETROL', 'L', 3.785),
    ('KG', 'NATURAL_GAS', 'MJ', 53.6),
    ('KG', 'LPG', 'MJ', 49.0),
    ('M3', 'NATURAL_GAS', 'MJ', 39.0),
    ('GJ', None, 'MJ', 1000),
    ('MWH', None, 'kWh', 1000),
]

AIRPORTS = [
    ('BOM', 'Chhatrapati Shivaji Intl', 'Mumbai', 'IN', 19.0887, 72.8679),
    ('DEL', 'Indira Gandhi Intl', 'Delhi', 'IN', 28.5562, 77.1000),
    ('BLR', 'Kempegowda Intl', 'Bangalore', 'IN', 13.1986, 77.7066),
    ('MAS', 'Chennai Intl', 'Chennai', 'IN', 12.9941, 80.1709),
    ('PNQ', 'Pune Airport', 'Pune', 'IN', 18.5822, 73.9197),
    ('CCU', 'Netaji Subhas Chandra Bose Intl', 'Kolkata', 'IN', 22.6547, 88.4467),
    ('LHR', 'London Heathrow', 'London', 'GB', 51.4700, -0.4543),
    ('DXB', 'Dubai Intl', 'Dubai', 'AE', 25.2532, 55.3657),
    ('SFO', 'San Francisco Intl', 'San Francisco', 'US', 37.6213, -122.3790),
    ('JFK', 'John F Kennedy Intl', 'New York', 'US', 40.6413, -73.7781),
    ('FRA', 'Frankfurt Airport', 'Frankfurt', 'DE', 50.0379, 8.5622),
    ('SIN', 'Changi Airport', 'Singapore', 'SG', 1.3644, 103.9915),
]


def seed_factors(apps, schema_editor):
    import uuid
    EmissionFactor = apps.get_model('factors', 'EmissionFactor')
    for activity_type, country_code, value, denom_unit, source in EMISSION_FACTORS:
        EmissionFactor.objects.get_or_create(
            activity_type=activity_type,
            country_code=country_code,
            defaults=dict(
                id=uuid.uuid4(),
                source=source,
                vintage_year=2024,
                value=value,
                numerator_unit='kgCO2e',
                denominator_unit=denom_unit,
            )
        )

    PlantLookup = apps.get_model('factors', 'PlantLookup')
    for code, name, city, country in PLANTS:
        PlantLookup.objects.get_or_create(plant_code=code, defaults=dict(name=name, city=city, country_code=country))

    MaterialGroupLookup = apps.get_model('factors', 'MaterialGroupLookup')
    for code, desc, cls, fuel_type in MATERIALS:
        MaterialGroupLookup.objects.get_or_create(code=code, defaults=dict(
            description=desc, classification=cls, fuel_type=fuel_type
        ))

    UoMConversion = apps.get_model('factors', 'UoMConversion')
    for from_unit, mat_type, to_unit, mult in UOM_CONVERSIONS:
        UoMConversion.objects.get_or_create(
            from_unit=from_unit, material_type=mat_type, to_unit=to_unit,
            defaults=dict(multiplier=mult)
        )

    AirportLookup = apps.get_model('factors', 'AirportLookup')
    for iata, name, city, country, lat, lon in AIRPORTS:
        AirportLookup.objects.get_or_create(iata_code=iata, defaults=dict(
            name=name, city=city, country_code=country, latitude=lat, longitude=lon
        ))


def unseed_factors(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('factors', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(seed_factors, unseed_factors),
    ]
