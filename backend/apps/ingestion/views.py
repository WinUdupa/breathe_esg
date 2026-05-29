import os
from django.db import transaction
from django.db.models import Sum, Count, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import IngestionBatch, Submission
from .pipeline import compute_hash, save_file, run_ingestion_pipeline
from apps.audit.logger import log as audit_log
from apps.normalization.models import NormalizedActivity
from apps.parsers.models import RawActivityRow


# ── Serialization helpers ─────────────────────────────────────────────────────

def batch_stats(batch):
    qs = NormalizedActivity.objects.filter(batch=batch)

    def scope_stats(scope):
        rows = qs.filter(scope=scope)
        total = rows.count()
        return {
            'total': total,
            'pending': rows.filter(status='PENDING').count(),
            'flagged': rows.filter(status='FLAGGED').count(),
            'accepted': rows.filter(status='ACCEPTED').count(),
            'rejected': rows.filter(status='REJECTED').count(),
            'locked': rows.filter(status='LOCKED').count(),
        }

    all_rows = {
        'total': qs.count(),
        'pending': qs.filter(status='PENDING').count(),
        'flagged': qs.filter(status='FLAGGED').count(),
        'accepted': qs.filter(status='ACCEPTED').count(),
        'rejected': qs.filter(status='REJECTED').count(),
        'locked': qs.filter(status='LOCKED').count(),
    }
    total_co2e = qs.filter(co2e_kg__isnull=False).aggregate(total=Sum('co2e_kg'))['total'] or 0
    rejected_co2e = float(
        qs.filter(status='REJECTED', co2e_kg__isnull=False).aggregate(t=Sum('co2e_kg'))['t'] or 0
    )

    return {
        'row_stats': all_rows,
        'scope_stats': {
            'scope_1': scope_stats(1),
            'scope_2': scope_stats(2),
            'scope_3': scope_stats(3),
        },
        'total_co2e': float(total_co2e),
        'rejected_co2e': rejected_co2e,
    }


def batch_to_dict(batch, detailed=False):
    d = {
        'id': str(batch.id),
        'submission_id': str(batch.submission_id) if batch.submission_id else None,
        'source_type': batch.source_type,
        'file_name': batch.file_name,
        'status': batch.status,
        'uploaded_by_name': batch.uploaded_by.username if batch.uploaded_by else None,
        'uploaded_at': batch.uploaded_at.isoformat(),
        'row_count': batch.row_count,
        'error_log': batch.error_log,
        'analyst_note': batch.analyst_note,
        'reviewed_by_name': batch.reviewed_by.username if batch.reviewed_by else None,
        'reviewed_at': batch.reviewed_at.isoformat() if batch.reviewed_at else None,
        'finalized_by_name': batch.finalized_by.username if batch.finalized_by else None,
        'finalized_at': batch.finalized_at.isoformat() if batch.finalized_at else None,
    }
    if detailed:
        d.update(batch_stats(batch))
    return d


def submission_to_dict(submission):
    files = list(submission.files.select_related('uploaded_by').order_by('uploaded_at'))

    # Flagged counts in one query
    flagged_by_batch = {}
    if files:
        for r in NormalizedActivity.objects.filter(
            batch__in=[f.id for f in files], status='FLAGGED'
        ).values('batch').annotate(n=Count('id')):
            flagged_by_batch[str(r['batch'])] = r['n']

    total_flagged = sum(flagged_by_batch.values())
    total_rows = sum(f.row_count or 0 for f in files)

    file_dicts = []
    for f in files:
        fd = batch_to_dict(f)
        fd['flagged_count'] = flagged_by_batch.get(str(f.id), 0)
        file_dicts.append(fd)

    return {
        'id': str(submission.id),
        'batch_number': submission.batch_number,
        'status': submission.status,
        'created_by_name': submission.created_by.username if submission.created_by else None,
        'created_at': submission.created_at.isoformat(),
        'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
        'reviewed_by_name': submission.reviewed_by.username if submission.reviewed_by else None,
        'reviewed_at': submission.reviewed_at.isoformat() if submission.reviewed_at else None,
        'analyst_note': submission.analyst_note,
        'finalized_by_name': submission.finalized_by.username if submission.finalized_by else None,
        'finalized_at': submission.finalized_at.isoformat() if submission.finalized_at else None,
        'files': file_dicts,
        'file_types': [f.source_type for f in files],
        'total_flagged': total_flagged,
        'total_rows': total_rows,
    }


# ── Submission CRUD ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submission_create_view(request):
    profile = request.user.profile
    client = profile.client

    with transaction.atomic():
        max_num = Submission.objects.filter(client=client).aggregate(
            Max('batch_number')
        )['batch_number__max'] or 0
        submission = Submission.objects.create(
            client=client,
            batch_number=max_num + 1,
            created_by=request.user,
        )

    return Response(submission_to_dict(submission), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def submission_list_view(request):
    profile = request.user.profile
    client = profile.client
    role = profile.role

    qs = Submission.objects.filter(client=client).prefetch_related('files')

    if role == 'UPLOADER':
        qs = qs.filter(created_by=request.user)
    elif role == 'ANALYST':
        qs = qs.filter(status__in=['PENDING_REVIEW', 'IN_REVIEW', 'ANALYST_APPROVED'])
    elif role == 'ADMIN':
        qs = qs.filter(status__in=['ANALYST_APPROVED', 'FINALIZED'])

    return Response([submission_to_dict(s) for s in qs])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def submission_detail_view(request, submission_id):
    profile = request.user.profile
    client = profile.client
    try:
        submission = Submission.objects.get(id=submission_id, client=client)
    except Submission.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(submission_to_dict(submission))


# ── File upload within a submission ──────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def submission_upload_view(request, submission_id):
    profile = request.user.profile
    client = profile.client

    try:
        submission = Submission.objects.get(id=submission_id, client=client)
    except Submission.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if submission.status == 'FINALIZED':
        return Response({'detail': 'Cannot upload to a finalized batch'}, status=status.HTTP_403_FORBIDDEN)

    source_type = request.data.get('source_type', '').upper()
    if source_type not in ('SAP', 'UTILITY', 'TRAVEL'):
        return Response({'detail': 'Invalid source_type'}, status=status.HTTP_400_BAD_REQUEST)

    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    file_bytes = file_obj.read()
    file_hash = compute_hash(file_bytes)

    # Duplicate check across other submissions
    dup = IngestionBatch.objects.filter(client=client, file_hash=file_hash).exclude(
        submission=submission
    ).first()
    if dup:
        return Response({
            'detail': f'Duplicate file — already uploaded on {dup.uploaded_at.strftime("%Y-%m-%d %H:%M")}.',
        }, status=status.HTTP_409_CONFLICT)

    # Replace existing file of the same type within this submission
    existing = IngestionBatch.objects.filter(submission=submission, source_type=source_type).first()
    if existing:
        _delete_batch_data(existing)

    batch = IngestionBatch.objects.create(
        client=client,
        submission=submission,
        source_type=source_type,
        uploaded_by=request.user,
        file_name=file_obj.name,
        file_path='',
        file_hash=file_hash,
        file_size_bytes=len(file_bytes),
        status='PROCESSING',
    )

    file_path = save_file(file_bytes, client.id, batch.id, file_obj.name)
    batch.file_path = file_path
    batch.save()

    run_ingestion_pipeline(batch, file_bytes, client)
    batch.refresh_from_db()
    audit_log(request.user, client, 'FILE_UPLOADED', 'IngestionBatch', batch.id,
              {'source_type': source_type, 'file_name': file_obj.name,
               'row_count': batch.row_count, 'batch_number': submission.batch_number})

    # If the submission was in review, revert to OPEN so it goes back through the queue
    if submission.status != 'OPEN':
        submission.status = 'OPEN'
        submission.submitted_at = None
        submission.reviewed_by = None
        submission.reviewed_at = None
        submission.save()

    submission.refresh_from_db()
    return Response(submission_to_dict(submission), status=status.HTTP_201_CREATED)


# ── File delete ───────────────────────────────────────────────────────────────

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def file_delete_view(request, file_id):
    profile = request.user.profile
    client = profile.client

    try:
        batch = IngestionBatch.objects.select_related('submission').get(id=file_id, client=client)
    except IngestionBatch.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if batch.submission and batch.submission.status == 'FINALIZED':
        return Response({'detail': 'Cannot delete files from a finalized batch'}, status=status.HTTP_403_FORBIDDEN)

    if profile.role == 'UPLOADER' and batch.uploaded_by != request.user:
        return Response({'detail': 'Cannot delete another user\'s file'}, status=status.HTTP_403_FORBIDDEN)

    submission = batch.submission
    audit_log(request.user, client, 'FILE_DELETED', 'IngestionBatch', file_id,
              {'source_type': batch.source_type, 'file_name': batch.file_name,
               'batch_number': submission.batch_number if submission else None})
    _delete_batch_data(batch)

    if submission:
        # Revert submission to OPEN if it had already been submitted for review
        if submission.status != 'OPEN':
            submission.status = 'OPEN'
            submission.submitted_at = None
            submission.reviewed_by = None
            submission.reviewed_at = None
            submission.save()
        else:
            submission.refresh_from_db()
        return Response(submission_to_dict(submission))
    return Response({'status': 'deleted'})


def _delete_batch_data(batch):
    NormalizedActivity.objects.filter(batch=batch).delete()
    RawActivityRow.objects.filter(batch=batch).delete()
    if batch.file_path and os.path.exists(batch.file_path):
        try:
            os.remove(batch.file_path)
        except OSError:
            pass
    batch.delete()


# ── Uploader submit for review ────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submission_uploader_submit_view(request, submission_id):
    profile = request.user.profile
    client = profile.client

    try:
        submission = Submission.objects.get(id=submission_id, client=client)
    except Submission.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if submission.status != 'OPEN':
        return Response({'detail': 'Submission is not open'}, status=status.HTTP_400_BAD_REQUEST)

    files = submission.files.all()
    if not files.exists():
        return Response({'detail': 'Upload at least one file before submitting'}, status=status.HTTP_400_BAD_REQUEST)

    failed = files.filter(status='FAILED')
    if failed.exists():
        return Response(
            {'detail': f'{failed.count()} file(s) failed processing. Delete and re-upload before submitting.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    processing = files.filter(status='PROCESSING')
    if processing.exists():
        return Response({'detail': 'Files still processing, please wait'}, status=status.HTTP_400_BAD_REQUEST)

    submission.status = 'PENDING_REVIEW'
    submission.submitted_at = timezone.now()
    submission.save()
    audit_log(request.user, client, 'SUBMISSION_SUBMITTED', 'Submission', submission.id,
              {'batch_number': submission.batch_number,
               'file_types': [f.source_type for f in files]})
    return Response(submission_to_dict(submission))


# ── Legacy single-file upload (kept for backward compat) ─────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_view(request):
    profile = request.user.profile
    client = profile.client
    source_type = request.data.get('source_type', '').upper()

    if source_type not in ('SAP', 'UTILITY', 'TRAVEL'):
        return Response({'detail': 'Invalid source_type'}, status=status.HTTP_400_BAD_REQUEST)

    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    file_bytes = file_obj.read()
    file_hash = compute_hash(file_bytes)

    existing = IngestionBatch.objects.filter(client=client, file_hash=file_hash).first()
    if existing:
        return Response({
            'detail': f'Duplicate file. Already uploaded on {existing.uploaded_at.strftime("%Y-%m-%d %H:%M")}.',
            'batch_id': str(existing.id),
        }, status=status.HTTP_409_CONFLICT)

    batch = IngestionBatch.objects.create(
        client=client,
        source_type=source_type,
        uploaded_by=request.user,
        file_name=file_obj.name,
        file_path='',
        file_hash=file_hash,
        file_size_bytes=len(file_bytes),
        status='PROCESSING',
    )

    file_path = save_file(file_bytes, client.id, batch.id, file_obj.name)
    batch.file_path = file_path
    batch.save()

    run_ingestion_pipeline(batch, file_bytes, client)
    batch.refresh_from_db()

    return Response(batch_to_dict(batch, detailed=True), status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_list_view(request):
    profile = request.user.profile
    client = profile.client
    role = profile.role

    qs = IngestionBatch.objects.filter(client=client)
    if role == 'UPLOADER':
        qs = qs.filter(uploaded_by=request.user)
    elif role == 'ANALYST':
        qs = qs.filter(status__in=['PENDING_REVIEW', 'IN_REVIEW', 'ANALYST_APPROVED'])
    elif role == 'ADMIN':
        qs = qs.filter(status__in=['ANALYST_APPROVED', 'FINALIZED'])

    return Response([batch_to_dict(b) for b in qs])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def batch_detail_view(request, batch_id):
    profile = request.user.profile
    client = profile.client
    try:
        batch = IngestionBatch.objects.get(id=batch_id, client=client)
    except IngestionBatch.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(batch_to_dict(batch, detailed=True))
