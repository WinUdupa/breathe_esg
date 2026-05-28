from django.db.models import Sum
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.normalization.models import NormalizedActivity


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def summary_view(request):
    client = request.user.profile.client
    batch_id = request.query_params.get('batch_id')

    qs = NormalizedActivity.objects.filter(client=client)
    if batch_id:
        qs = qs.filter(batch_id=batch_id)

    def scope_total(scope):
        return float(
            qs.filter(scope=scope, co2e_kg__isnull=False)
            .aggregate(t=Sum('co2e_kg'))['t'] or 0
        )

    by_subtype = {}
    for row in qs.filter(co2e_kg__isnull=False).values('activity_subtype').annotate(total=Sum('co2e_kg')):
        by_subtype[row['activity_subtype']] = float(row['total'])

    total = float(qs.filter(co2e_kg__isnull=False).aggregate(t=Sum('co2e_kg'))['t'] or 0)

    return Response({
        'total_co2e': total,
        'scope_1': scope_total(1),
        'scope_2': scope_total(2),
        'scope_3': scope_total(3),
        'by_subtype': by_subtype,
    })
