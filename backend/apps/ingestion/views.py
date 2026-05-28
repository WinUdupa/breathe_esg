from django.db.models import Sum, Count, Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import IngestionBatch
from .pipeline import compute_hash, save_file, run_ingestion_pipeline
from apps.normalization.models import NormalizedActivity


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
    total_co2e = qs.filter(co2e_kg__isnull=False).aggregate(
        total=Sum('co2e_kg')
    )['total'] or 0

    return {
        'row_stats': all_rows,
        'scope_stats': {
            'scope_1': scope_stats(1),
            'scope_2': scope_stats(2),
            'scope_3': scope_stats(3),
        },
        'total_co2e': float(total_co2e),
    }


def batch_to_dict(batch, detailed=False):
    d = {
        'id': str(batch.id),
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

    # Duplicate check
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

    batches = [batch_to_dict(b) for b in qs]
    return Response(batches)


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
