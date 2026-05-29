from .models import AuditLog


def log(actor, client, action, target_type='', target_id='', detail=None):
    try:
        AuditLog.objects.create(
            actor=actor,
            client=client,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else '',
            detail=detail or {},
        )
    except Exception:
        pass  # never let audit logging crash the main flow
