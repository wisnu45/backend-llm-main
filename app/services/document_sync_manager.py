"""
Utilities for running and managing the portal document synchronization job.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from psycopg2.extras import Json

from app.utils.database import getConnection
from app.utils.portal_pull import pull_from_portal_logic
from app.utils.website_pull import pull_combiphar_websites
from app.utils.sync_logger import SyncLogger

DEFAULT_MAX_ATTEMPTS = 30
DEFAULT_RETRY_DELAY = 2
DEFAULT_JOB_NAME = os.getenv("DOCUMENT_SYNC_JOB_NAME", "portal_documents_sync")


def wait_for_dependencies(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    retry_delay: int = DEFAULT_RETRY_DELAY,
) -> bool:
    """
    Ensure required services (e.g. PostgreSQL) are reachable before running the sync.

    Returns:
        bool: True when dependencies are available, otherwise False after timeout.
    """
    for attempt in range(max_attempts):
        try:
            logging.info(
                "🔄 Checking if PostgreSQL database is available (attempt %s/%s)...",
                attempt + 1,
                max_attempts,
            )
            conn = getConnection()
            if conn:
                conn.close()
                logging.info("✅ PostgreSQL database is available")
                return True
        except Exception as exc:
            logging.warning(
                "⚠️ Error checking PostgreSQL database availability: %s", exc
            )

        time.sleep(retry_delay)

    logging.error(
        "❌ PostgreSQL database did not become available within the timeout period"
    )
    return False


def run_portal_sync(wait_for_db: bool = True, sync_logger: Optional[SyncLogger] = None) -> Dict[str, Any]:
    """
    Execute the portal + website synchronization logic with optional dependency checks.

    Args:
        wait_for_db (bool): Wait for database readiness before running the sync.
        sync_logger (Optional[SyncLogger]): Logger instance to track sync results

    Returns:
        Dict[str, Any]: Combined result dictionary with portal and website ingestion details.
    """
    if wait_for_db and not wait_for_dependencies():
        raise RuntimeError("Required dependencies not available. Aborting portal sync.")

    logging.info("Starting portal document synchronization job...")
    portal_result = pull_from_portal_logic(sync_logger=sync_logger)

    if not isinstance(portal_result, dict):
        logging.warning(
            "pull_from_portal_logic returned non-dict result (%s); normalizing output",
            type(portal_result),
        )
        portal_result = {"downloaded_files": [], "raw_result": portal_result}

    portal_result.setdefault("downloaded_files", [])

    logging.info("Starting website content embedding job...")
    website_result = pull_combiphar_websites(sync_logger=sync_logger)

    if not isinstance(website_result, dict):
        logging.warning(
            "pull_combiphar_websites returned non-dict result (%s); normalizing output",
            type(website_result),
        )
        website_result = {
            "ingested_urls": [],
            "raw_result": website_result,
        }

    website_result.setdefault("ingested_urls", [])

    combined_result = {
        "portal": portal_result,
        "website": website_result,
        "downloaded_files": portal_result.get("downloaded_files", []),
        "ingested_urls": website_result.get("ingested_urls", []),
    }

    logging.info(
        "Completed document sync tasks (portal_files=%s, website_urls=%s)",
        len(combined_result["downloaded_files"]),
        len(combined_result["ingested_urls"]),
    )

    return combined_result


class DocumentSyncManager:
    """
    Thread-safe manager that allows triggering portal sync jobs without overlap.
    """

    JOB_NAME = DEFAULT_JOB_NAME
    TABLE_NAME = "document_sync"

    _lock = threading.Lock()
    _thread: Optional[threading.Thread] = None
    _status: Dict[str, Any] = {
        "job": JOB_NAME,
        "state": "idle",
        "trigger_source": None,
        "triggered_by": None,
        "started_at": None,
        "finished_at": None,
        "runtime_seconds": None,
        "result": None,
        "error": None,
        "updated_at": None,
        "_start_monotonic": None,
    }
    _table_initialized = False

    @classmethod
    def trigger(
        cls,
        triggered_by: Optional[str] = None,
        trigger_source: Optional[str] = "api",
        wait_for_db: bool = False,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Attempt to start the sync job in a background thread.

        Returns:
            Tuple[bool, Dict[str, Any]]:
                - bool indicates whether a new run was started.
                - Dict provides the current job status snapshot.
        """
        source_label = cls._normalize_trigger_source(trigger_source)
        triggered_by_value = cls._normalize_triggered_by(triggered_by)

        with cls._lock:
            if cls._thread and cls._thread.is_alive():
                logging.info("Document sync requested but already running (thread).")
                return False, cls.status()

            claimed, db_state = cls._claim_job(source_label, triggered_by_value)
            if not claimed:
                logging.info(
                    "Document sync request via %s ignored because another run is active.",
                    source_label,
                )
                return False, db_state

            cls._status.update(db_state)
            cls._status["state"] = "running"
            cls._status["trigger_source"] = source_label
            cls._status["triggered_by"] = triggered_by_value
            cls._status["result"] = None
            cls._status["error"] = None
            cls._status["_start_monotonic"] = time.monotonic()

            cls._thread = threading.Thread(
                target=cls._run_job,
                args=(wait_for_db, source_label, triggered_by_value),
                name="DocumentPortalSyncJob",
                daemon=True,
            )
            cls._thread.start()

        return True, cls.status()

    @classmethod
    def run_blocking(
        cls,
        trigger_source: Optional[str],
        triggered_by: Optional[str] = None,
        wait_for_db: bool = True,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Run the sync job synchronously in the current process.

        Returns:
            Tuple[bool, Dict[str, Any]]:
                - bool indicates whether this call executed the job (False when skipped).
                - Dict provides the final status snapshot (or current status if skipped).
        """
        source_label = cls._normalize_trigger_source(trigger_source)
        triggered_by_value = cls._normalize_triggered_by(triggered_by)

        claimed, _ = cls._claim_job(source_label, triggered_by_value)
        if not claimed:
            logging.info(
                "Document sync via %s skipped because another run is active.",
                source_label,
            )
            return False, cls.status()

        # Initialize sync logger
        sync_logger = SyncLogger()
        sync_log_id = sync_logger.start_sync_log(
            sync_type='portal',
            trigger_source=source_label,
            triggered_by=triggered_by_value
        )

        start_monotonic = time.monotonic()
        try:
            result = run_portal_sync(wait_for_db=wait_for_db, sync_logger=sync_logger)
            runtime = round(time.monotonic() - start_monotonic, 3)
            
            # Finish sync log
            if sync_log_id:
                sync_logger.finish_sync_log(
                    status='success',
                    runtime_seconds=runtime,
                    additional_metadata={
                        'trigger_source': source_label,
                        'triggered_by': triggered_by_value,
                        'result': result
                    }
                )
            
            final_state = cls._finalize_job("succeeded", runtime, result, None)
            return True, final_state
        except Exception as exc:
            runtime = round(time.monotonic() - start_monotonic, 3)

            # Finish sync log with failure but do not propagate exception to callers.
            if sync_log_id:
                sync_logger.finish_sync_log(
                    status='failed',
                    error_message=str(exc),
                    runtime_seconds=runtime,
                    additional_metadata={
                        'trigger_source': source_label,
                        'triggered_by': triggered_by_value
                    }
                )

            try:
                final_state = cls._finalize_job("failed", runtime, None, str(exc))
            except Exception:
                logging.exception(
                    "Failed to persist document sync failure details to the database"
                )
                final_state = cls._base_status()

            return True, final_state

    @classmethod
    def status(cls) -> Dict[str, Any]:
        """Return a snapshot of the current sync job status."""
        try:
            db_status = cls._fetch_status()
        except Exception as exc:
            logging.error("Failed to fetch document sync status: %s", exc)
            db_status = cls._base_status()

        with cls._lock:
            local_status = dict(cls._status)

        if local_status.get("state") == "running":
            start_marker = local_status.get("_start_monotonic")
            if start_marker is not None:
                db_status["runtime_seconds"] = round(
                    max(0.0, time.monotonic() - start_marker), 3
                )
            db_status.update({k: v for k, v in local_status.items() if k != "_start_monotonic"})

        db_status.pop("_start_monotonic", None)
        return db_status

    @classmethod
    def _run_job(
        cls,
        wait_for_db: bool,
        trigger_source: str,
        triggered_by: Optional[str],
    ) -> None:
        start_monotonic = time.monotonic()
        final_state = "succeeded"
        sync_log_status = "success"
        result: Optional[Dict[str, Any]] = None
        error_message: Optional[str] = None

        # Initialize sync logger
        sync_logger = SyncLogger()
        sync_log_id = sync_logger.start_sync_log(
            sync_type='portal',
            trigger_source=trigger_source,
            triggered_by=triggered_by
        )

        try:
            result = run_portal_sync(wait_for_db=wait_for_db, sync_logger=sync_logger)
        except Exception as exc:  # pragma: no cover - protective logging
            final_state = "failed"
            sync_log_status = "failed"
            error_message = str(exc)
            logging.exception("Document sync job failed during execution")

        runtime = round(time.monotonic() - start_monotonic, 3)
        
        # Finish sync log
        if sync_log_id:
            sync_logger.finish_sync_log(
                status=sync_log_status,
                error_message=error_message,
                runtime_seconds=runtime,
                additional_metadata={
                    'trigger_source': trigger_source,
                    'triggered_by': triggered_by,
                    'result': result
                }
            )
        
        try:
            db_state = cls._finalize_job(final_state, runtime, result, error_message)
        except Exception:
            logging.exception("Failed to persist document sync job result")
            db_state = cls._base_status()
            db_state.update(
                {
                    "state": final_state,
                    "trigger_source": trigger_source,
                    "triggered_by": triggered_by,
                    "runtime_seconds": runtime,
                    "result": result,
                    "error": error_message,
                }
            )

        with cls._lock:
            cls._status.update(db_state)
            cls._status["_start_monotonic"] = None
            cls._thread = None

    # Database helpers -----------------------------------------------------

    @classmethod
    def _ensure_table(cls) -> None:
        if cls._table_initialized:
            return

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {cls.TABLE_NAME} (
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
        """
        index_sql = f"""
        CREATE INDEX IF NOT EXISTS {cls.TABLE_NAME}_state_idx
            ON {cls.TABLE_NAME} (state);
        """

        cls._execute(create_table_sql)
        cls._execute(index_sql)
        cls._table_initialized = True

    @classmethod
    def _claim_job(
        cls,
        trigger_source: str,
        triggered_by: Optional[str],
    ) -> Tuple[bool, Dict[str, Any]]:
        cls._ensure_table()

        query = f"""
        INSERT INTO {cls.TABLE_NAME} (
            job_name, state, trigger_source, triggered_by,
            started_at, finished_at, runtime_seconds, result, error, updated_at
        )
        VALUES (%s, 'running', %s, %s, NOW(), NULL, NULL, NULL, NULL, NOW())
        ON CONFLICT (job_name) DO UPDATE
        SET state = 'running',
            trigger_source = EXCLUDED.trigger_source,
            triggered_by = EXCLUDED.triggered_by,
            started_at = NOW(),
            finished_at = NULL,
            runtime_seconds = NULL,
            result = NULL,
            error = NULL,
            updated_at = NOW()
        WHERE {cls.TABLE_NAME}.state <> 'running'
        RETURNING job_name, state, trigger_source, triggered_by,
                  started_at, finished_at, runtime_seconds, result, error, updated_at;
        """

        rows, columns = cls._execute(
            query,
            (cls.JOB_NAME, trigger_source, triggered_by),
        )

        if rows:
            return True, cls._row_to_status(rows[0], columns)

        return False, cls._fetch_status()

    @classmethod
    def _finalize_job(
        cls,
        state: str,
        runtime_seconds: float,
        result: Optional[Dict[str, Any]],
        error: Optional[str],
    ) -> Dict[str, Any]:
        cls._ensure_table()

        json_result = Json(result) if result is not None else None

        query = f"""
        UPDATE {cls.TABLE_NAME}
        SET state = %s,
            finished_at = NOW(),
            runtime_seconds = %s,
            result = %s,
            error = %s,
            updated_at = NOW()
        WHERE job_name = %s
        RETURNING job_name, state, trigger_source, triggered_by,
                  started_at, finished_at, runtime_seconds, result, error, updated_at;
        """

        rows, columns = cls._execute(
            query,
            (state, runtime_seconds, json_result, error, cls.JOB_NAME),
        )

        if not rows:
            raise RuntimeError("Failed to update document sync state; no rows affected")

        return cls._row_to_status(rows[0], columns)

    @classmethod
    def _fetch_status(cls) -> Dict[str, Any]:
        cls._ensure_table()
        query = f"""
        SELECT job_name, state, trigger_source, triggered_by,
               started_at, finished_at, runtime_seconds, result, error, updated_at
        FROM {cls.TABLE_NAME}
        WHERE job_name = %s
        LIMIT 1;
        """

        rows, columns = cls._execute(query, (cls.JOB_NAME,))
        if not rows:
            return cls._base_status()

        return cls._row_to_status(rows[0], columns)

    @staticmethod
    def _execute(query: str, params: Optional[Tuple[Any, ...]] = None):
        conn = None
        cursor = None
        try:
            conn = getConnection()
            cursor = conn.cursor()
            cursor.execute(query, params or ())

            rows = []
            columns: Tuple[str, ...] = ()
            if cursor.description:
                rows = cursor.fetchall()
                columns = tuple(desc[0] for desc in cursor.description)

            conn.commit()
            return rows, columns
        except Exception:
            if conn:
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # Utility helpers ------------------------------------------------------

    @classmethod
    def _base_status(cls) -> Dict[str, Any]:
        return {
            "job": cls.JOB_NAME,
            "state": "idle",
            "trigger_source": None,
            "triggered_by": None,
            "started_at": None,
            "finished_at": None,
            "runtime_seconds": None,
            "result": None,
            "error": None,
            "updated_at": None,
        }

    @classmethod
    def _row_to_status(cls, row: Tuple[Any, ...], columns: Optional[Tuple[str, ...]]) -> Dict[str, Any]:
        data = dict(zip(columns or [], row))

        status = cls._base_status()
        status["job"] = data.get("job_name", cls.JOB_NAME)
        status["state"] = data.get("state", status["state"])
        status["trigger_source"] = data.get("trigger_source", status["trigger_source"])
        status["triggered_by"] = data.get("triggered_by", status["triggered_by"])
        status["runtime_seconds"] = (
            float(data["runtime_seconds"]) if data.get("runtime_seconds") is not None else None
        )
        status["result"] = data.get("result")
        status["error"] = data.get("error")

        started_at = data.get("started_at")
        finished_at = data.get("finished_at")
        updated_at = data.get("updated_at")

        status["started_at"] = (
            started_at.isoformat() if isinstance(started_at, datetime) else None
        )
        status["finished_at"] = (
            finished_at.isoformat() if isinstance(finished_at, datetime) else None
        )
        status["updated_at"] = (
            updated_at.isoformat() if isinstance(updated_at, datetime) else None
        )

        return status

    @staticmethod
    def _normalize_trigger_source(value: Optional[str]) -> str:
        if value is None:
            return "unknown"
        normalized = str(value).strip().lower()
        return normalized or "unknown"

    @staticmethod
    def _normalize_triggered_by(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = str(value).strip()
        return trimmed or None
