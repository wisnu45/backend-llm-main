-- Migration: add 'website' value to document_source_type enum
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'document_source_type'
          AND e.enumlabel = 'website'
    ) THEN
        ALTER TYPE document_source_type ADD VALUE 'website';
    END IF;
END$$;
