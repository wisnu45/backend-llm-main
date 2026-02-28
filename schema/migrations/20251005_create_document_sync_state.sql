-- Track long-running document sync jobs to avoid duplicates across processes
CREATE TABLE IF NOT EXISTS public.document_sync (
    job_name VARCHAR(64) PRIMARY KEY,
    state VARCHAR(32) NOT NULL,
    trigger_source VARCHAR(32) DEFAULT NULL,
    triggered_by VARCHAR(255) DEFAULT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    finished_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    runtime_seconds DOUBLE PRECISION DEFAULT NULL,
    result JSONB DEFAULT NULL,
    error TEXT DEFAULT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS document_sync_state_idx
    ON public.document_sync (state);
