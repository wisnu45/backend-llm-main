#!/usr/bin/env python3
"""
Script to run the pull_from_portal_logic on container startup.
"""
import logging
import os
import sys

# Ensure project root is in Python path for proper module imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def configure_logging() -> None:
    """Configure root logging once per interpreter to prevent duplicate output."""
    if getattr(configure_logging, "_configured", False):
        return

    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(logging.Formatter('(%(name)s) | [%(levelname)s] | %(message)s'))
    root_logger.addHandler(stdout_handler)

    file_handler = logging.FileHandler(os.path.join(log_dir, 'pull.log'))
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('%(asctime)s | (%(name)s) | [%(levelname)s] | %(message)s'))
    root_logger.addHandler(file_handler)

    configure_logging._configured = True


configure_logging()

# Load reusable sync runner
from app.services.document_sync_manager import DocumentSyncManager

if __name__ == "__main__":
    logging.info("Starting portal document pull...")

    try:
        started, status = DocumentSyncManager.run_blocking(
            trigger_source=os.getenv("DOCUMENT_SYNC_TRIGGER_SOURCE", "startup"),
            triggered_by=os.getenv("DOCUMENT_SYNC_TRIGGERED_BY", "sync-docs-container"),
            wait_for_db=True,
        )

        if not started:
            logging.info(
                "Portal document sync skipped because another run is active "
                "(state=%s, trigger=%s, by=%s)",
                status.get("state"),
                status.get("trigger_source"),
                status.get("triggered_by"),
            )
            sys.exit(0)

        result_payload = status.get("result") or {}
        downloaded_files = result_payload.get("downloaded_files", [])
        ingested_urls = result_payload.get("ingested_urls", [])

        logging.info(
            "Portal document sync completed with state=%s (files=%s, websites=%s)",
            status.get("state"),
            len(downloaded_files),
            len(ingested_urls),
        )
        if downloaded_files:
            logging.info("Downloaded files: %s", downloaded_files)
        if ingested_urls:
            logging.info("Ingested website URLs: %s", ingested_urls)

    except Exception as exc:
        # Treat portal pull errors as non-fatal for the container run:
        # log the error but exit with success so the job is effectively "skipped".
        logging.error(f"Error pulling from portal: {exc}")
        sys.exit(0)
