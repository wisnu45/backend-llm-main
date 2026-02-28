-- SQL script untuk menambahkan message error baru "no_information" ke settings table
-- Jalankan script ini untuk menambah message baru yang digunakan ketika
-- benar-benar tidak ada informasi ditemukan dari semua sources

-- Insert the new message in a way that matches the `settings` table schema
-- `type` and `data_type` are NOT NULL in the schema, so include them
INSERT INTO settings (type, name, description, data_type, unit, value, is_protected) 
VALUES (
    'general',
    'message_no_information',
    'Message yang ditampilkan ketika sistem tidak menemukan informasi sama sekali dari semua sources (dokumen, website, web search)',
    'string',
    NULL,
    'Maaf, saya tidak menemukan informasi yang relevan untuk pertanyaan Anda. Silakan coba dengan pertanyaan yang berbeda atau lebih spesifik.',
    true
)
ON CONFLICT (name) 
DO UPDATE SET 
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    type = EXCLUDED.type,
    data_type = EXCLUDED.data_type,
    is_protected = EXCLUDED.is_protected;

-- Verifikasi message telah tersimpan
SELECT name, value, description 
FROM settings 
WHERE name LIKE 'message_%'
ORDER BY name;