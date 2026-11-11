"""Audit log: a permanent "who did what, when" record (BR-13, PRD sections 9 and 10).

Use it from any service with:

    from app.modules.audit import service as audit
    from app.modules.audit.actions import AuditAction

    audit.record(db, actor=current_user, action=AuditAction.USER_ROLE_CHANGED,
                 entity=user, before={...}, after={...})

The admin screen to browse it comes in Slice 8.1.
"""
