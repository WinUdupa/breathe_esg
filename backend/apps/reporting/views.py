from django.db.models import Sum, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.normalization.models import NormalizedActivity
from apps.clients.models import ReportingPeriod

SUBTYPE_LABELS = {
    'FUEL_DIESEL': 'Diesel Combustion',
    'FUEL_PETROL': 'Petrol Combustion',
    'FUEL_NATURAL_GAS': 'Natural Gas Combustion',
    'FUEL_LPG': 'LPG Combustion',
    'ELECTRICITY': 'Grid Electricity',
    'FLIGHT': 'Air Travel – Flights',
    'HOTEL': 'Hotel Stays',
    'GROUND_TAXI': 'Ground – Taxi / Rideshare',
    'GROUND_TRAIN': 'Ground – Rail',
    'GROUND_CAR': 'Ground – Car Rental',
    'GROUND_BUS': 'Ground – Bus',
}

ACCEPTED_STATUSES = ('ACCEPTED', 'LOCKED')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def summary_view(request):
    client = request.user.profile.client
    period_id = request.query_params.get('period_id')
    submission_id = request.query_params.get('submission_id')

    qs = NormalizedActivity.objects.filter(client=client)
    if period_id:
        qs = qs.filter(reporting_period_id=period_id)
    if submission_id:
        qs = qs.filter(batch__submission_id=submission_id)

    accepted_qs = qs.filter(status__in=ACCEPTED_STATUSES)
    rejected_qs = qs.filter(status='REJECTED')

    # Totals
    total_co2e = float(
        accepted_qs.filter(co2e_kg__isnull=False).aggregate(t=Sum('co2e_kg'))['t'] or 0
    )
    total_rows = accepted_qs.count()
    rejected_rows = rejected_qs.count()
    rejected_co2e = float(
        rejected_qs.filter(co2e_kg__isnull=False).aggregate(t=Sum('co2e_kg'))['t'] or 0
    )

    # By scope
    def scope_summary(scope):
        sq = accepted_qs.filter(scope=scope, co2e_kg__isnull=False)
        return {
            'co2e_kg': float(sq.aggregate(t=Sum('co2e_kg'))['t'] or 0),
            'rows': accepted_qs.filter(scope=scope).count(),
        }

    # By source (activity_subtype)
    by_source = []
    for row in (
        accepted_qs.filter(co2e_kg__isnull=False)
        .values('activity_subtype', 'scope')
        .annotate(co2e_kg=Sum('co2e_kg'), rows=Count('id'))
        .order_by('scope', 'activity_subtype')
    ):
        by_source.append({
            'activity_subtype': row['activity_subtype'],
            'label': SUBTYPE_LABELS.get(row['activity_subtype'], row['activity_subtype']),
            'scope': row['scope'],
            'rows': row['rows'],
            'co2e_kg': float(row['co2e_kg']),
        })

    # Period info
    period_info = None
    if period_id:
        try:
            p = ReportingPeriod.objects.get(id=period_id, client=client)
            period_info = {
                'id': str(p.id),
                'name': p.name,
                'start_date': p.start_date.isoformat(),
                'end_date': p.end_date.isoformat(),
                'is_locked': p.is_locked,
            }
        except ReportingPeriod.DoesNotExist:
            pass

    # All periods for this client (for the filter dropdown)
    periods = [
        {
            'id': str(p.id),
            'name': p.name,
            'start_date': p.start_date.isoformat(),
            'end_date': p.end_date.isoformat(),
            'is_locked': p.is_locked,
        }
        for p in ReportingPeriod.objects.filter(client=client).order_by('start_date')
    ]

    return Response({
        'period': period_info,
        'periods': periods,
        'total_co2e_kg': total_co2e,
        'total_rows': total_rows,
        'by_scope': {
            'scope_1': scope_summary(1),
            'scope_2': scope_summary(2),
            'scope_3': scope_summary(3),
        },
        'by_source': by_source,
        'rejected': {
            'rows': rejected_rows,
            'co2e_kg': rejected_co2e,
        },
    })
