"""
Portal pull utilities for fetching and processing documents from Combiphar portal.
"""
import os
import requests
import logging
import json
import uuid

from datetime import datetime, timezone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .database import safe_db_query
from .portal import create_user_token
from .pgvectorstore import get_vectorstore
from .document import (
    validate_file_content,
    extract_text_from_document,
    validate_document_exist_db,
)
from .time_provider import get_current_datetime

DEFAULT_DOWNLOAD_TIMEOUT = 60
PORTAL_DOWNLOAD_MAX_RETRIES = 3

def _get_portal_download_timeout():
    """Fetch configurable document download timeout with safe fallback."""
    env_value = os.getenv("PORTAL_DOWNLOAD_TIMEOUT")
    if not env_value:
        return DEFAULT_DOWNLOAD_TIMEOUT

    try:
        timeout_value = float(env_value)
    except ValueError:
        logging.warning(
            "Invalid PORTAL_DOWNLOAD_TIMEOUT '%s', falling back to %s seconds",
            env_value,
            DEFAULT_DOWNLOAD_TIMEOUT,
        )
        return DEFAULT_DOWNLOAD_TIMEOUT

    if timeout_value <= 0:
        logging.warning(
            "Non-positive PORTAL_DOWNLOAD_TIMEOUT '%s', falling back to %s seconds",
            env_value,
            DEFAULT_DOWNLOAD_TIMEOUT,
        )
        return DEFAULT_DOWNLOAD_TIMEOUT

    return timeout_value


def _download_with_retry(url, timeout, max_retries=PORTAL_DOWNLOAD_MAX_RETRIES):
    """Download helper that retries on timeout up to max_retries times."""
    for attempt in range(1, max_retries + 1):
        try:
            return requests.get(url, timeout=timeout)
        except requests.exceptions.Timeout as exc:
            logging.warning(
                "Timeout downloading %s (attempt %s/%s): %s",
                url,
                attempt,
                max_retries,
                exc,
            )
            if attempt == max_retries:
                raise

def pull_from_portal_logic(sync_logger=None):
    """Core logic to pull documents from portal, perform OCR, and store embeddings."""
    logging.info("Starting pull_from_portal_logic")

    # Generate token and fetch list
    token = create_user_token()
    url = f"https://portal.combiphar.com/Documents/GetDocumentList?q={token}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # attempt JSON parsing regardless of content-type
        try:
            data = response.json()
        except Exception:
            data = json.loads(response.text)
    except Exception as e:
        error_msg = f"Failed to fetch document list: {e}"
        logging.error(error_msg)
        # Log global failure to sync logger
        if sync_logger:
            sync_logger.log_document_result(
                document_title="Portal API Request",
                status='failed',
                error_message=error_msg
            )
        return {"downloaded_files": []}

    # Determine file list
    file_list = []
    if isinstance(data, dict):
        file_list = data.get('data') or data.get('items') or []
    elif isinstance(data, list):
        file_list = data
    else:
        file_list = []

    if not isinstance(file_list, list):
        file_list = []
    logging.info(f"Found {len(file_list)} items in portal list")

    # Keep original data for response
    portal_data = data

    # Setup folders and get vector store
    download_folder = './data/documents/portal/'
    os.makedirs(download_folder, exist_ok=True)

    # Get vectorstore 
    vectorstore = get_vectorstore()
    if not vectorstore:
        logging.error("❌ Cannot connect to vector store. Aborting pull from portal.")
        return {"downloaded_files": []}

    # Initialize text splitter for chunking
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
    downloaded = []
    download_timeout = _get_portal_download_timeout()
    for item in file_list:
        logging.debug(f"Processing item: {item}")
        now = get_current_datetime()
        document_name = item.get('Title')
        orig_filename = item.get('FileName')
        document_id = item.get('Id') or item.get('ID')
        name, ext = os.path.splitext(orig_filename)
        normalized = name + (ext.lower() if ext else '')
        document_source = normalized
        is_published = item.get('IsPublished', False)

        # Skip if not published
        if not is_published:
            logging.info(f"Skipping unpublished document: {item.get('Title')}")
            # Log as skipped (not failed)
            if sync_logger:
                sync_logger.log_document_result(
                    document_title=document_name,
                    document_filename=orig_filename,
                    document_id=str(document_id) if document_id else None,
                    status='failed',
                    error_message='Document not published',
                    metadata={'is_published': is_published}
                )
            continue

        # Extract metadata
        logging.info(f"Processing document: {document_name} (source: {document_source})")

        # Normalize document_source
        if not document_source:
            document_source = f"{uuid.uuid4()}{ext.lower() if ext else ''}"
            logging.warning(f"Generated new document_source: {document_source} for {orig_filename}")
        
        document_source = document_source.strip().replace(' ', '_').replace('/', '_').replace('\\', '_')
        if not document_source.endswith(ext.lower() if ext else ''):
            document_source += (ext.lower() if ext else '')
        
        # Check if document exists and compare filenames for changes
        existing_doc_query = '''
            SELECT original_filename, stored_filename, id, storage_path 
            FROM documents 
            WHERE source_type = 'portal' AND metadata::json->>'FileName' = %s
        '''
        existing_results, _ = safe_db_query(existing_doc_query, (orig_filename,))
        
        should_skip = False
        needs_reprocessing = False
        existing_stored_filename = None
        existing_doc_id = None
        existing_storage_path = None
        
        if existing_results:
            db_original_filename = existing_results[0][0]
            existing_stored_filename = existing_results[0][1]
            existing_doc_id = existing_results[0][2]
            existing_storage_path = existing_results[0][3] if len(existing_results[0]) > 3 else None
            
            # Additional validation using validate_document_exist_db
            if existing_stored_filename and not validate_document_exist_db(existing_stored_filename):
                logging.warning(f"Database inconsistency detected for {existing_stored_filename}, will reprocess")
                needs_reprocessing = True
            else:
                candidate_paths = []
                if existing_storage_path:
                    if os.path.isabs(existing_storage_path):
                        candidate_paths.append(existing_storage_path)
                    else:
                        candidate_paths.append(os.path.join('.', existing_storage_path))
                if existing_stored_filename:
                    candidate_paths.append(os.path.join(download_folder, existing_stored_filename))

                file_exists = any(os.path.isfile(path) for path in candidate_paths)

                vectors_exist = False
                if existing_doc_id:
                    try:
                        vector_count_rows, _ = safe_db_query(
                            "SELECT COUNT(*) FROM documents_vectors WHERE document_id = %s",
                            (existing_doc_id,),
                        )
                        if isinstance(vector_count_rows, list) and vector_count_rows:
                            vectors_exist = (vector_count_rows[0][0] or 0) > 0
                    except Exception as vector_err:
                        logging.warning(
                            f"Failed to verify embeddings for document {existing_doc_id}: {vector_err}"
                        )

                if not file_exists:
                    logging.warning(
                        f"Stored file missing for {existing_stored_filename}, forcing reprocessing"
                    )
                    needs_reprocessing = True
                elif not vectors_exist:
                    logging.warning(
                        f"Embeddings missing for document {existing_doc_id}, forcing reprocessing"
                    )
                    needs_reprocessing = True
                elif db_original_filename == document_source:
                    # Filename hasn't changed and document exists, skip processing
                    logging.info(
                        f"Skipping {document_source} - filename unchanged (original_filename: {db_original_filename})"
                    )
                    should_skip = True
                else:
                    # Filename has changed, need to reprocess
                    logging.info(
                        f"Filename changed: '{db_original_filename}' -> '{document_source}', reprocessing..."
                    )
                    needs_reprocessing = True
        
        if should_skip:
            continue
        
        # If needs reprocessing, delete old vector data first
        if needs_reprocessing and existing_stored_filename:
            try:
                # Delete from vector store using the stored filename as document source
                vectorstore = get_vectorstore()
                if vectorstore:
                    # Delete documents with matching stored_filename from PGVector
                    vectorstore.delete_by_metadata({"stored_filename": existing_stored_filename})
                    logging.info(f"✅ Deleted old vector data for {existing_stored_filename}")
                
                # Delete old database record
                delete_query = "DELETE FROM documents WHERE id = %s"
                safe_db_query(delete_query, (existing_doc_id,))
                logging.info(f"✅ Deleted old database record for {existing_stored_filename}")
                
                # Delete old file if it exists
                old_file_path = os.path.join(download_folder, existing_stored_filename)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    logging.info(f"✅ Deleted old file {old_file_path}")
                elif existing_storage_path:
                    candidate_path = (
                        existing_storage_path
                        if os.path.isabs(existing_storage_path)
                        else os.path.join('.', existing_storage_path)
                    )
                    if os.path.exists(candidate_path):
                        os.remove(candidate_path)
                        logging.info(f"✅ Deleted old file {candidate_path}")
                    
            except Exception as e:
                logging.error(f"❌ Failed to delete old data for {existing_stored_filename}: {e}")
                # Continue with processing despite deletion error
        
        # Download file, fallback to static portal path
        file_url = (item.get('DownloadUrl') or item.get('downloadUrl') or item.get('FileUrl') or item.get('fileUrl'))
        if not file_url:
            base_dl = "https://portal.combiphar.com/DocAnnouncements"
            file_url = f"{base_dl}/{orig_filename}"
        logging.info(f"Downloading file from {file_url}")
        try:
            resp_file = _download_with_retry(file_url, download_timeout)
            resp_file.raise_for_status()
        except requests.exceptions.Timeout as e:
            error_msg = f"Failed to download after {PORTAL_DOWNLOAD_MAX_RETRIES} timeout retries: {e}"
            logging.warning(
                "Failed to download %s after %s timeout retries: %s",
                file_url,
                PORTAL_DOWNLOAD_MAX_RETRIES,
                e,
            )
            # Log download timeout failure
            if sync_logger:
                sync_logger.log_document_result(
                    document_title=document_name,
                    document_filename=orig_filename,
                    document_id=str(document_id) if document_id else None,
                    status='failed',
                    error_message=error_msg,
                    metadata={'file_url': file_url, 'error_type': 'timeout'}
                )
            continue
        except Exception as e:
            error_msg = f"Failed to download: {e}"
            logging.warning(f"Failed to download {file_url}: {e}")
            # Log download failure
            if sync_logger:
                sync_logger.log_document_result(
                    document_title=document_name,
                    document_filename=orig_filename,
                    document_id=str(document_id) if document_id else None,
                    status='failed',
                    error_message=error_msg,
                    metadata={'file_url': file_url, 'error_type': 'download_error'}
                )
            continue

        # Validate file content before saving and processing
        is_valid, validation_reason = validate_file_content(resp_file.content, document_source)
        if not is_valid:
            logging.warning(f"⚠️ Skipping invalid file {document_source}: {validation_reason}")
            # Log validation failure
            if sync_logger:
                sync_logger.log_document_result(
                    document_title=document_name,
                    document_filename=orig_filename,
                    document_id=str(document_id) if document_id else None,
                    status='failed',
                    error_message=f"Invalid file format: {validation_reason}",
                    metadata={'validation_reason': validation_reason}
                )
            continue

        file_path = os.path.join(download_folder, document_source)
        with open(file_path, 'wb') as f:
            f.write(resp_file.content)
        downloaded.append(document_source)
        logging.info(f"✅ File {document_source} validated and saved successfully")

        # Extract text using unified extraction function
        text = extract_text_from_document(file_path, document_source)

        if not text.strip():
            logging.warning(f"⚠️ No text extracted from {document_source}, skipping vector storage")
            file_size = 0
            try:
                file_size = os.path.getsize(file_path)
            except Exception as size_err:
                logging.warning(f"Failed to get file size for {file_path}: {size_err}")
            if sync_logger:
                sync_logger.log_document_result(
                    document_title=document_name,
                    document_filename=orig_filename,
                    document_id=str(document_id) if document_id else None,
                    status='failed',
                    error_message='No text extracted from document',
                    file_size=file_size,
                    metadata={'error_type': 'no_text_extracted'}
                )
            continue
        # Save metadata to database using new structure
        import uuid as uuid_lib
        import mimetypes
        
        # Generate UUID-based stored filename
        file_ext = os.path.splitext(document_source)[1].lower()
        stored_filename = f"{uuid_lib.uuid4()}{file_ext}"
        
        # Ensure generated stored_filename doesn't already exist (extremely unlikely but good practice)
        while validate_document_exist_db(stored_filename):
            logging.warning(f"UUID collision detected for {stored_filename}, generating new UUID")
            stored_filename = f"{uuid_lib.uuid4()}{file_ext}"
        
        try:
            file_size = os.path.getsize(file_path)
        except Exception as size_err:
            logging.warning(f"Failed to get file size for {file_path}: {size_err}")
            file_size = 0
        mime_type, _ = mimetypes.guess_type(document_source)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Prepare storage path (will be updated after file rename)
        storage_path = os.path.relpath(file_path, '.')
        
        # Prepare metadata
        item_metadata = json.dumps(item)
        
        # Rename the actual file to use stored_filename
        new_file_path = os.path.join(download_folder, stored_filename)
        if file_path != new_file_path:
            os.rename(file_path, new_file_path)
            logging.info(f"Renamed {document_source} to {stored_filename}")
            # Update storage path to reflect new filename
            storage_path = os.path.relpath(new_file_path, '.')
        
        insert_query = '''
            INSERT INTO documents
            (source_type, original_filename, stored_filename, mime_type, size_bytes, metadata, storage_path, uploaded_by) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        '''
        result, _ = safe_db_query(insert_query, (
            'portal',  # source_type
            document_source,  # original_filename 
            stored_filename,  # stored_filename
            mime_type,  # mime_type
            file_size,  # size_bytes
            item_metadata,  # metadata
            storage_path,  # storage_path
            None  # uploaded_by (system upload)
        ))
        
        # Get the document ID from the database insert
        # Handle both cases: result as list (SELECT-like) or as int (INSERT rowcount)
        if isinstance(result, list) and len(result) > 0:
            document_db_id = result[0][0]
        elif isinstance(result, int) and result > 0:
            # For INSERT with RETURNING that's treated as INSERT, need to get the ID differently
            # Let's use a SELECT query to get the last inserted ID
            select_query = "SELECT id FROM documents WHERE stored_filename = %s ORDER BY id DESC LIMIT 1"
            id_result, _ = safe_db_query(select_query, (stored_filename,))
            if id_result and len(id_result) > 0:
                document_db_id = id_result[0][0]
            else:
                logging.error(f"Failed to get document ID after insert for {stored_filename}")
                continue
        else:
            logging.error(f"Failed to get document ID after insert for {stored_filename}")
            continue
        
        # Chunk text and add to vector store using LangChain vectorstore with improved metadata
        chunks = text_splitter.split_text(text)
        
        if chunks:
            # Prepare documents for LangChain vectorstore
            docs = []
            
            display_name = document_name or document_source or ""
            prefix = f"{display_name}\n\n" if display_name else ""
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    metadata = {
                        "document_id": str(document_db_id),
                        "chat_id": None,
                        "source_type": "portal",
                        "uploaded_by": None,
                        "original_filename": document_source,
                        "stored_filename": stored_filename,
                        "storage_path": storage_path,
                        "mime_type": mime_type,
                        "chunk_index": i,
                        "chunk_total": len([c for c in chunks if c.strip()]),
                        "created_at": now.isoformat() if now else None
                    }
                    content = f"{prefix}{chunk}" if prefix else chunk
                    doc = Document(page_content=content, metadata=metadata)
                    docs.append(doc)
            
            # Add to vector store using LangChain (handles embeddings automatically)
            if docs:
                try:
                    vectorstore.add_documents(docs)
                    logging.info(f"✅ Added {len(docs)} chunks to vector store for {stored_filename}")
                    
                    # Log successful processing
                    if sync_logger:
                        sync_logger.log_document_result(
                            document_title=document_name,
                            document_filename=orig_filename,
                            document_id=str(document_id) if document_id else None,
                            status='success',
                            file_size=file_size,
                            metadata={
                                'stored_filename': stored_filename,
                                'chunks_count': len(docs),
                                'text_length': len(text)
                            }
                        )
                        
                except Exception as e:
                    error_msg = f"Failed to add chunks to vector store: {e}"
                    logging.error(f"❌ Failed to add chunks to vector store: {e}")
                    
                    # Log vector store failure
                    if sync_logger:
                        sync_logger.log_document_result(
                            document_title=document_name,
                            document_filename=orig_filename,
                            document_id=str(document_id) if document_id else None,
                            status='failed',
                            error_message=error_msg,
                            file_size=file_size,
                            metadata={'error_type': 'vector_store_error'}
                        )
                    
                    # Rollback: delete file and database record due to embedding failure
                    try:
                        os.remove(new_file_path)
                        logging.info(f"✅ Deleted file {new_file_path} due to embedding failure")
                    except Exception as del_e:
                        logging.error(f"❌ Failed to delete file {new_file_path}: {del_e}")
                    
                    try:
                        delete_query = "DELETE FROM documents WHERE id = %s"
                        safe_db_query(delete_query, (document_db_id,))
                        logging.info(f"✅ Deleted database record for {stored_filename} due to embedding failure")
                    except Exception as del_e:
                        logging.error(f"❌ Failed to delete database record for {stored_filename}: {del_e}")
                    # Continue to next document
                    continue
        else:
            # No text extracted but file was saved - log as partial success
            if sync_logger:
                sync_logger.log_document_result(
                    document_title=document_name,
                    document_filename=orig_filename,
                    document_id=str(document_id) if document_id else None,
                    status='failed',
                    error_message='No text extracted from document',
                    file_size=file_size,
                    metadata={'error_type': 'no_text_extracted'}
                )
            continue
        
        # Update document_source for downloaded list to use stored_filename
        document_source = stored_filename
    # Return response with consistent structure
    return {
        "message": "Success pull from portal",
        "downloaded_files": downloaded,
        "data": {"portal_data": portal_data, "downloaded_files": downloaded}
    }
