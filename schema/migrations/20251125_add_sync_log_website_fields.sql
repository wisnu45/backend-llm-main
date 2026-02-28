-- Migration: Add website sync logging fields
-- Date: 2025-11-25
-- Description: Extend sync log tables to capture website sync results.

START TRANSACTION;

-- Aggregate counters for website sync results
ALTER TABLE sync_logs
    ADD COLUMN IF NOT EXISTS total_website_documents INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS successful_website_documents INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS failed_website_documents INTEGER DEFAULT 0;

-- Detail records: allow logging both document and website items
ALTER TABLE sync_log_details
    ADD COLUMN IF NOT EXISTS item_type VARCHAR(32) NOT NULL DEFAULT 'document',
    ADD COLUMN IF NOT EXISTS item_url TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS item_source VARCHAR(255) DEFAULT NULL;

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_sync_log_details_item_type ON sync_log_details(item_type);
CREATE INDEX IF NOT EXISTS idx_sync_log_details_item_url ON sync_log_details(item_url);

COMMIT;
