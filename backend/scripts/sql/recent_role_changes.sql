-- Who changed whose role, and when (Slice 1.6 check; BR-13).
-- Run with:
--   & "C:\Program Files\PostgreSQL\18\bin\psql.exe" -h localhost -p 5433 -U itam_app -d itam_dev -f backend\scripts\sql\recent_role_changes.sql
-- (password: the development password from backend\.env)
SELECT
    a.id,
    a.created_at                                AS changed_at_utc,
    a.created_at AT TIME ZONE 'Asia/Kolkata'    AS changed_at_india,
    a.actor_user_id                             AS admin_id,
    admin.email                                 AS admin_email,
    target.email                                AS user_email,
    a.before_data ->> 'role'                    AS old_role,
    a.after_data  ->> 'role'                    AS new_role
FROM audit_logs AS a
LEFT JOIN users AS admin  ON admin.id = a.actor_user_id
LEFT JOIN users AS target ON a.entity_type = 'users' AND target.id::text = a.entity_id
WHERE a.action = 'user.role_changed'
ORDER BY a.created_at DESC
LIMIT 20;
