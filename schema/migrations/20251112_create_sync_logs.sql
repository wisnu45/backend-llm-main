-- Migration: Create sync logs tables for document synchronization tracking
-- Date: 2025-11-12
-- Description: Create tables to track document sync operations and individual document results

START TRANSACTION;

-- Table untuk menyimpan log sinkronisasi dokumen
CREATE TABLE IF NOT EXISTS sync_logs (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY,
    sync_type VARCHAR(32) NOT NULL DEFAULT 'portal', -- Tipe sync: portal, website, manual
    status VARCHAR(32) NOT NULL, -- Status: running, success, partial_success, failed
    total_documents INTEGER DEFAULT 0, -- Total dokumen yang diproses
    successful_documents INTEGER DEFAULT 0, -- Dokumen yang berhasil disinkronisasi
    failed_documents INTEGER DEFAULT 0, -- Dokumen yang gagal disinkronisasi
    trigger_source VARCHAR(32) DEFAULT NULL, -- Sumber trigger: api, cron, startup, dll
    triggered_by VARCHAR(255) DEFAULT NULL, -- Identifier pengguna/actor yang men-trigger
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, -- Waktu mulai sinkronisasi
    finished_at TIMESTAMP WITH TIME ZONE DEFAULT NULL, -- Waktu selesai sinkronisasi
    runtime_seconds DOUBLE PRECISION DEFAULT NULL, -- Durasi eksekusi dalam detik
    error_message TEXT DEFAULT NULL, -- Pesan error global jika ada
    metadata JSONB DEFAULT '{}'::jsonb, -- Metadata tambahan (hasil detail, dll)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Table untuk menyimpan detail hasil sinkronisasi per dokumen
CREATE TABLE IF NOT EXISTS sync_log_details (
    id UUID DEFAULT uuid_generate_v4() NOT NULL PRIMARY KEY,
    sync_log_id UUID NOT NULL REFERENCES sync_logs (id) ON DELETE CASCADE,
    document_title VARCHAR(255) DEFAULT NULL, -- Judul dokumen dari metadata
    document_filename VARCHAR(255) DEFAULT NULL, -- Nama file asli
    document_id VARCHAR(255) DEFAULT NULL, -- ID dokumen dari portal atau sistem
    status VARCHAR(32) NOT NULL, -- Status: success, failed
    error_message TEXT DEFAULT NULL, -- Pesan error spesifik untuk dokumen ini
    file_size BIGINT DEFAULT NULL, -- Ukuran file dalam bytes
    metadata JSONB DEFAULT '{}'::jsonb, -- Metadata tambahan dokumen
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes untuk performa yang lebih baik
CREATE INDEX IF NOT EXISTS idx_sync_logs_sync_type ON sync_logs(sync_type);
CREATE INDEX IF NOT EXISTS idx_sync_logs_status ON sync_logs(status);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started_at ON sync_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_sync_logs_triggered_by ON sync_logs(triggered_by);

CREATE INDEX IF NOT EXISTS idx_sync_log_details_sync_log_id ON sync_log_details(sync_log_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_status ON sync_log_details(status);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_processed_at ON sync_log_details(processed_at);

COMMIT;