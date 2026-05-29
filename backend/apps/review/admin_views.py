from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.ingestion.models import IngestionBatch
from apps.normalization.models import NormalizedActivity
from apps.clients.models import ReportingPeriod
from apps.audit.logger import log as audit_log


def _require_admin(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role != 'ADMIN':
        return Response({'detail': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finalize_batch_view(request, batch_id):
    err = _require_admin(request)
    if err:
        return err

    client = request.user.profile.client
    try:
        batch = IngestionBatch.objects.get(id=batch_id, client=client, status='ANALYST_APPROVED')
    except IngestionBatch.DoesNotExist:
        return Response({'detail': 'Not found or not in ANALYST_APPROVED state'}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    NormalizedActivity.objects.filter(batch=batch, status='ACCEPTED').update(
        status='LOCKED',
        locked_at=now,
    )
    batch.status = 'FINALIZED'
    batch.finalized_by = request.user
    batch.finalized_at = now
    batch.save()
    return Response({'status': 'FINALIZED'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def finalize_submission_view(request, submission_id):
    err = _require_admin(request)
    if err:
        return err

    from apps.ingestion.models import Submission
    client = request.user.profile.client
    try:
        submission = Submission.objects.get(id=submission_id, client=client, status='ANALYST_APPROVED')
    except Submission.DoesNotExist:
        return Response({'detail': 'Not found or not ANALYST_APPROVED'}, status=status.HTTP_404_NOT_FOUND)

    now = timezone.now()
    batch_ids = list(submission.files.values_list('id', flat=True))

    NormalizedActivity.objects.filter(batch_id__in=batch_ids, status='ACCEPTED').update(
        status='LOCKED',
        locked_at=now,
    )
    submission.files.all().update(
        status='FINALIZED',
        finalized_by=request.user,
        finalized_at=now,
    )
    submission.status = 'FINALIZED'
    submission.finalized_by = request.user
    submission.finalized_at = now
    submission.save()
    audit_log(request.user, client, 'SUBMISSION_FINALIZED', 'Submission', submission.id,
              {'batch_number': submission.batch_number})
    return Response({'status': 'FINALIZED'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lock_period_view(request, period_id):
    err = _require_admin(request)
    if err:
        return err

    client = request.user.profile.client
    try:
        period = ReportingPeriod.objects.get(id=period_id, client=client)
    except ReportingPeriod.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    period.is_locked = True
    period.locked_at = timezone.now()
    period.locked_by = request.user
    period.save()
    audit_log(request.user, client, 'PERIOD_LOCKED', 'ReportingPeriod', period.id,
              {'name': period.name})
    return Response({'status': 'locked'})
