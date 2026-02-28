-- Seed configuration to restrict document sync access to specific usernames
INSERT INTO settings (type, name, description, data_type, unit, value, is_protected)
VALUES (
    'general',
    'document_sync_allowed_users',
    'Daftar username yang diizinkan menjalankan sinkronisasi dokumen portal & website',
    'array',
    NULL,
    '["subhan.pradana"]',
    TRUE
)
ON CONFLICT (name) DO UPDATE
SET
    type = EXCLUDED.type,
    description = EXCLUDED.description,
    data_type = EXCLUDED.data_type,
    unit = EXCLUDED.unit,
    value = EXCLUDED.value,
    is_protected = EXCLUDED.is_protected;

-- Preview current configuration for double-checking
SELECT name, value
FROM settings
WHERE name = 'document_sync_allowed_users';
