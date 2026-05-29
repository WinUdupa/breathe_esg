from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ReportingPeriod
from apps.audit.logger import log as audit_log


def period_to_dict(p):
    return {
        'id': str(p.id),
        'name': p.name,
        'start_date': p.start_date.isoformat(),
        'end_date': p.end_date.isoformat(),
        'is_locked': p.is_locked,
        'locked_at': p.locked_at.isoformat() if p.locked_at else None,
        'locked_by': p.locked_by.username if p.locked_by else None,
    }


def _require_admin(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role != 'ADMIN':
        return Response({'detail': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def period_list_view(request):
    client = request.user.profile.client

    if request.method == 'GET':
        periods = ReportingPeriod.objects.filter(client=client).order_by('start_date')
        return Response([period_to_dict(p) for p in periods])

    err = _require_admin(request)
    if err:
        return err

    name = request.data.get('name', '').strip()
    start_date = request.data.get('start_date')
    end_date = request.data.get('end_date')

    if not name or not start_date or not end_date:
        return Response({'detail': 'name, start_date, and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    if ReportingPeriod.objects.filter(client=client, name=name).exists():
        return Response({'detail': f'A period named "{name}" already exists'}, status=status.HTTP_409_CONFLICT)

    period = ReportingPeriod.objects.create(
        client=client,
        name=name,
        start_date=start_date,
        end_date=end_date,
    )
    audit_log(request.user, client, 'PERIOD_CREATED', 'ReportingPeriod', period.id,
              {'name': name, 'start_date': start_date, 'end_date': end_date})
    return Response(period_to_dict(period), status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def period_detail_view(request, period_id):
    err = _require_admin(request)
    if err:
        return err

    client = request.user.profile.client
    try:
        period = ReportingPeriod.objects.get(id=period_id, client=client)
    except ReportingPeriod.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if period.is_locked:
        return Response({'detail': 'Cannot modify a locked period'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'DELETE':
        period.delete()
        return Response({'status': 'deleted'})

    # PATCH
    for field in ('name', 'start_date', 'end_date'):
        if field in request.data:
            setattr(period, field, request.data[field])
    period.save()
    return Response(period_to_dict(period))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def period_lock_view(request, period_id):
    err = _require_admin(request)
    if err:
        return err

    client = request.user.profile.client
    try:
        period = ReportingPeriod.objects.get(id=period_id, client=client)
    except ReportingPeriod.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if period.is_locked:
        return Response({'detail': 'Already locked'}, status=status.HTTP_400_BAD_REQUEST)

    period.is_locked = True
    period.locked_at = timezone.now()
    period.locked_by = request.user
    period.save()
    audit_log(request.user, client, 'PERIOD_LOCKED', 'ReportingPeriod', period.id,
              {'name': period.name})
    return Response(period_to_dict(period))
