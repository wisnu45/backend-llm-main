-- Grant menu-type settings to admin role
INSERT INTO roles_settings (roles_id, settings_id, value)
SELECT r.id AS roles_id,
       s.id AS settings_id,
       true
FROM roles r
CROSS JOIN settings s
WHERE s.type = 'menu'
AND r.name = 'admin'
ON CONFLICT (roles_id, settings_id) DO NOTHING;
