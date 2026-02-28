from flask import Blueprint, request, jsonify, send_file
from flasgger import swag_from

from app.utils.general import yaml_path
from app.utils.document import data_path, verify_document_exists
from app.utils.auth import validate_jwt_token
from app.utils.database import safe_db_query

import os
import logging
import mimetypes

storage_bp = Blueprint('storage', __name__)

def get_document_by_id(document_id):
    """
    Get document information by document ID.
    Returns document info if found, None if not found.
    """
    try:
        query = """
            SELECT 
                id,
                original_filename,
                stored_filename,
                mime_type,
                size_bytes,
                storage_path,
                source_type,
                created_at
            FROM documents 
            WHERE id = %s
        """
        results, _ = safe_db_query(query, [document_id])
        
        if isinstance(results, list) and results:
            row = results[0]
            document = {
                "id": str(row[0]),
                "original_filename": row[1],
                "stored_filename": row[2],
                "mime_type": row[3],
                "size_bytes": row[4],
                "storage_path": row[5],
                "source_type": row[6],
                "created_at": row[7]
            }
            logging.info(f"Document found: {document['original_filename']} (ID: {document['id']})")
            return document
        else:
            logging.warning(f"Document not found for ID: {document_id}")
            return None
            
    except Exception as e:
        logging.error(f"Error getting document by ID {document_id}: {e}", exc_info=True)
        return None

def authenticate_user_from_token(access_token):
    """
    Authenticate user from access token parameter.
    Returns user info if valid, None if invalid.
    """
    if not access_token:
        return None
        
    try:
        # Validate JWT token
        validated_token = validate_jwt_token(access_token)
        if not validated_token:
            logging.warning("Invalid or expired access token")
            return None

        # Ensure this is an access token
        if validated_token.get("type") != "access":
            logging.warning("Invalid token type, expected access token")
            return None

        # Get user from database
        query = """
            SELECT
                u.id,
                r.id AS role_id,
                u.name,
                u.username,
                u.is_portal,
                u.created_at,
                u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.id = %s
        """
        results, _ = safe_db_query(query, [validated_token["user_id"]])
        
        if isinstance(results, list) and results:
            row = results[0]
            user = {
                "user_id": str(row[0]),
                "role_id": row[1],
                "name": row[2],
                "username": row[3],
                "is_portal": row[4],
            }
            logging.info(f"User authenticated: {user['username']} (ID: {user['user_id']})")
            return user
        else:
            logging.warning(f"User not found for token user_id: {validated_token.get('user_id')}")
            return None
            
    except Exception as e:
        logging.error(f"Authentication error: {e}", exc_info=True)
        return None

@storage_bp.route('/storage/<docs_id>', methods=['GET'])
@swag_from(yaml_path("storage.yml"))
def download(docs_id):
    """
    Serve document files with preview and download modes using document ID.
    
    Path Parameters:
    - docs_id: Required. Document ID (UUID) to serve
    
    Query Parameters:
    - download: 'true'/'false' (default: 'false' for preview mode)
    # - access_token: Required. JWT access token for authentication (TEMPORARILY DISABLED)
    
    Preview mode (download=false): PDF and images shown inline, others downloaded
    Download mode (download=true): All files forced download
    
    # Authentication: Requires valid access token in access_token parameter (TEMPORARILY DISABLED)
    
    Examples:
    - /storage/123e4567-e89b-12d3-a456-426614174000 -> Show document in browser (preview)
    - /storage/123e4567-e89b-12d3-a456-426614174000?download=true -> Force download document
    - /storage/123e4567-e89b-12d3-a456-426614174000?download=false -> Preview document in browser
    """
    try:
        # TEMPORARILY DISABLED: Authenticate user from access_token parameter
        # access_token = request.args.get('access_token')
        # user = authenticate_user_from_token(access_token)
        
        # if not user:
        #     logging.warning("Unauthorized access attempt to storage endpoint")
        #     return jsonify({
        #         "error": "Authentication required",
        #         "message": "Parameter 'access_token' diperlukan dengan token yang valid."
        #     }), 401
        
        # Mock user for logging purposes (temporary)
        user = {
            "username": "anonymous",
            "user_id": "temporary"
        }

        # Validate document ID from path parameter
        if not docs_id:
            logging.warning("Empty document ID in path parameter")
            return jsonify({
                "error": "Document ID tidak valid",
                "message": "Harap sertakan document ID yang valid di URL."
            }), 400
            
        # Validate UUID format
        try:
            import uuid
            uuid.UUID(docs_id)
        except ValueError:
            logging.warning(f"Invalid document ID format: {docs_id}")
            return jsonify({
                "error": "Document ID tidak valid",
                "message": "Format document ID harus berupa UUID yang valid."
            }), 400

        # Get download parameter - only support 'true'/'false' (default: false for preview)
        download_param = request.args.get('download', 'false').lower()
        force_download = download_param in ['true', '1', 'yes']
        
        # Get document information from database
        document = get_document_by_id(docs_id)
        if not document:
            logging.warning(f"Document not found: {docs_id}")
            return jsonify({
                "error": "Dokumen tidak ditemukan",
                "message": f"Dokumen dengan ID '{docs_id}' tidak tersedia."
            }), 404

        # Extract document information
        stored_filename = document['stored_filename']
        original_filename = document['original_filename']
        mime_type = document['mime_type']
        storage_path = document['storage_path']
        
        # Resolve storage path - handle both absolute and relative paths
        if os.path.isabs(storage_path):
            # Absolute path - use as is
            resolved_path = storage_path
        else:
            # Relative path - resolve relative to current working directory
            # The storage_path from database is relative to project root
            resolved_path = os.path.join(os.getcwd(), storage_path)
        
        # Verify the physical file exists
        if not os.path.exists(resolved_path):
            logging.warning(f"Physical file not found for document {docs_id}: {resolved_path}")
            return jsonify({
                "error": "File tidak ditemukan",
                "message": f"File dokumen dengan ID '{docs_id}' tidak tersedia di server."
            }), 404

        # Log the request details with user info
        mode_str = "download" if force_download else "preview"
        logging.info(f"User '{user['username']}' (ID: {user['user_id']}) serving document '{docs_id}' (original: '{original_filename}') in {mode_str} mode, mime: {mime_type}")

        # Determine if file should be served inline or as attachment
        if force_download:
            # Force download for all files when download=true
            as_attachment = True
        else:
            # Preview mode (download=false): show PDF and images inline, download others
            is_pdf = mime_type == 'application/pdf'
            is_image = mime_type and mime_type.startswith('image/')
            as_attachment = not (is_pdf or is_image)

        # Serve file using the storage path from database
        try:
            return send_file(resolved_path, as_attachment=as_attachment,
                       download_name=original_filename,
                       mimetype=mime_type)
        except Exception as send_error:
            logging.error(f"Error sending file {docs_id}: {send_error}")
            return jsonify({
                "error": "Internal Server Error",
                "message": "Terjadi kesalahan pada server. Silakan coba lagi nanti."
            }), 500

    except Exception as e:
        # Log the specific error with more context
        error_msg = str(e)
        docs_id_safe = docs_id if 'docs_id' in locals() else 'unknown'
        logging.error(f"Unexpected error serving document '{docs_id_safe}': {error_msg}", exc_info=True)
        return jsonify({
            "error": "Internal Server Error",
            "message": "Terjadi kesalahan pada server. Silakan coba lagi nanti."
        }), 500
