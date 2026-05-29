from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import AuditLog


def log_to_dict(entry):
    return {
        'id': str(entry.id),
        'timestamp': entry.timestamp.isoformat(),
        'actor': entry.actor.username if entry.actor else 'system',
        'action': entry.action,
        'target_type': entry.target_type,
        'target_id': entry.target_id,
        'detail': entry.detail,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def audit_log_view(request):
    client = request.user.profile.client
    qs = AuditLog.objects.filter(client=client).select_related('actor')

    action = request.query_params.get('action')
    if action:
        qs = qs.filter(action=action)

    actor = request.query_params.get('actor')
    if actor:
        qs = qs.filter(actor__username=actor)

    target_type = request.query_params.get('target_type')
    if target_type:
        qs = qs.filter(target_type=target_type)

    paginator = PageNumberPagination()
    paginator.page_size = 50
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response([log_to_dict(e) for e in page])
