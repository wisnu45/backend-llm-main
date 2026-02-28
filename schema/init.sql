-- Active: 1757570008208@@127.0.0.1@5432@combiphar-db@public
START TRANSACTION;

CREATE extension IF NOT EXISTS "uuid-ossp";
-- Untuk UUID generation

-- Table untuk menyimpan roles user
CREATE TABLE IF NOT EXISTS roles (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    name VARCHAR(255) NOT NULL, -- Nama role (misalnya admin, user)
    description TEXT DEFAULT NULL, -- Deskripsi role
    is_protected BOOLEAN DEFAULT FALSE, -- Menandai apakah role ini adalah role default (misalnya admin, user)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan terakhir
    CONSTRAINT unique_name UNIQUE (name) -- Menjamin nama role unik
);

-- Table untuk menyimpan settings (features/general)
CREATE TABLE IF NOT EXISTS settings (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    type VARCHAR(64) NOT NULL, -- Tipe setting (misalnya feature, general)
    name VARCHAR(255) NOT NULL, -- Nama setting (misalnya enable_chat, max_upload_size)
    description TEXT DEFAULT NULL, -- Deskripsi setting
    data_type VARCHAR(64) NOT NULL, -- Tipe input (misalnya boolean, text, number, select)
    unit VARCHAR(64) DEFAULT NULL, -- Satuan untuk nilai setting (misalnya MB, menit)
    value TEXT DEFAULT NULL, -- Opsi nilai untuk tipe input select (disimpan sebagai JSON array)
    is_protected BOOLEAN DEFAULT FALSE, -- Menandai apakah setting ini bisa dihapus
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan terakhir
    CONSTRAINT unique_setting_name UNIQUE (name)
);

-- Table untuk menghubungkan roles dengan settings (many-to-many)
CREATE TABLE IF NOT EXISTS roles_settings (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    roles_id UUID NOT NULL REFERENCES roles (id) ON DELETE CASCADE, -- Foreign key ke roles
    settings_id UUID NOT NULL REFERENCES settings (id) ON DELETE CASCADE, -- Foreign key ke settings
    value TEXT NOT NULL, -- Nilai setting untuk role tertentu
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan
    CONSTRAINT roles_settings_unique UNIQUE (roles_id, settings_id) -- Cegah duplikasi pasangan role-setting
);

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    roles_id UUID REFERENCES roles (id), -- Foreign key ke roles
    name VARCHAR(255) NOT NULL, -- Nama lengkap user
    username VARCHAR(255) NOT NULL UNIQUE, -- Username unik untuk login
    password TEXT NOT NULL, -- Menyimpan hash password
    is_portal BOOLEAN DEFAULT FALSE, -- Menandai apakah role ini adalah role portal (dari portal eksternal)
    is_protected BOOLEAN DEFAULT FALSE, -- Menandai apakah user ini dilindungi (tidak bisa dihapus)
    last_login TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu login terakhir
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan terakhir
    CONSTRAINT unique_username UNIQUE (username) -- Menjamin username unik
);

-- Table untuk menyimpan refresh tokens (JWT refresh token, hanya hash jti yang disimpan)
CREATE TABLE IF NOT EXISTS token_refresh (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE, -- Foreign key ke users
    jti VARCHAR(64) NOT NULL, -- JWT ID dari refresh token (jti)
    is_revoked BOOLEAN DEFAULT FALSE, -- Menandai apakah token sudah dicabut
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan terakhir
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Waktu kedaluwarsa token
    CONSTRAINT unique_token_refresh_jti UNIQUE (jti) -- Menjamin jti unik
);

-- Table untuk menyimpan blacklisted JWT tokens (untuk logout)
CREATE TABLE IF NOT EXISTS token_revoked (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    jti VARCHAR(64) NOT NULL, -- JWT ID dari token yang diblacklist (jti)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Waktu kedaluwarsa token
    CONSTRAINT unique_token_revoked_jti UNIQUE (jti) -- Menjamin jti unik
);

-- Chats Table
CREATE TABLE IF NOT EXISTS chats (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    user_id UUID REFERENCES users (id) ON DELETE CASCADE, -- Foreign key ke users
    subject TEXT DEFAULT NULL, -- Menyimpan subjek atau topik percakapan
    pinned BOOLEAN DEFAULT FALSE, -- Menandai apakah percakapan dipin atau tidak
    options JSONB DEFAULT NULL, -- Menyimpan opsi tambahan dalam format JSONB
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL -- Waktu pembaruan terakhir
);

-- Chat Details Table
CREATE TABLE IF NOT EXISTS chat_details (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    chat_id UUID REFERENCES chats (id) ON DELETE CASCADE, -- Foreign key ke chats
    question TEXT NOT NULL, -- Menyimpan pertanyaan dari user
    answer TEXT NOT NULL, -- Menyimpan jawaban dari chatbot
    source_documents TEXT DEFAULT NULL, -- JSON array of source document references
    attachments TEXT DEFAULT NULL, -- JSON array of attachment URLs or file paths
    feedback SMALLINT DEFAULT NULL, -- 1 untuk Like dan -1 untuk Dislike
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL -- Waktu pembaruan terakhir
);

-- ENUM type for source_type in documents table
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_source_type') THEN
        CREATE TYPE document_source_type AS ENUM ('portal', 'admin', 'user', 'website');
    END IF;
END$$;

-- Documents table to support multiple source types and associations
CREATE TABLE IF NOT EXISTS documents (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    chat_detail_id UUID DEFAULT NULL REFERENCES chat_details(id) ON DELETE CASCADE, -- Foreign key ke chat_details (jika dokumen terkait chat)
    source_type document_source_type NOT NULL, -- tipe sumber dokumen: portal, admin, user
    original_filename VARCHAR(255) NOT NULL, -- nama asli saat diunggah
    stored_filename VARCHAR(255) NOT NULL, -- nama unik di disk (uuid.ext)
    mime_type VARCHAR(100) NOT NULL, -- tipe MIME file
    size_bytes BIGINT NOT NULL, -- ukuran file dalam bytes
    metadata JSONB DEFAULT '{}'::jsonb, -- metadata tambahan dalam format JSONB
    storage_path TEXT NOT NULL, -- contoh: data/documents/portal/uuid.pdf, data/documents/admin/uuid.pdf, data/documents/chat/<chat_id>/uuid.pdf
    uploaded_by UUID NULL REFERENCES users(id) ON DELETE SET NULL, -- user yang mengunggah dokumen (jika kosong, berarti sistem)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan terakhir
    CONSTRAINT unique_stored_filename UNIQUE (stored_filename) -- Menjamin stored_filename unik
);

CREATE TABLE IF NOT EXISTS users_documents (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY, -- Primary key
    users_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE, -- Foreign key ke users
    documents_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE, -- Foreign key ke documents
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, -- Waktu pembuatan
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu pembaruan
    CONSTRAINT users_documents_unique UNIQUE (users_id, documents_id) -- Cegah duplikasi pasangan users-documents
);

CREATE TABLE IF NOT EXISTS document_sync (
    job_name VARCHAR(64) PRIMARY KEY, -- Nama unique untuk job sync (misal: portal_documents)
    state VARCHAR(32) NOT NULL, -- Status saat ini: idle, running, succeeded, failed
    trigger_source VARCHAR(32) DEFAULT NULL, -- Sumber trigger: api, cron, startup, dll
    triggered_by VARCHAR(255) DEFAULT NULL, -- Identifier pengguna/actor yang men-trigger
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu mulai sinkronisasi
    finished_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu selesai sinkronisasi
    runtime_seconds DOUBLE PRECISION DEFAULT NULL, -- Durasi eksekusi dalam detik
    result JSONB DEFAULT NULL, -- Ringkasan hasil sinkronisasi (daftar file, dll)
    error TEXT DEFAULT NULL, -- Pesan error jika gagal
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP -- Waktu update terakhir
);

-- Sync logs (aggregate + per-item details)
-- Note: migrations still apply for existing DB volumes; this is for fresh DB init.
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY,
    sync_type VARCHAR(32) NOT NULL DEFAULT 'portal', -- portal, website, manual
    status VARCHAR(32) NOT NULL, -- running, success, partial_success, failed
    total_documents INTEGER DEFAULT 0,
    successful_documents INTEGER DEFAULT 0,
    failed_documents INTEGER DEFAULT 0,
    total_website_documents INTEGER DEFAULT 0,
    successful_website_documents INTEGER DEFAULT 0,
    failed_website_documents INTEGER DEFAULT 0,
    trigger_source VARCHAR(32) DEFAULT NULL,
    triggered_by VARCHAR(255) DEFAULT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    runtime_seconds DOUBLE PRECISION DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS sync_log_details (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY,
    sync_log_id UUID NOT NULL REFERENCES sync_logs (id) ON DELETE CASCADE,
    item_type VARCHAR(32) NOT NULL DEFAULT 'document',
    item_url TEXT DEFAULT NULL,
    item_source VARCHAR(255) DEFAULT NULL,
    document_title VARCHAR(255) DEFAULT NULL,
    document_filename VARCHAR(255) DEFAULT NULL,
    document_id VARCHAR(255) DEFAULT NULL,
    status VARCHAR(32) NOT NULL, -- success, failed
    error_message TEXT DEFAULT NULL,
    file_size BIGINT DEFAULT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_details_chat_id ON chat_details(chat_id);
CREATE INDEX IF NOT EXISTS idx_chat_details_created_at ON chat_details(created_at);
CREATE INDEX IF NOT EXISTS idx_users_roles_id ON users(roles_id);
CREATE INDEX IF NOT EXISTS idx_roles_name_unique ON roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_settings_roles_id ON roles_settings(roles_id);
CREATE INDEX IF NOT EXISTS idx_roles_settings_settings_id ON roles_settings(settings_id);
CREATE INDEX IF NOT EXISTS idx_token_refresh_user_id ON token_refresh(user_id);
CREATE INDEX IF NOT EXISTS idx_token_refresh_expires_at ON token_refresh(expires_at);
CREATE INDEX IF NOT EXISTS idx_token_revoked_expires_at ON token_revoked(expires_at);
CREATE INDEX IF NOT EXISTS document_sync_state_idx ON document_sync(state);

CREATE INDEX IF NOT EXISTS idx_sync_logs_sync_type ON sync_logs(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started_at ON sync_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_sync_logs_triggered_by ON sync_logs(triggered_by);

CREATE INDEX IF NOT EXISTS idx_sync_log_details_sync_log_id ON sync_log_details(sync_log_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_status ON sync_log_details(status);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_processed_at ON sync_log_details(processed_at);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_item_type ON sync_log_details(item_type);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_item_url ON sync_log_details(item_url);

COMMIT;
