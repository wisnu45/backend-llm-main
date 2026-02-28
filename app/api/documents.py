from flask import Blueprint, request, jsonify, send_file, g
from flasgger import swag_from

from app.utils.auth import require_auth, require_auth_with_exclude, require_access
from app.utils.general import chatbot, yaml_path
from app.utils.database import safe_db_query
from app.utils.pgvectorstore import get_vectorstore
from app.utils.document import process_document_for_vector_storage, verify_document_exists, data_path
from app.utils.permission import get_setting
from app.utils.time_provider import get_current_datetime, get_datetime_from_timestamp
from app.services.document_sync_manager import DocumentSyncManager

from datetime import datetime
import os
import json
import logging
import mimetypes

documents_bp = Blueprint('documents', __name__)


def _get_request_user(kwargs):
    user = kwargs.get('user')
    if user:
        return user
    return getattr(g, 'current_user', {}) or {}


def _is_allowed_to_sync_documents(user: dict) -> bool:
    """Check whether the given user can access document sync endpoints."""
    username = (user or {}).get('username')
    allowed_users_setting = get_setting("document_sync_allowed_users", [])
    allowed_usernames = []

    if isinstance(allowed_users_setting, list):
        allowed_usernames = [
            str(item).strip().lower()
            for item in allowed_users_setting
            if str(item).strip()
        ]
    elif isinstance(allowed_users_setting, str):
        allowed_usernames = (
            [allowed_users_setting.strip().lower()]
            if allowed_users_setting.strip()
            else []
        )

    if not allowed_usernames:
        return True  # no restriction configured

    return bool(username and username.lower() in allowed_usernames)


def _is_date_only(value: str) -> bool:
    return len(value) == 10 and value[4] == '-' and value[7] == '-'


def _parse_sync_log_date(value: str, *, end_of_day: bool = False):
    if value is None:
        return None

    raw = str(value).strip()
    if not raw:
        return None

    normalized = raw[:-1] + '+00:00' if raw.endswith('Z') else raw

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if _is_date_only(raw):
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)

    return parsed


def _parse_sync_log_filters():
    sync_type = request.args.get('sync_type', '').strip() or None
    status = request.args.get('status', '').strip() or None
    search = request.args.get('search', '').strip() or None

    start_date_raw = (
        request.args.get('start_date')
        or request.args.get('date_start')
        or request.args.get('from')
    )
    end_date_raw = (
        request.args.get('end_date')
        or request.args.get('date_end')
        or request.args.get('to')
    )

    start_date = _parse_sync_log_date(start_date_raw) if start_date_raw else None
    end_date = _parse_sync_log_date(end_date_raw, end_of_day=True) if end_date_raw else None

    if start_date_raw and not start_date:
        return None, "Format start_date tidak valid. Gunakan ISO 8601."

    if end_date_raw and not end_date:
        return None, "Format end_date tidak valid. Gunakan ISO 8601."

    if start_date and end_date and end_date < start_date:
        return None, "end_date harus lebih besar atau sama dengan start_date."

    return {
        "sync_type": sync_type,
        "status": status,
        "search": search,
        "start_date": start_date,
        "end_date": end_date,
    }, None


def _normalize_sync_status(status):
    if not status:
        return status

    normalized = str(status).strip().lower()
    if normalized == "succeeded":
        return "success"
    return normalized


def _build_failed_documents(document_details, global_error_message=None):
    failed_documents = []
    for detail in document_details or []:
        detail_status = _normalize_sync_status(detail.get("status"))
        if detail_status != "failed":
            continue

        item_type = detail.get("item_type") or "document"

        file_identifier = (
            detail.get("document_filename")
            or detail.get("document_id")
            or detail.get("item_url")
            or "N/A"
        )

        failed_documents.append({
            "item_type": item_type,
            "item_url": detail.get("item_url"),
            "item_source": detail.get("item_source"),
            "document_title": detail.get("document_title"),
            "document_filename": detail.get("document_filename"),
            "document_id": detail.get("document_id"),
            "file_identifier": file_identifier,
            "error_message": detail.get("error_message"),
        })

    if not failed_documents and global_error_message:
        failed_documents.append({
            "document_title": "Sinkronisasi gagal",
            "document_filename": None,
            "document_id": None,
            "file_identifier": "N/A",
            "error_message": "Lihat global error di atas",
            "is_global_error": True,
        })

    return failed_documents


@documents_bp.before_request
@require_auth_with_exclude(exclude=['documents.documents_download_file'])
def check_access(**kwargs):
    # daftar exclude endpoint
    exclude = ['documents.documents_download_file']

    if request.endpoint in exclude:
        return 

    # ambil user dari kwargs
    user = _get_request_user(kwargs)
    if user:
        try:
            g.current_user = user
        except Exception:
            pass

    # cek akses menu_user
    access = require_access(user, 'menu_document')
    if not access or not access.get("value") : 
        return jsonify({"message": "Access tidak diizinkan"}), 403

def delete_from_vectordb(document_source=None, portal_id=None):
    """Helper function to delete documents from vector database"""
    try:
        vectorstore = get_vectorstore()
        if not vectorstore:
            logging.warning("❌ Vectorstore not available for deletion")
            return

        deleted_any = False

        if document_source:
            if vectorstore.delete_by_metadata({"stored_filename": document_source}):
                logging.info(f"Deleted vector entries for stored_filename={document_source}")
                deleted_any = True
                try:
                    chatbot().invalidate_document_cache(document_source)
                except Exception:
                    logging.debug("Failed to invalidate chatbot cache after vector deletion", exc_info=True)

        if portal_id:
            if vectorstore.delete_by_metadata({"portal_id": portal_id}):
                logging.info(f"Deleted vector entries for portal_id={portal_id}")
                deleted_any = True

        if not deleted_any:
            logging.info("No matching vector entries found for deletion")

    except Exception as e:
        logging.warning(f"Failed to delete from vectordb: {e}")

def delete_all_from_vectordb():
    """Helper function to delete all documents from vector database"""
    try:
        vectorstore = get_vectorstore()
        if not vectorstore:
            logging.warning("❌ Vectorstore not available for deletion")
            return

        if vectorstore.delete_collection():
            logging.info("Deleted all documents from vector store")
        else:
            logging.info("Vector store delete_collection returned False (possibly already empty)")

    except Exception as e:
        logging.warning(f"Failed to delete all from vectordb: {e}")

@documents_bp.route('/documents', methods=['POST'])
@swag_from(yaml_path("documents_post.yml"))
def create_document(**kwargs):
    """Create a new document with optional file upload and metadata."""
    user = _get_request_user(kwargs)
    data = request.form
    file = request.files.get('file')
    metadata = data.get('metadata')
    source_type = data.get('source_type', 'admin')  # default to admin upload
    chat_id = data.get('chat_id')  # for user-specific chat attachments
        
    allow_attach = get_setting("attachment", False)
    if not allow_attach : 
        return jsonify({'error': 'Anda tidak memiliki izin untuk mengunggah file'}), 403
    
    # metadata dari form biasanya string, coba parse json jika ada
    if metadata and isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    if not file:
        return jsonify({'error': 'File is required'}), 400
        
    if file.filename == '':
        return jsonify({"message": "Tidak ada file yang dipilih"}), 400
    if not file.filename:
        return jsonify({'error': 'Invalid file name'}), 400

    # Validate source_type
    if source_type not in ['portal', 'admin', 'user', 'website']:
        source_type = 'admin'
    
    # If source_type is user and chat_id is provided, validate chat_id
    if source_type == 'user' and chat_id:
        try:
            import uuid
            uuid.UUID(chat_id)  # Validate chat_id is a valid UUID
        except ValueError:
            return jsonify({'error': 'Invalid chat_id format. Must be a valid UUID'}), 400

    import uuid
    original_filename = str(file.filename)
    file_ext = os.path.splitext(original_filename)[1].lower()
    stored_filename = f"{uuid.uuid4()}{file_ext}"
    
    # Determine storage path based on source_type
    if source_type == 'admin':
        storage_folder = data_path('documents', 'admin')
    elif source_type == 'user':
        if chat_id:
            # User-specific folder with chat_id subfolder
            storage_folder = data_path('documents', 'user', chat_id)
        else:
            # General user folder
            storage_folder = data_path('documents', 'user')
    elif source_type == 'website':
        storage_folder = data_path('documents', 'website')
    else:  # portal
        storage_folder = data_path('documents', 'portal')
    
    os.makedirs(storage_folder, exist_ok=True)
    file_path = os.path.join(storage_folder, stored_filename)
    storage_path = os.path.relpath(file_path, '.')
    
    # Save file
    file.save(file_path)
    
    # Get file info
    file_size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(original_filename)
    if not mime_type:
        mime_type = 'application/octet-stream'

    allow_attach_size = get_setting("attachment_file_size", 0)
    if((file_size/1024000) > allow_attach_size) :
        os.remove(file_path)
        return jsonify({"message": "Ukuran file melebihi batas {max_size} MB.".format(max_size=allow_attach_size)}), 400
    
    allow_attach_type = get_setting("attachment_file_types", [])
    if(file_ext[1:] not in allow_attach_type) :
        os.remove(file_path)
        return jsonify({"message": "Tipe file tidak didukung. Gunakan: {supported_types}.".format(supported_types=", ".join(allow_attach_type))}), 400

    if(file_ext[1:] in ['xls', 'xlsx', 'xlsm']) :
        from app.services.agent.file_excel_service import FileExcelService
        excel_service = FileExcelService()
        if excel_service.enabled :
            summary = excel_service.generate_summary(
                file_path=file_path,
                filename=original_filename,
                nrows=5,
                question=None
            )
            if summary:
                if not metadata:
                    metadata = {}
                metadata['Summary'] = summary

    metadata_json = json.dumps(metadata) if metadata else '{}'
    insert_query = '''
        INSERT INTO documents 
        (source_type, original_filename, stored_filename, mime_type, size_bytes, metadata, storage_path, uploaded_by) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    '''

    try:
        safe_db_query(insert_query, (
            source_type,
            original_filename,
            stored_filename,
            mime_type,
            file_size,
            metadata_json,
            storage_path,
            user.get('id')
        ))
    except Exception as db_err:
        logging.error(f"❌ Failed to insert document record: {db_err}")
        try:
            os.remove(file_path)
        except OSError:
            pass
        return jsonify({'error': 'Gagal menyimpan dokumen'}), 500

    document_id = None
    try:
        rows, columns = safe_db_query(
            "SELECT id FROM documents WHERE stored_filename = %s LIMIT 1",
            (stored_filename,)
        )
        if isinstance(rows, list) and rows:
            document_id = str(rows[0][0])
    except Exception as fetch_err:
        logging.warning(f"⚠️ Failed to resolve document ID for {stored_filename}: {fetch_err}")

    supported_extensions = ['.pdf','.txt', '.md', '.log', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']

    if file_ext in supported_extensions and document_id:
        try:
            vector_metadata = {
                'file_type': file_ext[1:],
                'upload_method': 'manual_upload',
                'file_size': file_size,
                'source_type': source_type,
                'original_filename': original_filename,
                'mime_type': mime_type,
                'storage_path': storage_path,
                'uploaded_by': user.get('id'),
                'chat_id': chat_id
            }
            if metadata:
                vector_metadata.update(metadata)

            success = process_document_for_vector_storage(
                file_path=file_path,
                document_name=original_filename,
                document_source=stored_filename,
                metadata=vector_metadata,
                document_id=document_id,
                storage_path=storage_path
            )

            if success:
                logging.info(f"✅ Document {original_filename} added to vector storage")
                try:
                    chatbot().invalidate_document_cache(stored_filename)
                except Exception:
                    logging.debug("Failed to invalidate chatbot cache after document insert", exc_info=True)
            else:
                logging.warning(f"⚠️ Failed to add {original_filename} to vector storage")
        except Exception as e:
            logging.warning(f"Vector storage processing failed for {original_filename}: {e}")
    elif file_ext not in supported_extensions:
        logging.info(f"📄 File type {file_ext} not supported for vector storage, saved file only")
        logging.info(f"Supported types: {', '.join(supported_extensions)}")
    else:
        logging.warning(f"⚠️ Document ID not resolved for {stored_filename}, skipping vector embedding")

    return jsonify({"message": "Berhasil menambahkan data documents", "document_id": document_id}), 201

@documents_bp.route('/documents', methods=['GET'])
@swag_from(yaml_path("documents_get.yml"))
def get_documents(**kwargs):
    """Get all documents with pagination and filtering options."""
    # Pagination params
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        if page < 1: page = 1
        if page_size < 1: page_size = 10
    except Exception:
        page, page_size = 1, 10

    # Search param
    search = request.args.get('search', '').strip()

    # source_type param (replaces doc_type)
    source_type = request.args.get('source_type', 'all').lower()
    if source_type not in ['all', 'portal', 'admin', 'user', 'website']:
        source_type = 'all'

    # Build query with new structure
    base_query = '''
        SELECT d.id, d.source_type, d.original_filename, d.stored_filename, d.mime_type, 
               d.size_bytes, d.metadata, d.storage_path, d.created_at, d.updated_at,
               u.name as uploaded_by_name
        FROM documents d
        LEFT JOIN users u ON d.uploaded_by = u.id
    '''
    count_query = 'SELECT COUNT(*) FROM documents d'
    params = []
    count_params = []
    where_conditions = []

    if search:
        where_conditions.append('(d.metadata::json->>\'Title\' ILIKE %s OR d.original_filename ILIKE %s)')
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')
    
    if source_type != 'all':
        where_conditions.append('d.source_type = %s')
        params.append(source_type)
        count_params.append(source_type)
    else :
        where_conditions.append('d.source_type <> %s')
        params.append("user")
        count_params.append("user")

    if where_conditions:
        where_clause = ' WHERE ' + ' AND '.join(where_conditions)
        base_query += where_clause
        count_query += where_clause

    base_query += ' ORDER BY d.created_at DESC LIMIT %s OFFSET %s'
    params.extend([page_size, (page-1)*page_size])

    # Get total count
    total_rows, _ = safe_db_query(count_query, count_params)
    if not isinstance(total_rows, list) or not total_rows:
        total = 0
    else:
        total = total_rows[0][0]

    # Get paginated data
    rows, _ = safe_db_query(base_query, params)
    if not isinstance(rows, list):
        rows = []

    docs = []
    for row in rows:
        if isinstance(row, (list, tuple)) and len(row) >= 10:
            # Build download URL using stored_filename
            base_url = request.host_url.rstrip('/').replace('http://', 'https://')
            doc_id = row[0]
            document_url = None
            if doc_id:
                document_url = f"{base_url}/storage/{doc_id}"

            title = row[6].get('Title') if row[6] else None
            
            docs.append({
                'id': row[0],
                'source_type': row[1],
                'original_filename': row[2],
                'stored_filename': row[3],
                'mime_type': row[4],
                'size_bytes': row[5],
                'metadata': row[6],
                'storage_path': row[7],
                'created_at': row[8].isoformat() if row[8] else None,
                'updated_at': row[9].isoformat() if row[9] else None,
                'uploaded_by_name': row[10],
                'title': title,
                'url': document_url
            })
            
    return {
        "message": "Berhasil mengambil data documents",
        "data": docs,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total // page_size) + (1 if total % page_size else 0)
        }
    }, 200

@documents_bp.route('/documents/<doc_id>', methods=['GET'])
@swag_from(yaml_path("documents_id_get.yml"))
def get_document(doc_id, **kwargs):
    """Get a specific document by ID."""
    # Query with new structure
    query = '''
        SELECT d.id, d.source_type, d.original_filename, d.stored_filename, d.mime_type, 
               d.size_bytes, d.metadata, d.storage_path, d.created_at, d.updated_at,
               u.name as uploaded_by_name
        FROM documents d
        LEFT JOIN users u ON d.uploaded_by = u.id
        WHERE d.id = %s
    '''
    rows, _ = safe_db_query(query, (doc_id,))
    if not isinstance(rows, list) or not rows:
        return jsonify({'error': 'Dokumen tidak ditemukan'}), 404
    row = rows[0]
    if not isinstance(row, (list, tuple)) or len(row) < 10:
        return jsonify({'error': 'Dokumen tidak ditemukan'}), 404
    
    # Build download URL using stored_filename
    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
    doc_id = row[0]
    document_url = None
    if doc_id:
        document_url = f"{base_url}/storage/{doc_id}"

    title = row[6].get('Title') if row[6] else None
            
    doc = {
        'id': row[0],
        'source_type': row[1],
        'original_filename': row[2],
        'stored_filename': row[3],
        'mime_type': row[4],
        'size_bytes': row[5],
        'metadata': row[6],  # Already JSONB, no need to dumps
        'storage_path': row[7],
        'created_at': row[8].isoformat() if row[8] else None,
        'updated_at': row[9].isoformat() if row[9] else None,
        'uploaded_by_name': row[10],
        'title': title,
        'url': document_url
    }
    return {"message": "Berhasil mengambil data documents", "data": doc}, 200

@documents_bp.route('/documents/<doc_id>', methods=['PATCH'])
@swag_from(yaml_path("documents_id_patch.yml"))
def update_document(doc_id, **kwargs):
    """Update an existing document by ID."""
    if request.is_json:
        data = request.get_json()
        original_filename = data.get('original_filename')
        metadata = data.get('metadata')
        file = None
    else:
        data = request.form
        original_filename = data.get('original_filename') or (request.files['file'].filename if 'file' in request.files else None)
        metadata = data.get('metadata')
        file = request.files.get('file')
        if metadata is not None and isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

    # Check if document exists and get current info
    check_query = 'SELECT source_type, stored_filename, storage_path FROM documents WHERE id=%s'
    rows, _ = safe_db_query(check_query, (doc_id,))
    if not isinstance(rows, list) or not rows:
        return jsonify({'error': 'Dokumen tidak ditemukan'}), 404
    
    current_source_type = rows[0][0]
    current_stored_filename = rows[0][1]
    current_storage_path = rows[0][2]
    
    # Only allow updating non-portal documents for now (can be adjusted based on business rules)
    if current_source_type == 'portal':
        return jsonify({'error': 'Dokumen portal tidak dapat diubah'}), 403

    update_fields = []
    update_values = []
    
    if original_filename:
        update_fields.append('original_filename=%s')
        update_values.append(original_filename)
    
    if metadata:
        update_fields.append('metadata=%s')
        update_values.append(json.dumps(metadata))
    
    if file:
        if file.filename == '':
            return jsonify({"message": "Tidak ada file yang dipilih"}), 400
        if not file.filename:
            return jsonify({'error': 'Invalid file name'}), 400
            
        import uuid
        new_original_filename = str(file.filename)
        file_ext = os.path.splitext(new_original_filename)[1].lower()
        new_stored_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Determine storage folder based on current source_type
        if current_source_type == 'admin':
            storage_folder = data_path('documents', 'admin')
        elif current_source_type == 'user':
            storage_folder = data_path('documents', 'user')
        elif current_source_type == 'website':
            storage_folder = data_path('documents', 'website')
        else:  # portal
            storage_folder = data_path('documents', 'portal')
        
        os.makedirs(storage_folder, exist_ok=True)
        file_path = os.path.join(storage_folder, new_stored_filename)
        new_storage_path = os.path.relpath(file_path, '.')
        
        # Save new file
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(new_original_filename)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Update database fields for new file
        update_fields.extend([
            'original_filename=%s', 
            'stored_filename=%s', 
            'mime_type=%s',
            'size_bytes=%s', 
            'storage_path=%s',
            'updated_at=CURRENT_TIMESTAMP'
        ])
        update_values.extend([
            new_original_filename, 
            new_stored_filename, 
            mime_type,
            file_size, 
            new_storage_path
        ])

        # Process updated document for vector storage
        supported_extensions = ['.pdf', '.txt', '.md', '.log', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']

        if file_ext in supported_extensions:
            try:
                # Remove old document from vector storage
                delete_from_vectordb(document_source=current_stored_filename)
                logging.info(f"🗑️ Removed old document {current_stored_filename} from vector storage")
                
                vector_metadata = {
                    'file_type': file_ext[1:],
                    'upload_method': 'manual_update',
                    'file_size': file_size,
                    'source_type': current_source_type,
                    'original_filename': new_original_filename,
                    'updated_at': get_current_datetime().isoformat(),
                    'mime_type': mime_type,
                    'storage_path': new_storage_path
                }
                if metadata:
                    vector_metadata.update(metadata)
                    
                success = process_document_for_vector_storage(
                    file_path=file_path,
                    document_name=new_original_filename,
                    document_source=new_stored_filename,
                    metadata=vector_metadata,
                    document_id=doc_id,
                    storage_path=new_storage_path
                )
                if success:
                    logging.info(f"✅ Updated document {new_original_filename} added to vector storage")
                    try:
                        chatbot().invalidate_document_cache(new_stored_filename)
                    except Exception:
                        logging.debug("Failed to invalidate chatbot cache after document update", exc_info=True)
                else:
                    logging.warning(f"⚠️ Failed to add updated document {new_original_filename} to vector storage")
            except Exception as e:
                logging.warning(f"Vector storage processing failed for updated document {new_original_filename}: {e}")
        else:
            logging.info(f"📄 Updated file type {file_ext} not supported for vector storage, saved file only")
            logging.info(f"Supported types: {', '.join(supported_extensions)}")
        
        # Delete old file
        try:
            if current_storage_path and os.path.exists(current_storage_path):
                os.remove(current_storage_path)
                logging.info(f"Deleted old file: {current_storage_path}")
        except Exception as e:
            logging.warning(f"Failed to delete old file {current_storage_path}: {e}")
    
    elif metadata:
        # Update only metadata (re-process vector storage with new metadata)
        try:
            # Remove old document from vector storage
            delete_from_vectordb(document_source=current_stored_filename)
            
            # Re-add document with updated metadata
            if current_storage_path and os.path.exists(current_storage_path):
                vector_metadata = {
                    'upload_method': 'metadata_update',
                    'source_type': current_source_type,
                    'updated_at': get_current_datetime().isoformat(),
                    'storage_path': current_storage_path
                }
                vector_metadata.update(metadata)

                success = process_document_for_vector_storage(
                    file_path=current_storage_path,
                    document_name=original_filename or current_stored_filename,
                    document_source=current_stored_filename,
                    metadata=vector_metadata,
                    document_id=doc_id,
                    storage_path=current_storage_path
                )

                if success:
                    logging.info(f"✅ Updated metadata for document {current_stored_filename} in vector storage")
                    try:
                        chatbot().invalidate_document_cache(current_stored_filename)
                    except Exception:
                        logging.debug("Failed to invalidate chatbot cache after metadata update", exc_info=True)
                else:
                    logging.warning(f"⚠️ Failed to update metadata for document {current_stored_filename} in vector storage")
            else:
                logging.warning(f"📄 File {current_storage_path} not found on disk, skipping vector storage update")

        except Exception as e:
            logging.warning(f"Failed to update vector storage metadata: {e}")

    if not update_fields:
        return jsonify({'error': 'Tidak ada perubahan yang dilakukan'}), 400

    update_values.append(doc_id)

    # Update database
    query = f'UPDATE documents SET {", ".join(update_fields)} WHERE id=%s'
    affected_rows, _ = safe_db_query(query, tuple(update_values))

    return {"message": "Berhasil memperbarui dokumen"}, 200

@documents_bp.route('/documents/<doc_id>', methods=['DELETE'])
@swag_from(yaml_path("documents_id_delete.yml"))
def delete_document(doc_id, **kwargs):
    """Delete a specific document by ID."""
    # Get document info with new structure
    check_query = 'SELECT source_type, stored_filename, storage_path, original_filename FROM documents WHERE id=%s'
    rows, _ = safe_db_query(check_query, (doc_id,))
    if not isinstance(rows, list) or not rows:
        return jsonify({'error': 'Dokumen tidak ditemukan'}), 404
    
    source_type = rows[0][0]
    stored_filename = rows[0][1]
    storage_path = rows[0][2]
    original_filename = rows[0][3]
    
    # Optional: Add business rules for deletion restrictions
    # if source_type == 'portal':
    #     return jsonify({'error': 'Dokumen portal tidak dapat dihapus'}), 403

    # Delete from vector database first
    delete_from_vectordb(document_source=stored_filename)

    # Invalidate chatbot cache for this document
    try:
        chatbot().invalidate_document_cache(stored_filename)
        logging.info(f"Cache invalidated for document: {stored_filename}")
    except Exception as e:
        logging.warning(f"Failed to invalidate chatbot cache for {stored_filename}: {e}")

    # Delete physical file
    deleted_file = None
    if storage_path and os.path.exists(storage_path):
        try:
            os.remove(storage_path)
            deleted_file = original_filename
            logging.info(f"Deleted file: {storage_path}")
        except Exception as e:
            logging.warning(f"Failed to delete file {storage_path}: {e}")

    # Delete from database
    query = 'DELETE FROM documents WHERE id=%s;'
    affected_rows, _ = safe_db_query(query, (doc_id,))

    response_data = {"message": "Berhasil menghapus data documents"}
    if deleted_file:
        response_data["deleted_file"] = deleted_file

    return response_data, 200

@documents_bp.route('/documents', methods=['DELETE'])
@swag_from(yaml_path("documents_delete_all.yml"))
def delete_all_documents(**kwargs):
    """Delete all documents and files."""
    # Delete all from vector database first
    delete_all_from_vectordb()

    # Clear all chatbot caches
    try:
        chatbot().clear_cache()
        logging.info("All chatbot caches cleared")
    except Exception as e:
        logging.warning(f"Failed to clear chatbot cache: {e}")

    # Get all documents to delete their files
    query = 'SELECT storage_path, original_filename FROM documents'
    rows, _ = safe_db_query(query, ())
    
    deleted_files = []
    if isinstance(rows, list):
        for row in rows:
            storage_path = row[0]
            original_filename = row[1]
            if storage_path and os.path.exists(storage_path):
                try:
                    os.remove(storage_path)
                    deleted_files.append(original_filename)
                    logging.info(f"Deleted file: {storage_path}")
                except Exception as e:
                    logging.warning(f"Failed to delete file {storage_path}: {e}")

    # Delete all document folders (for cleanup)
    document_folders = [
        data_path('documents', 'admin'),
        data_path('documents', 'user'), 
        data_path('documents', 'portal'),
        data_path('documents', 'website')
    ]
    
    for folder in document_folders:
        if os.path.exists(folder):
            try:
                import shutil
                shutil.rmtree(folder)
                logging.info(f"Removed folder: {folder}")
            except Exception as e:
                logging.warning(f"Failed to remove folder {folder}: {e}")

    # Delete all data from documents table
    query = 'DELETE FROM documents'
    affected_rows, _ = safe_db_query(query, ())

    return {"message": "Berhasil menghapus semua data documents dan file", "deleted_files": deleted_files}, 200


@documents_bp.route('/documents/sync', methods=['POST'])
@swag_from(yaml_path('documents_sync_trigger.yml'))
def trigger_documents_sync(**kwargs):
    """Trigger portal & website document sync without restarting the container."""
    user = _get_request_user(kwargs) or {}
    if not _is_allowed_to_sync_documents(user):
        return jsonify({"message": "Access sinkronisasi dokumen tidak diizinkan"}), 403

    triggered_by = user.get('username') or user.get('user_id')
    identifier = str(triggered_by) if triggered_by else None

    started, status = DocumentSyncManager.trigger(
        triggered_by=identifier,
        wait_for_db=True,
    )

    if started:
        message = "Proses sinkronisasi dokumen portal & website telah dimulai"
        http_status = 202
    else:
        message = "Sinkronisasi dokumen portal & website sedang berjalan"
        http_status = 409

    return jsonify({"message": message, "status": status}), http_status


@documents_bp.route('/documents/sync', methods=['GET'])
@swag_from(yaml_path('documents_sync_status.yml'))
def get_documents_sync_status(**kwargs):
    """Get the current status of the portal & website document sync job."""
    user = _get_request_user(kwargs) or {}
    if not _is_allowed_to_sync_documents(user):
        return jsonify({"message": "Access sinkronisasi dokumen tidak diizinkan"}), 403

    status = DocumentSyncManager.status()
    return jsonify(
        {"message": "Status sinkronisasi dokumen portal & website", "status": status}
    ), 200


@documents_bp.route('/documents/sync-logs', methods=['GET'])
@swag_from(yaml_path('documents_sync_logs_get.yml'))
def get_sync_logs(**kwargs):
    """Get sync logs with pagination and filtering."""
    user = _get_request_user(kwargs) or {}
    if not _is_allowed_to_sync_documents(user):
        return jsonify({"message": "Access log sinkronisasi dokumen tidak diizinkan"}), 403

    # Pagination params
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        if page < 1: page = 1
        if page_size < 1 or page_size > 100: page_size = 10
    except Exception:
        page, page_size = 1, 10

    filters, error_message = _parse_sync_log_filters()
    if error_message:
        return jsonify({"message": error_message}), 400

    sync_type = filters.get("sync_type")
    status = filters.get("status")
    search = filters.get("search")
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")

    try:
        from app.utils.sync_logger import SyncLogger
        logs, total = SyncLogger.get_sync_logs(
            page=page,
            page_size=page_size,
            sync_type=sync_type,
            status=status,
            search=search,
            start_date=start_date,
            end_date=end_date,
        )

        return jsonify({
            "message": "Berhasil mengambil log sinkronisasi dokumen",
            "data": logs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total // page_size) + (1 if total % page_size else 0)
            }
        }), 200

    except Exception as e:
        logging.error(f"Error retrieving sync logs: {e}")
        return jsonify({"message": "Gagal mengambil log sinkronisasi dokumen"}), 500


@documents_bp.route('/documents/sync-logs', methods=['DELETE'])
@swag_from(yaml_path('documents_sync_logs_delete.yml'))
def delete_sync_logs(**kwargs):
    """Delete sync logs with optional filtering."""
    user = _get_request_user(kwargs) or {}
    if not _is_allowed_to_sync_documents(user):
        return jsonify({"message": "Access log sinkronisasi dokumen tidak diizinkan"}), 403

    filters, error_message = _parse_sync_log_filters()
    if error_message:
        return jsonify({"message": error_message}), 400

    try:
        from app.utils.sync_logger import SyncLogger
        deleted_count = SyncLogger.delete_sync_logs(
            sync_type=filters.get("sync_type"),
            status=filters.get("status"),
            search=filters.get("search"),
            start_date=filters.get("start_date"),
            end_date=filters.get("end_date"),
        )

        return jsonify({
            "message": "Log sinkronisasi dokumen berhasil dihapus",
            "deleted": deleted_count
        }), 200
    except Exception as e:
        logging.error(f"Error deleting sync logs: {e}")
        return jsonify({"message": "Gagal menghapus log sinkronisasi dokumen"}), 500


@documents_bp.route('/documents/sync-logs/<sync_log_id>', methods=['GET'])
@swag_from(yaml_path('documents_sync_log_details_get.yml'))
def get_sync_log_details(sync_log_id, **kwargs):
    """Get detailed information about a specific sync log."""
    user = _get_request_user(kwargs) or {}
    if not _is_allowed_to_sync_documents(user):
        return jsonify({"message": "Access detail log sinkronisasi dokumen tidak diizinkan"}), 403

    try:
        from app.utils.sync_logger import SyncLogger
        sync_log, document_details = SyncLogger.get_sync_log_details(sync_log_id)

        if not sync_log:
            return jsonify({"message": "Log sinkronisasi tidak ditemukan"}), 404

        normalized_status = _normalize_sync_status(sync_log.get("status"))
        if normalized_status:
            sync_log["status_normalized"] = normalized_status

        failed_documents = _build_failed_documents(
            document_details,
            global_error_message=sync_log.get("error_message"),
        )

        return jsonify({
            "message": "Berhasil mengambil detail log sinkronisasi dokumen",
            "data": {
                "sync_log": sync_log,
                "document_details": document_details,
                "failed_documents": failed_documents,
            }
        }), 200

    except Exception as e:
        logging.error(f"Error retrieving sync log details: {e}")
        return jsonify({"message": "Gagal mengambil detail log sinkronisasi dokumen"}), 500

@documents_bp.route('/documents/embed', methods=['POST'])
@swag_from(yaml_path('documents_embed_local.yml'))
def embed_local_documents(**kwargs):
    """
    Embed portal documents from filesystem into vector store.
    """
    try:
        from app.utils.local_embedding import embed_local_documents_logic, embed_specific_files
        
        data = request.get_json() or {}
        
        # Get parameters from request
        documents_path = data.get('documents_path', 'data/documents/portal')
        source_type = data.get('source_type', 'portal')  # default to portal
        skip_existing = data.get('skip_existing', True)
        allowed_extensions = data.get('allowed_extensions', ['.pdf', '.txt', '.doc', '.docx', '.png', '.jpg', '.jpeg'])
        specific_files = data.get('specific_files', None)
        
        logging.info(f"Starting local document embedding with parameters:")
        logging.info(f"  - Path: {documents_path}")
        logging.info(f"  - Source type: {source_type}")
        logging.info(f"  - Skip existing: {skip_existing}")
        logging.info(f"  - Extensions: {allowed_extensions}")
        logging.info(f"  - Specific files: {specific_files}")
        
        # Process documents
        if specific_files and isinstance(specific_files, list):
            # Process specific files
            result = embed_specific_files(
                file_paths=specific_files,
                source_type=source_type,
                base_path=documents_path
            )
        else:
            # Process all documents in directory
            result = embed_local_documents_logic(
                documents_path=documents_path,
                source_type=source_type,
                skip_existing=skip_existing,
                allowed_extensions=allowed_extensions
            )
        
        # Format response
        processed_count = len(result.get("processed_files", []))
        skipped_count = len(result.get("skipped_files", []))
        error_count = len(result.get("errors", []))
        
        response_data = {
            "message": f"Local document embedding completed. Processed: {processed_count}, Skipped: {skipped_count}, Errors: {error_count}",
            "processed_files": result.get("processed_files", []),
            "skipped_files": result.get("skipped_files", []),
            "errors": result.get("errors", []),
            "summary": result.get("summary", {}),
            "success": error_count == 0
        }
        
        status_code = 200 if error_count == 0 else 207  # 207 Multi-Status for partial success
        
        return response_data, status_code
        
    except Exception as e:
        logging.error(f"Error in embed_local_documents: {e}")
        return {
            "message": f"Error embedding local documents: {str(e)}",
            "success": False,
            "errors": [str(e)]
        }, 500

@documents_bp.route('/documents/scan', methods=['GET'])
@swag_from(yaml_path('documents_scan_local.yml'))
def scan_local_documents(**kwargs):
    """
    Scan local documents directory and return file information.
    """
    try:
        from pathlib import Path
        
        documents_path = request.args.get('path', 'data/documents/portal')
        allowed_extensions = request.args.getlist('extensions') or ['.pdf', '.txt', '.doc', '.docx', '.png', '.jpg', '.jpeg']
        
        # Convert to lowercase for comparison
        allowed_extensions = [ext.lower() for ext in allowed_extensions]
        
        # Get absolute path to documents directory
        project_root = Path(__file__).parent.parent.parent
        full_documents_path = project_root / documents_path
        
        if not full_documents_path.exists():
            return {
                "message": f"Documents path does not exist: {documents_path}",
                "files": [],
                "success": False
            }, 404
        
        files_info = []
        
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
                    continue
                
                try:
                    relative_path = file_path.relative_to(full_documents_path)
                    file_stat = file_path.stat()
                    
                    # Check if file exists in database
                    query = """
                        SELECT id, created_at FROM documents 
                        WHERE storage_path = %s
                    """
                    result, _ = safe_db_query(query, (str(relative_path),))
                    exists_in_db = bool(result and len(result) > 0)
                    db_created_at = result[0][1] if exists_in_db else None
                    
                    files_info.append({
                        "filename": filename,
                        "relative_path": str(relative_path),
                        "extension": file_extension,
                        "size_bytes": file_stat.st_size,
                        "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                        "modified_at": get_datetime_from_timestamp(file_stat.st_mtime).isoformat(),
                        "exists_in_db": exists_in_db,
                        "db_created_at": db_created_at.isoformat() if db_created_at else None
                    })
                    
                except Exception as e:
                    logging.warning(f"Error getting info for {filename}: {e}")
                    continue
        
        # Sort files by relative path
        files_info.sort(key=lambda x: x["relative_path"])
        
        # Summary statistics
        total_files = len(files_info)
        total_size_mb = sum(f["size_mb"] for f in files_info)
        files_in_db = sum(1 for f in files_info if f["exists_in_db"])
        files_not_in_db = total_files - files_in_db
        
        return {
            "message": f"Found {total_files} files in {documents_path}",
            "files": files_info,
            "summary": {
                "total_files": total_files,
                "total_size_mb": round(total_size_mb, 2),
                "files_in_database": files_in_db,
                "files_not_in_database": files_not_in_db,
                "extensions_found": list(set(f["extension"] for f in files_info))
            },
            "success": True
        }, 200
        
    except Exception as e:
        logging.error(f"Error in scan_local_documents: {e}")
        return {
            "message": f"Error scanning local documents: {str(e)}",
            "success": False
        }, 500
