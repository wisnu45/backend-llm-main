#!/usr/bin/env python3
"""
Script to run local document embedding processing.
Processes documents from the local filesystem and embeds them into the vector store.
"""
import logging
import os
import sys
import argparse
import time

# Ensure project root is in Python path for proper module imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables using centralized env loader
from app.utils.env_loader import env_load

# Load local embedding logic
from app.utils.local_embedding import embed_local_documents_logic, embed_specific_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def wait_for_dependencies():
    """Wait for required services to be available before starting."""
    from app.utils.database import getConnection

    max_attempts = 30
    retry_delay = 2

    for attempt in range(max_attempts):
        try:
            logging.info(f"🔄 Checking if PostgreSQL database is available (attempt {attempt + 1}/{max_attempts})...")
            
            # Test database connection
            conn = getConnection()
            if conn:
                conn.close()
                logging.info("✅ PostgreSQL database is available")
                return True
            else:
                logging.warning(f"⚠️ PostgreSQL database not yet available (attempt {attempt + 1}/{max_attempts})")
                time.sleep(retry_delay)

        except Exception as e:
            logging.warning(f"⚠️ Error checking PostgreSQL database availability: {e}")
            time.sleep(retry_delay)

    logging.error("❌ PostgreSQL database did not become available within the timeout period")
    return False

def main():
    """Main function to run local document embedding."""
    parser = argparse.ArgumentParser(description="Process and embed local documents")
    parser.add_argument(
        "--path", 
        default="data/documents", 
        help="Path to documents directory (default: data/documents)"
    )
    parser.add_argument(
        "--source-type", 
        default="portal", 
        help="Source type for documents (default: portal)"
    )
    parser.add_argument(
        "--skip-existing", 
        action="store_true", 
        default=True,
        help="Skip files that already exist in database (default: True)"
    )
    parser.add_argument(
        "--no-skip-existing", 
        action="store_false", 
        dest="skip_existing",
        help="Process all files even if they exist in database"
    )
    parser.add_argument(
        "--files", 
        nargs="+", 
        help="Specific files to process (relative paths from base directory)"
    )
    parser.add_argument(
        "--extensions", 
        nargs="+", 
        default=['.pdf', '.txt', '.doc', '.docx', '.png', '.jpg', '.jpeg'],
        help="Allowed file extensions (default: .pdf .txt .doc .docx .png .jpg .jpeg)"
    )

    args = parser.parse_args()

    logging.info("🚀 Starting local document embedding process...")
    logging.info(f"📁 Documents path: {args.path}")
    logging.info(f"🏷️ Source type: {args.source_type}")
    logging.info(f"⏭️ Skip existing: {args.skip_existing}")
    logging.info(f"📄 Allowed extensions: {args.extensions}")

    # Wait for dependencies to be available
    if not wait_for_dependencies():
        logging.error("❌ Required dependencies not available. Exiting.")
        exit(1)

    try:
        if args.files:
            # Process specific files
            logging.info(f"Processing specific files: {args.files}")
            result = embed_specific_files(
                file_paths=args.files,
                source_type=args.source_type,
                base_path=args.path
            )
        else:
            # Process all documents in directory
            result = embed_local_documents_logic(
                documents_path=args.path,
                source_type=args.source_type,
                skip_existing=args.skip_existing,
                allowed_extensions=args.extensions
            )

        # Log results
        processed_files = result.get("processed_files", [])
        skipped_files = result.get("skipped_files", [])
        errors = result.get("errors", [])
        summary = result.get("summary", {})

        logging.info(f"📊 Processing completed!")
        logging.info(f"   ✅ Processed {len(processed_files)} files")
        
        if skipped_files:
            logging.info(f"   ⏭️ Skipped {len(skipped_files)} files")
        
        if errors:
            logging.warning(f"   ❌ {len(errors)} errors occurred")
            for error in errors:
                logging.error(f"      • {error}")

        # Log processed files
        if processed_files:
            logging.info("📄 Successfully processed files:")
            for file in processed_files:
                logging.info(f"   • {file}")

        # Log summary
        if summary:
            logging.info(f"📈 Summary: {summary}")

        # Exit with error code if there were errors
        if errors:
            exit(1)

    except Exception as e:
        logging.error(f"❌ Error during local document embedding: {e}")
        exit(1)

if __name__ == "__main__":
    main()