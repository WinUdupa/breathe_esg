from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.normalization.models import NormalizedActivity
from apps.normalization.flags import FLAG_MESSAGES
from apps.ingestion.models import IngestionBatch
from apps.audit.logger import log as audit_log


def row_to_dict(row, detail=False):
    d = {
        'id': str(row.id),
        'row_number': row.raw_row.row_number,
        'scope': row.scope,
        'scope_3_category': row.scope_3_category,
        'activity_subtype': row.activity_subtype,
        'raw_quantity': row.raw_quantity,
        'raw_unit': row.raw_unit,
        'raw_date_text': row.raw_date_text,
        'raw_location_code': row.raw_location_code,
        'normalized_quantity': float(row.normalized_quantity) if row.normalized_quantity is not None else None,
        'normalized_unit': row.normalized_unit,
        'resolved_location': row.resolved_location,
        'resolved_country_code': row.resolved_country_code,
        'resolved_material_name': row.resolved_material_name,
        'co2e_kg': float(row.co2e_kg) if row.co2e_kg is not None else None,
        'conversion_display': row.conversion_display,
        'co2e_display': row.co2e_display,
        'status': row.status,
        'flags': row.flags,
        'flag_messages': [{'code': f, 'message': FLAG_MESSAGES.get(f, f)} for f in row.flags],
        'flag_summary': row.flag_summary,
        'reviewed_by': row.reviewed_by.username if row.reviewed_by else None,
        'reviewed_at': row.reviewed_at.isoformat() if row.reviewed_at else None,
        'review_note': row.review_note,
        'is_edited': row.is_edited,
        'activity_period_start': row.activity_period_start.isoformat() if row.activity_period_start else None,
        'activity_period_end': row.activity_period_end.isoformat() if row.activity_period_end else None,
        'reporting_period': str(row.reporting_period) if row.reporting_period else None,
    }
    if detail:
        d['raw_data'] = row.raw_row.raw_data
        d['edit_history'] = row.edit_history
        if row.emission_factor:
            ef = row.emission_factor
            d['emission_factor_detail'] = {
                'source': ef.source,
                'year': ef.vintage_year,
                'value': float(ef.value),
                'activity_type': ef.activity_type,
                'denominator_unit': ef.denominator_unit,
            }
        else:
            d['emission_factor_detail'] = None
    return d


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def row_list_view(request):
    profile = request.user.profile
    client = profile.client

    batch_id = request.query_params.get('batch_id')
    scope = request.query_params.get('scope')
    status_filter = request.query_params.get('status', '')

    qs = NormalizedActivity.objects.filter(client=client).select_related(
        'raw_row', 'reviewed_by', 'emission_factor', 'reporting_period'
    )
    if batch_id:
        qs = qs.filter(batch_id=batch_id)
    if scope:
        qs = qs.filter(scope=int(scope))
    if status_filter:
        statuses = [s.strip() for s in status_filter.split(',')]
        qs = qs.filter(status__in=statuses)

    # Sort: flagged first, then pending, then rest
    from django.db.models import Case, When, IntegerField
    qs = qs.annotate(
        sort_order=Case(
            When(status='FLAGGED', then=0),
            When(status='PENDING', then=1),
            When(status='ACCEPTED', then=2),
            When(status='REJECTED', then=3),
            When(status='LOCKED', then=4),
            default=5,
            output_field=IntegerField(),
        )
    ).order_by('sort_order', 'raw_row__row_number')

    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginator.page_size = 20
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response([row_to_dict(r) for r in page])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def row_detail_view(request, row_id):
    profile = request.user.profile
    client = profile.client
    try:
        row = NormalizedActivity.objects.select_related(
            'raw_row', 'reviewed_by', 'emission_factor', 'reporting_period'
        ).get(id=row_id, client=client)
    except NormalizedActivity.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(row_to_dict(row, detail=True))


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def row_edit_view(request, row_id):
    profile = request.user.profile
    client = profile.client
    try:
        row = NormalizedActivity.objects.get(id=row_id, client=client)
    except NormalizedActivity.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if row.status == 'LOCKED':
        return Response({'detail': 'Row is locked'}, status=status.HTTP_403_FORBIDDEN)

    editable_fields = [
        'normalized_quantity', 'normalized_unit', 'activity_period_start',
        'activity_period_end', 'resolved_country_code', 'review_note',
    ]
    history = row.edit_history or []
    now = timezone.now().isoformat()

    for field in editable_fields:
        if field in request.data:
            old_val = str(getattr(row, field, ''))
            new_val = request.data[field]
            if str(old_val) != str(new_val):
                history.append({
                    'field': field,
                    'old_value': old_val,
                    'new_value': str(new_val),
                    'changed_by': request.user.username,
                    'changed_at': now,
                    'reason': request.data.get('reason', ''),
                })
                setattr(row, field, new_val)

    row.is_edited = True
    row.edit_history = history
    row.status = 'FLAGGED'
    row.reviewed_by = None
    row.reviewed_at = None
    row.save()
    if history:
        audit_log(request.user, client, 'ROW_EDITED', 'NormalizedActivity', row.id,
                  {'row_number': row.raw_row.row_number, 'changes': history[-len(request.data):]})
    return Response(row_to_dict(row, detail=True))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def row_accept_view(request, row_id):
    profile = request.user.profile
    client = profile.client
    try:
        row = NormalizedActivity.objects.get(id=row_id, client=client)
    except NormalizedActivity.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if row.status == 'LOCKED':
        return Response({'detail': 'Row is locked'}, status=status.HTTP_403_FORBIDDEN)

    review_note = request.data.get('review_note', '').strip()
    if row.status == 'FLAGGED' and not review_note:
        return Response({'detail': 'review_note required for flagged rows'}, status=status.HTTP_400_BAD_REQUEST)

    row.status = 'ACCEPTED'
    row.reviewed_by = request.user
    row.reviewed_at = timezone.now()
    row.review_note = review_note
    row.save()
    audit_log(request.user, client, 'ROW_ACCEPTED', 'NormalizedActivity', row.id,
              {'row_number': row.raw_row.row_number, 'subtype': row.activity_subtype,
               'co2e_kg': float(row.co2e_kg) if row.co2e_kg else None, 'note': review_note})
    return Response(row_to_dict(row))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def row_reject_view(request, row_id):
    profile = request.user.profile
    client = profile.client
    try:
        row = NormalizedActivity.objects.get(id=row_id, client=client)
    except NormalizedActivity.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if row.status == 'LOCKED':
        return Response({'detail': 'Row is locked'}, status=status.HTTP_403_FORBIDDEN)

    review_note = request.data.get('review_note', '').strip()
    if not review_note:
        return Response({'detail': 'review_note required for rejection'}, status=status.HTTP_400_BAD_REQUEST)

    row.status = 'REJECTED'
    row.reviewed_by = request.user
    row.reviewed_at = timezone.now()
    row.review_note = review_note
    row.save()
    audit_log(request.user, client, 'ROW_REJECTED', 'NormalizedActivity', row.id,
              {'row_number': row.raw_row.row_number, 'subtype': row.activity_subtype,
               'co2e_kg': float(row.co2e_kg) if row.co2e_kg else None, 'note': review_note})
    return Response(row_to_dict(row))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_accept_view(request):
    profile = request.user.profile
    client = profile.client
    batch_id = request.data.get('batch_id')
    scope = request.data.get('scope')

    qs = NormalizedActivity.objects.filter(client=client, status='PENDING')
    if batch_id:
        qs = qs.filter(batch_id=batch_id)
    if scope:
        qs = qs.filter(scope=int(scope))

    now = timezone.now()
    updated = qs.update(
        status='ACCEPTED',
        reviewed_by=request.user,
        reviewed_at=now,
        review_note='Bulk accepted',
    )
    audit_log(request.user, client, 'ROWS_BULK_ACCEPTED', 'IngestionBatch', batch_id or '',
              {'scope': scope, 'count': updated})
    return Response({'accepted': updated})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_submit_view(request, batch_id):
    profile = request.user.profile
    client = profile.client
    try:
        batch = IngestionBatch.objects.get(id=batch_id, client=client)
    except IngestionBatch.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check all FLAGGED rows are resolved
    flagged_remaining = NormalizedActivity.objects.filter(
        batch=batch, status='FLAGGED'
    ).count()
    if flagged_remaining > 0:
        return Response(
            {'detail': f'{flagged_remaining} flagged rows must be resolved before submitting'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Auto-accept remaining PENDING rows
    NormalizedActivity.objects.filter(batch=batch, status='PENDING').update(
        status='ACCEPTED',
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
        review_note='Auto-accepted on submit',
    )

    batch.status = 'ANALYST_APPROVED'
    batch.reviewed_by = request.user
    batch.reviewed_at = timezone.now()
    batch.analyst_note = request.data.get('analyst_note', '')
    batch.save()
    return Response({'status': 'ANALYST_APPROVED'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def batch_set_in_review_view(request, batch_id):
    profile = request.user.profile
    client = profile.client
    try:
        batch = IngestionBatch.objects.get(id=batch_id, client=client)
    except IngestionBatch.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if batch.status == 'PENDING_REVIEW':
        batch.status = 'IN_REVIEW'
        batch.save()
    return Response({'status': batch.status})


# ── Submission-level analyst endpoints ────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submission_set_in_review_view(request, submission_id):
    from apps.ingestion.models import Submission
    profile = request.user.profile
    client = profile.client
    try:
        submission = Submission.objects.get(id=submission_id, client=client)
    except Submission.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if submission.status == 'PENDING_REVIEW':
        submission.status = 'IN_REVIEW'
        submission.save()
        submission.files.filter(status='PENDING_REVIEW').update(status='IN_REVIEW')
    return Response({'status': submission.status})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submission_analyst_submit_view(request, submission_id):
    from apps.ingestion.models import Submission
    profile = request.user.profile
    client = profile.client
    try:
        submission = Submission.objects.get(id=submission_id, client=client)
    except Submission.DoesNotExist:
        return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    if submission.status not in ('PENDING_REVIEW', 'IN_REVIEW'):
        return Response({'detail': 'Submission not in review'}, status=status.HTTP_400_BAD_REQUEST)

    all_batch_ids = list(submission.files.values_list('id', flat=True))

    flagged_remaining = NormalizedActivity.objects.filter(
        batch_id__in=all_batch_ids, status='FLAGGED'
    ).count()
    if flagged_remaining > 0:
        return Response(
            {'detail': f'{flagged_remaining} flagged rows must be resolved before submitting'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now = timezone.now()
    NormalizedActivity.objects.filter(batch_id__in=all_batch_ids, status='PENDING').update(
        status='ACCEPTED',
        reviewed_by=request.user,
        reviewed_at=now,
        review_note='Auto-accepted on submit',
    )

    submission.files.all().update(
        status='ANALYST_APPROVED',
        reviewed_by=request.user,
        reviewed_at=now,
        analyst_note=request.data.get('analyst_note', ''),
    )

    submission.status = 'ANALYST_APPROVED'
    submission.reviewed_by = request.user
    submission.reviewed_at = now
    submission.analyst_note = request.data.get('analyst_note', '')
    submission.save()
    audit_log(request.user, client, 'SUBMISSION_ANALYST_APPROVED', 'Submission', submission.id,
              {'batch_number': submission.batch_number, 'note': submission.analyst_note})
    return Response({'status': 'ANALYST_APPROVED'})
