-- Assign feature-type settings to every role
INSERT INTO roles_settings (roles_id, settings_id, value)
SELECT r.id AS roles_id,
       s.id AS settings_id,
       COALESCE(s.value, 'true')::text AS value
FROM roles r
CROSS JOIN settings s
WHERE s.type = 'feature'
ON CONFLICT (roles_id, settings_id) DO NOTHING;
