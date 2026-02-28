#!/usr/bin/env python3
"""Script to ingest Combiphar-affiliated website content on container startup."""
import logging
import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def configure_logging() -> None:
    """Configure logging outputs for website ingestion."""
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

    file_handler = logging.FileHandler(os.path.join(log_dir, 'pull_websites.log'))
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter('%(asctime)s | (%(name)s) | [%(levelname)s] | %(message)s'))
    root_logger.addHandler(file_handler)

    configure_logging._configured = True


configure_logging()

from app.utils.website_pull import pull_combiphar_websites


def wait_for_dependencies() -> bool:
    """Ensure PostgreSQL is available before ingestion starts."""
    from app.utils.database import getConnection

    max_attempts = 30
    retry_delay = 2

    for attempt in range(max_attempts):
        try:
            logging.info(f"🔄 Checking if PostgreSQL database is available (attempt {attempt + 1}/{max_attempts})...")
            conn = getConnection()
            if conn:
                conn.close()
                logging.info("✅ PostgreSQL database is available")
                return True
            logging.warning("⚠️ Database connection returned None")
        except Exception as exc:
            logging.warning(f"⚠️ Error checking PostgreSQL availability: {exc}")
        time.sleep(retry_delay)

    logging.error("❌ PostgreSQL database did not become available within the timeout period")
    return False


if __name__ == "__main__":
    logging.info("Starting Combiphar website ingestion...")

    if not wait_for_dependencies():
        logging.error("❌ Required dependencies not available. Exiting.")
        sys.exit(1)

    try:
        result = pull_combiphar_websites()
        urls = result.get("ingested_urls", []) if isinstance(result, dict) else []
        summary = result.get("summary", {}) if isinstance(result, dict) else {}

        logging.info(f"📝 Website ingestion summary: {summary}")
        logging.info(f"✅ Ingested {len(urls)} website pages")
    except Exception as exc:
        logging.error(f"❌ Error ingesting websites: {exc}")
        sys.exit(1)
