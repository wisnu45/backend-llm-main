"""
Local document embedding utilities for processing documents from local filesystem.
"""
import os
import logging
import uuid
import json
import mimetypes
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .database import safe_db_query
from .pgvectorstore import get_vectorstore
from .document import validate_file_content, extract_text_from_document, validate_document_exist_db
from .time_provider import get_current_datetime

# Configure logger
logger = logging.getLogger(__name__)

def embed_local_documents_logic(
    documents_path: str = "data/documents/admin", 
    source_type: str = "admin",
    skip_existing: bool = True,
    allowed_extensions: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Core logic to process and embed local documents from filesystem.
    
    Args:
        documents_path: Path to the documents folder (relative to project root)
        source_type: Type identifier for the documents (e.g., 'local', 'admin', 'user')
        skip_existing: Whether to skip files that are already processed
        allowed_extensions: List of allowed file extensions (default: common document formats)
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting local document embedding from: {documents_path}")
    
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.txt', '.doc', '.docx', '.png', '.jpg', '.jpeg']
    
    # Get vectorstore
    vectorstore = get_vectorstore()
    if not vectorstore:
        logger.error("❌ Failed to get vectorstore")
        return {"processed_files": [], "errors": ["Failed to initialize vectorstore"]}
    
    # Initialize text splitter with optimized settings for document processing
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    processed_files = []
    errors = []
    skipped_files = []
    
    # Get absolute path to documents directory
    project_root = Path(__file__).parent.parent.parent
    full_documents_path = project_root / documents_path
    
    if not full_documents_path.exists():
        error_msg = f"Documents path does not exist: {full_documents_path}"
        logger.error(error_msg)
        return {"processed_files": [], "errors": [error_msg]}
    
    logger.info(f"Scanning directory: {full_documents_path}")
    
    # Walk through all files in the documents directory
    for root, dirs, files in os.walk(full_documents_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for filename in files:
            # Skip hidden files and system files
            if filename.startswith('.') or filename.startswith('~'):
                continue
                
            file_path = Path(root) / filename
            file_extension = file_path.suffix.lower()
            
            # Check if file extension is allowed
            if file_extension not in allowed_extensions:
                logger.debug(f"⏭️ Skipping {filename} - extension {file_extension} not allowed")
                continue
            
            try:
                relative_path = file_path.relative_to(full_documents_path)
                logger.info(f"📄 Processing file: {relative_path}")
                
                # Check if file already exists in database
                if skip_existing and _check_file_exists_in_db(str(relative_path), source_type):
                    logger.info(f"⏭️ Skipping {relative_path} - already exists in database")
                    skipped_files.append(str(relative_path))
                    continue
                
                # Process the file
                result = _process_single_file(
                    file_path=file_path,
                    relative_path=str(relative_path),
                    source_type=source_type,
                    text_splitter=text_splitter,
                    vectorstore=vectorstore
                )
                
                if result["success"]:
                    processed_files.append(str(relative_path))
                    logger.info(f"✅ Successfully processed: {relative_path}")
                else:
                    errors.append(f"{relative_path}: {result['error']}")
                    logger.error(f"❌ Failed to process {relative_path}: {result['error']}")
                    
            except Exception as e:
                error_msg = f"Error processing {filename}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
    
    # Summary
    total_processed = len(processed_files)
    total_skipped = len(skipped_files)
    total_errors = len(errors)
    
    logger.info(f"📊 Processing summary:")
    logger.info(f"   ✅ Processed: {total_processed} files")
    logger.info(f"   ⏭️ Skipped: {total_skipped} files")
    logger.info(f"   ❌ Errors: {total_errors} files")
    
    return {
        "processed_files": processed_files,
        "skipped_files": skipped_files,
        "errors": errors,
        "summary": {
            "total_processed": total_processed,
            "total_skipped": total_skipped,
            "total_errors": total_errors
        }
    }

def _check_file_exists_in_db(relative_path: str, source_type: str) -> bool:
    """
    Check if a file already exists in the database.
    
    Args:
        relative_path: Relative path of the file
        source_type: Source type of the document
        
    Returns:
        True if file exists, False otherwise
    """
    try:
        query = """
            SELECT id FROM documents 
            WHERE storage_path = %s AND source_type = %s
        """
        result, _ = safe_db_query(query, (relative_path, source_type))
        return bool(result and len(result) > 0)
    except Exception as e:
        logger.warning(f"Error checking file existence in DB: {e}")
        return False

def _process_single_file(
    file_path: Path,
    relative_path: str,
    source_type: str,
    text_splitter: RecursiveCharacterTextSplitter,
    vectorstore
) -> Dict[str, Any]:
    """
    Process a single file: validate, extract text, chunk, and embed.
    
    Args:
        file_path: Full path to the file
        relative_path: Relative path for storage
        source_type: Type of document source
        text_splitter: Text splitter instance
        vectorstore: Vector store instance
        
    Returns:
        Dictionary with success status and error message if any
    """
    try:
        # Read file content for validation
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Validate file content
        is_valid, reason = validate_file_content(file_content, file_path.name)
        if not is_valid:
            return {"success": False, "error": f"Invalid file content: {reason}"}
        
        # Extract text from document
        text = extract_text_from_document(str(file_path), source_type)
        if not text or len(text.strip()) < 10:
            return {"success": False, "error": "No text content extracted or content too short"}
        
        # Generate UUID-based stored filename (like portal_pull.py)
        file_ext = file_path.suffix.lower()
        stored_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Ensure generated stored_filename doesn't already exist (extremely unlikely but good practice)
        while validate_document_exist_db(stored_filename):
            logger.warning(f"UUID collision detected for {stored_filename}, generating new UUID")
            stored_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Get file info
        file_size = file_path.stat().st_size
        mime_type = _get_mime_type(file_ext, file_path.name)
        created_time = get_current_datetime()
        
        # Prepare storage path for the UUID-based filename
        storage_dir = file_path.parent
        new_file_path = storage_dir / stored_filename
        
        # Copy file with UUID-based name if it's different from original
        if str(file_path) != str(new_file_path):
            import shutil
            shutil.copy2(file_path, new_file_path)
            logger.info(f"Copied {file_path.name} to {stored_filename}")
            # Update storage path to reflect new filename
            storage_path = str(new_file_path.relative_to(Path.cwd()))
        else:
            storage_path = relative_path
        
        # Insert document record
        document_id = _insert_document_record(
            original_filename=file_path.name,
            stored_filename=stored_filename,
            storage_path=storage_path,
            source_type=source_type,
            mime_type=mime_type,
            file_size=file_size,
            created_time=created_time
        )
        
        if not document_id:
            return {"success": False, "error": "Failed to insert document record"}
        
        # Chunk text and add to vector store
        chunks = text_splitter.split_text(text)
        
        if not chunks:
            return {"success": False, "error": "No text chunks generated"}
        
        docs = []
        display_name = file_path.name
        prefix = f"{display_name}\n\n" if display_name else ""
        for i, chunk in enumerate(chunks):
            if chunk.strip():
                metadata = {
                    "document_id": str(document_id),
                    "chat_id": None,
                    "source_type": source_type,
                    "uploaded_by": None,
                    "original_filename": file_path.name,
                    "stored_filename": stored_filename,
                    "storage_path": storage_path,
                    "mime_type": mime_type,
                    "chunk_index": i,
                    "chunk_total": len([c for c in chunks if c.strip()]),
                    "created_at": created_time.isoformat()
                }
                content = f"{prefix}{chunk}" if prefix else chunk
                doc = Document(page_content=content, metadata=metadata)
                docs.append(doc)
        
        # Add to vector store (handles embeddings automatically)
        if docs:
            try:
                vectorstore.add_documents(docs)
                logger.debug(f"Added {len(docs)} chunks to vector store for {stored_filename}")
            except Exception as e:
                logger.error(f"❌ Failed to add chunks to vector store: {e}")
                # Continue processing despite vector store error
        
        return {"success": True, "chunks": len(docs)}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def _insert_document_record(
    original_filename: str,
    stored_filename: str,
    storage_path: str,
    source_type: str,
    mime_type: str,
    file_size: int,
    created_time: datetime
) -> Optional[str]:
    """
    Insert a document record into the database.
    
    Returns:
        Document ID if successful, None otherwise
    """
    try:
        insert_query = """
            INSERT INTO documents (
                source_type, original_filename, stored_filename, storage_path,
                mime_type, size_bytes, uploaded_by, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        params = (
            source_type,
            original_filename,
            stored_filename,
            storage_path,
            mime_type,
            file_size,
            None,  # uploaded_by (system)
            created_time
        )
        
        result, _ = safe_db_query(insert_query, params)
        
        # Get the document ID from the database insert
        if isinstance(result, list) and len(result) > 0:
            document_db_id = result[0][0]
            return str(document_db_id)
        elif isinstance(result, int) and result > 0:
            # Fallback: get the last inserted ID
            select_query = "SELECT id FROM documents WHERE stored_filename = %s ORDER BY created_at DESC LIMIT 1"
            id_result, _ = safe_db_query(select_query, (stored_filename,))
            if id_result and len(id_result) > 0:
                return str(id_result[0][0])
        
        logger.error(f"Failed to get document ID after insert for {stored_filename}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to insert document record: {e}")
        return None

def _get_mime_type(file_extension: str, filename: str = None) -> str:
    """
    Get MIME type based on file extension, using mimetypes library.
    
    Args:
        file_extension: File extension (with dot)
        filename: Optional full filename for better detection
        
    Returns:
        MIME type string
    """
    # First try using mimetypes library
    if filename:
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
    
    # Fallback to manual mapping for common types
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff'
    }
    
    return mime_types.get(file_extension.lower(), 'application/octet-stream')

def embed_specific_files(
    file_paths: List[str], 
    source_type: str = "admin",
    base_path: str = "data/documents/admin"
) -> Dict[str, Any]:
    """
    Embed specific files by their paths.
    
    Args:
        file_paths: List of relative file paths from base_path
        source_type: Type identifier for the documents
        base_path: Base path for the documents
        
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Processing specific files: {file_paths}")
    
    # Get vectorstore
    vectorstore = get_vectorstore()
    if not vectorstore:
        logger.error("❌ Failed to get vectorstore")
        return {"processed_files": [], "errors": ["Failed to initialize vectorstore"]}
    
    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    processed_files = []
    errors = []
    
    # Get absolute base path
    project_root = Path(__file__).parent.parent.parent
    full_base_path = project_root / base_path
    
    for file_path in file_paths:
        try:
            full_file_path = full_base_path / file_path
            
            if not full_file_path.exists():
                error_msg = f"File does not exist: {file_path}"
                errors.append(error_msg)
                logger.error(error_msg)
                continue
            
            # Process the file
            result = _process_single_file(
                file_path=full_file_path,
                relative_path=file_path,
                source_type=source_type,
                text_splitter=text_splitter,
                vectorstore=vectorstore
            )
            
            if result["success"]:
                processed_files.append(file_path)
                logger.info(f"✅ Successfully processed: {file_path}")
            else:
                errors.append(f"{file_path}: {result['error']}")
                logger.error(f"❌ Failed to process {file_path}: {result['error']}")
                
        except Exception as e:
            error_msg = f"Error processing {file_path}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    return {
        "processed_files": processed_files,
        "errors": errors,
        "summary": {
            "total_processed": len(processed_files),
            "total_errors": len(errors)
        }
    }
