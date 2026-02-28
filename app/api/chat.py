from flask import Blueprint, request, jsonify, send_from_directory
from flasgger import swag_from

from app.utils.auth import require_auth, require_access
from app.utils.general import chatbot, yaml_path
from app.utils.database import safe_db_query
from app.utils.document import verify_document_exists
from app.utils.permission import get_setting, validate_chat_request, can_create_chat_topic, get_chat_limits_info
from app.utils.text import to_bool
from app.services.agent.translation_service import translation_service

import uuid
import os
import logging
import mimetypes
import base64
import re
import json

chat_bp = Blueprint('chat', __name__)

def save_attachment(attachment, folder="data", filename="output"):
    """
    Simpan lampiran ke folder. Mendukung dua format input:
    - String base64 dengan prefix data URI (data:image/xxx;base64,...)
    - Path file lokal (string path) untuk upload file biasa (non-base64)
    
    Args:
        attachment (str): Base64 data URI ATAU path file lokal.
        folder (str): Nama folder tujuan simpan file.
        filename (str): Nama file output.
    
    Returns:
        str: Path file hasil decode.
    """
    # Pastikan folder ada
    os.makedirs(folder, exist_ok=True)
    dpi = None
    # Jika string diawali dengan data:...;base64, perlakukan sebagai base64
    if isinstance(attachment, str) and attachment.startswith("data:"):
        match = re.match(r"data:(.*?);base64,(.*)", attachment)
        if not match:
            raise ValueError("Format attachment tidak valid")
        mime_type, b64_data = match.groups()
        ext = mime_type.split("/")[-1]
        file_bytes = base64.b64decode(b64_data)
        filepath = os.path.join(folder, f"{os.path.splitext(filename)[0]}.{ext}")
        with open(filepath, "wb") as f:
            f.write(file_bytes)
    else:
        try:
            from werkzeug.datastructures import FileStorage
        except Exception:
            FileStorage = None

        if FileStorage is not None and isinstance(attachment, FileStorage):
            # Jika FileStorage, gunakan filename asli utk ext dan simpan langsung
            original_name = attachment.filename or filename
            src_ext = os.path.splitext(original_name)[1].lstrip('.')
            ext = src_ext or 'bin'
            mime_type = attachment.mimetype or mimetypes.guess_type(original_name)[0] or 'application/octet-stream'
            filepath = os.path.join(folder, f"{os.path.splitext(filename)[0]}.{ext}")
            # Simpan menggunakan .save
            attachment.save(filepath)
            # Ambil metadata DPI jika gambar
            try:
                image_exts = {"jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif", "webp"}
                if ext.lower() in image_exts:
                    from PIL import Image
                    with Image.open(attachment) as img:
                        print(f"{img.info}")
                        dpi = img.info.get('dpi')
                    # Simpan DPI di variabel lokal untuk dikembalikan bila perlu
                    # (Tidak mengubah return schema yang ada)
            except Exception:
                pass
        else:
            # Path file biasa; salin ke folder tujuan
            if not isinstance(attachment, str) or not os.path.exists(attachment):
                raise ValueError("Attachment tidak ditemukan atau path tidak valid")
            # Tentukan ext dari nama file sumber
            src_ext = os.path.splitext(attachment)[1].lstrip('.')
            ext = src_ext or 'bin'
            # Coba tebak mimetype jika memungkinkan
            mime_type, _ = mimetypes.guess_type(attachment)
            mime_type = mime_type or 'application/octet-stream'
            filepath = os.path.join(folder, f"{os.path.splitext(filename)[0]}.{ext}")
            # Salin isi file ke lokasi baru
            with open(attachment, 'rb') as src, open(filepath, 'wb') as dst:
                dst.write(src.read())
            # Ambil metadata DPI jika gambar
            try:
                image_exts = {"jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif", "webp"}
                if ext.lower() in image_exts:
                    from PIL import Image
                    with Image.open(attachment) as img:
                        print(f"{img.info}")
                        dpi = img.info.get('dpi')
                    # Simpan DPI di variabel lokal untuk dikembalikan bila perlu
                    # (Tidak mengubah return schema yang ada)
            except Exception:
                pass

    # Ambil ukuran file
    file_size = os.path.getsize(filepath)

    return {
        "mimetype": mime_type,
        "ext": ext,
        "size": file_size,
        "path": filepath,
        "filename": f"{os.path.basename(os.path.splitext(filename)[0])}.{ext}",
        "dpi": dpi
    }

def delete_attachment(saved_files):
    """
    Hapus file attachment yang sudah terlanjur di save.

    Args:
        saved_files (list): List Saved File yang akan dihapus.
    """
    for file in saved_files:
        try:
            if file.get('path') and os.path.exists(file['path']):
                os.remove(file['path'])
        except Exception as e:
            pass
    
    return True

def remove_folder_chat(path):
    """
    Helper untuk Hapus folder dan semua isinya jika ada.
    """
    logging.debug("Mulai proses penghapusan folder chat: %s", path)
    try:
        # Jika Path kosong, tidak ada yang dihapus.
        if not path:
            logging.debug("Path folder chat kosong, tidak ada tindakan diambil")
            return True

        normalized_path = os.path.normpath(path)
        expected_parent = os.path.normpath("data/documents/chats")

        # Pastikan folder berada langsung di bawah data/documents/chats/<uuid>
        if os.path.dirname(normalized_path) != expected_parent:
            logging.debug(
                "Lewati penghapusan folder %s karena berada di luar direktori yang diizinkan",
                normalized_path,
            )
            return True

        # Lewati penghapusan jika bukan UUID yang valid.
        chat_id = os.path.basename(normalized_path)
        try:
            uuid.UUID(chat_id)
        except (ValueError, AttributeError):
            logging.debug(
                "Lewati penghapusan folder %s karena nama folder bukan UUID valid",
                normalized_path,
            )
            return True

        if os.path.exists(normalized_path):
            import shutil
            shutil.rmtree(normalized_path)  # hapus folder + semua isinya
            logging.info("Folder chat %s berhasil dihapus", normalized_path)
        else:
            logging.debug("Folder chat %s tidak ditemukan saat penghapusan", normalized_path)
    except Exception as e:
        logging.error("Terjadi kesalahan saat menghapus folder %s", path, exc_info=True)

@chat_bp.before_request
@require_auth
def check_access(**kwargs):
    # daftar exclude endpoint
    exclude = []

    if request.endpoint in exclude:
        return 

    # ambil user dari kwargs
    user = kwargs.get('user')

    # cek akses menu_user
    access = require_access(user, 'menu_chat')
    if not access or not access.get("value") : 
        return jsonify({"message": "Access tidak diizinkan"}), 403

# --- ASK QUESTION ---
@chat_bp.route('/chats/ask', methods=['POST'])
@swag_from(yaml_path("chats_ask.yml"))
@require_auth
def ask_question(**kwargs):
    """
    Endpoint to ask a question to the chatbot.
    It requires a valid session ID and a question in the request body.
    The session ID must be a valid UUID.
    Supports is_browse parameter for internet search functionality.
    """
    user = kwargs['user']
    user_id = user["user_id"]
    if request.is_json:
        data = request.get_json()
        attachments = data.get('with_document')
        if attachments is None:
            attachments = data.get('attachments')
        if attachments is not None and not isinstance(attachments, list):
            attachments = [attachments]
    else:
        data = request.form.to_dict()
        attachments = (
            request.files.getlist('with_document[]')
            or request.files.getlist('with_document')
            or request.files.getlist('attachments[]')
            or request.files.getlist('attachments')
        )
        if attachments == []:
            attachments = None

    if not data or "question" not in data:
        return jsonify({"message": "Pertanyaan tidak boleh kosong"}), 400

    question = data.get("question", "")
    max = get_setting("chat_max_text")
    if len(question) > max:
        return jsonify({"message": "Pertanyaan tidak boleh lebih dari {} karakter".format(max)}), 400

    chat_id_raw = data.get("chat_id")
    if chat_id_raw:
        try:
            uuid.UUID(chat_id_raw)
            chat_id = chat_id_raw
            chat_id_provided = True
        except Exception:
            return jsonify({"message": "Chat ID harus berupa UUID yang valid"}), 400
    else:
        chat_id = str(uuid.uuid4())
        chat_id_provided = False

    # Normalize toggle values to proper booleans (handles JSON and form submissions)
    is_browse_raw = data.get("is_browse", False)  # Add is_browse parameter
    # Backwards compatible: prefer new `is_company`, fallback to legacy `is_company_policy`
    is_company_raw = data.get("is_company", data.get("is_company_policy", False))
    is_general_raw = data.get("is_general", False)

    is_browse = to_bool(is_browse_raw) if isinstance(is_browse_raw, str) else bool(is_browse_raw)
    is_company = to_bool(is_company_raw) if isinstance(is_company_raw, str) else bool(is_company_raw)
    is_general = to_bool(is_general_raw) if isinstance(is_general_raw, str) else bool(is_general_raw)

    # Validasi chat_id harus sesuai dengan user_id (jika chat_id diberikan)
    if chat_id_provided:
        query_check_owner = "SELECT COUNT(*) FROM chats WHERE id = %s AND user_id = %s"
        rows, _ = safe_db_query(query_check_owner, [chat_id, user_id])
        
        if not rows or rows[0][0] == 0:
            return jsonify({"message": "Chat ID tidak ditemukan atau Anda tidak memiliki akses dengan Sesi ini."}), 403

    # Validasi batasan chat berdasarkan konfigurasi
    is_new_topic = not chat_id_provided  # Jika chat_id tidak diberikan, berarti topic baru
    existing_chat_id = chat_id if chat_id_provided else None
    
    validation = validate_chat_request(
        chat_id=existing_chat_id,
        is_new_topic=is_new_topic,
        user_data=user
    )
    
    if not validation["can_proceed"]:
        return jsonify({
            "message": validation["error_message"],
            "error_code": validation["error_code"],
            "limits": validation["limits"],
            "is_browse" : is_browse,
            "is_company" : is_company,
            "is_general" : is_general,
        }), 429  # Too Many Requests
    
    allow_attach = get_setting("attachment", False)
    allow_attach_size = get_setting("attachment_file_size", 0)
    allow_attach_type = get_setting("attachment_file_types", [])

    # Create UUID for save to chat_details and relations documents
    chat_detail_id = str(uuid.uuid4())

    saved_files = []
    if attachments :
        if not allow_attach :
            return jsonify({"message": "Anda tidak memiliki izin untuk mengunggah file"}), 400
        else : 
            if not isinstance(attachments, list):
                return jsonify({"message": "Request tidak valid"}), 400
            else :
                for idx, attachment in enumerate(attachments):
                    try:
                        path = save_attachment(attachment, folder=f"data/documents/chats/{chat_id}/{chat_detail_id}", filename=str(uuid.uuid4()))
                        saved_files.append(path)
                    except ValueError as e:
                        logging.error(f"Gagal mengunggah file: {e}")
                        delete_attachment(saved_files)
                        return jsonify({"message": "Terjadi kendala saat mengunggah. Periksa koneksi dan format file, lalu coba lagi."}), 400

                for idx, file in enumerate(saved_files, start=1):
                    if((file['size']/1024000) > allow_attach_size) :
                        delete_attachment(saved_files)
                        return jsonify({"message": "Ukuran file melebihi batas {max_size} MB.".format(max_size=allow_attach_size)}), 400
                    if(file['ext'] not in allow_attach_type) :
                        delete_attachment(saved_files)
                        return jsonify({"message": "Tipe file tidak didukung. Gunakan: {supported_types}.".format(supported_types=", ".join(allow_attach_type))}), 400

    logging.info(f"Processing question for user {user_id}, session {chat_id}")
    logging.info(f"Question: {question[:100]}")
    logging.info(f"Browse internet: {is_browse}")
    logging.info(f"Company mode: {is_company}")
    logging.info(f"General mode: {is_general}")
    logging.info(f"Attachments: {len(saved_files)} files")

    # Detect user language and translate question to Indonesian.
    # Use per-chat language hint (stored in chats.options) to avoid language flip-flopping on short replies.
    language_hint = None
    try:
        if chat_id and chat_id.strip():
            rows, _ = safe_db_query(
                "SELECT options FROM chats WHERE id = %s AND user_id = %s LIMIT 1",
                (chat_id, user_id),
            )
            if rows and isinstance(rows, list) and rows[0] and rows[0][0]:
                options_raw = rows[0][0]
                if isinstance(options_raw, str):
                    try:
                        options_json = json.loads(options_raw)
                    except Exception:
                        options_json = {}
                elif isinstance(options_raw, dict):
                    options_json = options_raw
                else:
                    options_json = {}

                lang = (options_json.get('original_language') or '').lower().strip()
                if lang in {'id', 'en'}:
                    language_hint = lang
    except Exception as e:
        logging.debug(f"Failed to load chat language hint: {e}")

    translated, original_language = translation_service.detect_and_translate_to_indonesian(
        question, language_hint=language_hint
    )

    # Call chatbot.ask with flags: is_browse, is_company, is_general
    # Pass both original question and translated question
    logging.info("Calling chatbot.ask() method...")
    answer = chatbot().ask(translated, chat_id, chat_detail_id, user_id, user_data=user, is_browse=is_browse, is_company=is_company, is_general=is_general, attachments=saved_files, original_language=original_language, original_question=question)
    logging.info(f"chatbot.ask() completed successfully")
    logging.info(f"Answer received, type: {type(answer)}, content: {str(answer)[:100]}...")

    if isinstance(answer, dict):
        answer["question"] = question
        # Only include chat_id in answer data if it was NOT provided in the request
        if not chat_id_provided:
            answer["chat_id"] = chat_id
    
    answer["is_browse"] = is_browse
    answer["is_company"] = is_company
    answer["is_general"] = is_general

    return jsonify({"message": "Berhasil mendapatkan jawaban", "data": answer}), 200

# --- CHAT FEEDBACK (by chat_id) ---
@chat_bp.route('/chats/feedback/<chat_id>', methods=['PATCH'])
@require_auth
@swag_from(yaml_path("chats_feedback.yml"))
def chat_feedback(chat_id, **kwargs):
    """
    Endpoint to submit feedback for a specific chat message.
    It updates the feedback field in the chat_details table for the given chat_id.
    """
    user = kwargs['user']
    data = request.get_json()
    feedback = data.get('feedback')
    # Validasi feedback
    if feedback not in ["1", "-1", None]:
        return jsonify({"message": "Feedback harus 1 (like), -1 (dislike), atau null"}), 400
    # Update feedback pada chat_details
    query = "UPDATE chat_details SET feedback = %s WHERE id = %s"
    affected_rows, _ = safe_db_query(query, (feedback, chat_id))
    if affected_rows == 0:
        return jsonify({"message": "Chat tidak ditemukan"}), 404
    return jsonify({"message": "Feedback berhasil disimpan"}), 200

# --- RENAME TITLE (by id) ---
@chat_bp.route('/chats/rename/<chat_id>', methods=['PATCH'])
@swag_from(yaml_path("chats_rename.yml"))
@require_auth
def chats_rename(chat_id, **kwargs):
    """
    Rename (update) title untuk satu baris chat_history berdasarkan id baris.
    Untuk mengganti judul sesi yang tampil di /chats/history pastikan mengubah baris pertama (created_at paling awal) pada session tersebut.
    """
    user = kwargs['user']
    data = request.get_json() or {}
    new_title = (data.get('title') or "").strip()
    if not new_title:
        return jsonify({"message": "Title tidak boleh kosong"}), 400
    if len(new_title) > 255:
        # Batas untuk judul list
        new_title = new_title[:255]
    query = "UPDATE chats SET subject = %s WHERE id = %s AND user_id = %s"
    affected, _ = safe_db_query(query, (new_title, chat_id, user["user_id"]))
    if affected == 0:
        return jsonify({"message": "Chat tidak ditemukan"}), 404
    return jsonify({"message": "Berhasil mengubah title", "data": {"id": chat_id, "title": new_title}}), 200

# --- PIN / UNPIN CHAT (by id) ---
@chat_bp.route('/chats/pin/<chat_id>', methods=['PATCH'])
@swag_from(yaml_path("chats_pin.yml"))
@require_auth
def chats_pin(chat_id, **kwargs):
    """
    Set kolom pinned untuk satu baris chat_history (bisa digunakan untuk menandai sesi).
    Frontend dapat menampilkan sesi sebagai pinned jika salah satu baris pada chat_id memiliki pinned = true.
    Body boleh mengirim {"pinned": true/false}, default true.
    """
    user = kwargs['user']
    data = request.get_json() or {}
    pinned_value = data.get('pinned', True)
    if not isinstance(pinned_value, bool):
        return jsonify({"message": "Field pinned harus boolean"}), 400
    query = "UPDATE chats SET pinned = %s WHERE id = %s AND user_id = %s"
    affected, _ = safe_db_query(query, (pinned_value, chat_id, user["user_id"]))
    if affected == 0:
        return jsonify({"message": "Chat tidak ditemukan"}), 404
    return jsonify({"message": ("Berhasil pin chat" if pinned_value else "Berhasil unpin chat"), "data": {"id": chat_id, "pinned": pinned_value}}), 200

# --- GET CHAT HISTORY ---
@chat_bp.route('/chats', methods=['GET'])
@swag_from(yaml_path("chats_history.yml"))
@require_auth
def chat_history(**kwargs):
    """
    Ambil daftar sesi chat user:
    - Judul diambil dari baris pertama (created_at paling awal) per chat_id (kolom title)
    - Pinned: TRUE jika ada salah satu baris pada chat_id bertanda pinned = TRUE
    - Urutan: pinned DESC lalu created_at pertama DESC (pinned di atas)
    - Option: Option daripada chat (is_browse, is_company, is_general)
    """
    user = kwargs['user']
    user_id = user["user_id"]

    # Schema baru: gunakan tabel chats sebagai daftar sesi
    # Kembalikan kolom kompatibel: id, chat_id, title, pinned, created_at
    query = """
        SELECT 
            c.id,
            c.id AS chat_id,
            COALESCE(NULLIF(TRIM(c.subject), ''), 'Untitled Session') AS title,
            COALESCE(c.pinned, FALSE) AS pinned,
            c.created_at,
            c.options
        FROM chats c
        WHERE c.user_id = %s
        ORDER BY COALESCE(c.pinned, FALSE) DESC, c.created_at DESC;
    """

    rows, columns = safe_db_query(query, [user_id])

    # Normalisasi rows -> list of dicts
    result = []
    if isinstance(rows, list) and columns:
        col_index = {c: i for i, c in enumerate(columns)}
        for r in rows:
            if not isinstance(r, (list, tuple)):
                continue
            
            try:
                result.append({
                    "id": r[col_index.get("id")],
                    "chat_id": r[col_index.get("chat_id")],
                    "title": r[col_index.get("title")],
                    "pinned": bool(r[col_index.get("pinned")]),
                    # created_at bisa dipakai front-end untuk sorting client side bila perlu
                    "created_at": r[col_index.get("created_at")],
                    "is_browse": r[col_index.get("options")].get("is_browse", False) if r[col_index.get("options")] else False,
                    "is_company": r[col_index.get("options")].get("is_company", False) if r[col_index.get("options")] else False,
                    "is_general": r[col_index.get("options")].get("is_general", False)if r[col_index.get("options")] else False 
                })
            except Exception:
                # Lewati baris rusak agar endpoint tetap jalan
                continue

    return jsonify({"message": "Berhasil mengambil riwayat chat", "data": result}), 200

# --- GET CHAT DETAIL (by chat_id) ---
@chat_bp.route('/chats/<chat_id>', methods=['GET'])
@swag_from(yaml_path("chats_detail.yml"))
@require_auth
def chat_detail(chat_id, **kwargs):
    """
    Endpoint to retrieve chat history for a specific session ID.
    It returns all chat messages for the given session ID, following the same output format as ask endpoint.
    Now includes source_documents in the same format as the ask endpoint.
    """
    user = kwargs['user']
    try:
        uuid.UUID(chat_id)
    except Exception:
        return jsonify({"message": "Session ID harus berupa UUID yang valid"}), 400

    # ambil data chat berdasarkan id
    try:
        sel_query = """
            SELECT
                id,
                options
            FROM chats
            WHERE id = %s
        """

        results, _ = safe_db_query(sel_query, [chat_id])
        chat = (
            tuple(results[0])
            if results and isinstance(results, list) and len(results) > 0
            else None
        )

        if not chat:
            return jsonify({"error": "Gagal mengambil data chats"}), 404

    except Exception as e:
        logging.error(f"Data chats error: {e}")
        return jsonify({"error": "Gagal mengambil data chat"}), 404

    # decode options jika ada
    options = {}
    if chat[1]:
        try:
            options = json.loads(chat[1]) if isinstance(chat[1], str) else chat[1]
            if not isinstance(options, dict):
                options = {}
        except Exception:
            options = {}
    
    # Ambil dokumen terkait chat_id dari tabel document dan bangun URL
    try:
        doc_query = "SELECT id, stored_filename, storage_path, mime_type FROM documents WHERE chat_id = %s"
        doc_rows, doc_cols = safe_db_query(doc_query, [chat_id])

        documents = {}
        if isinstance(doc_rows, list) and doc_rows:
            col_idx = {c: i for i, c in enumerate(doc_cols or [])}
            for r in doc_rows:
                if not isinstance(r, (list, tuple)):
                    continue
                
                doc_id = r[col_idx.get("id")]
                storage_path = r[col_idx.get("storage_path")]
                mimetype = r[col_idx.get("mime_type")]
                # ext dari storage_path
                ext = os.path.splitext(storage_path or "")[1].lstrip(".")
                # base url + storage endpoint
                base_url = request.host_url.rstrip('/').replace('http://', 'https://')
                document_url = f"{base_url}/storage/{doc_id}"
                documents[storage_path] = {
                    "mimetype": mimetype,
                    "ext": ext,
                    "url": document_url
                }
    except Exception as e:
        logging.warning(f"Gagal mengambil dokumen untuk chat {chat_id}: {e}")

    # Schema baru: ambil detail dari chat_details berdasarkan chat_id (chat_id)
    query = "SELECT * FROM chat_details WHERE chat_id = %s ORDER BY created_at;"
    rows, columns = safe_db_query(query, [chat_id])
    # Defensive: ensure rows is a list of tuples
    if not isinstance(rows, list):
        rows = []
    data = []
    check_val = []
    for row in rows:
        if isinstance(row, (list, tuple)) and columns:
            item = dict(zip(columns, row))
            # Normalisasi kolom attachments bila ada dan mapping ke documents
            try:
                import json
                attachments_val = item.get('attachments') # This is already a string from the DB
                processed_attachments = []
                if attachments_val:
                    # Pastikan berbentuk list dengan json.loads jika string JSON
                    attachments_list = json.loads(attachments_val) if isinstance(attachments_val, str) else attachments_val
                    check_val.append(attachments_list)
                    # Loop dan cocokkan dengan key pada documents (stored_filename)
                    for p in attachments_list:
                        if not isinstance(p, str):
                            continue
                        # Ambil filename dari path
                        doc_info = documents.get(p)
                        if doc_info:
                            processed_attachments.append({
                                'mimetype': doc_info.get('mimetype'),
                                'ext': doc_info.get('ext'),
                                'url': doc_info.get('url')
                            })

                # Replace kolom attachment dengan hasil terproses bila ada
                item['attachments'] = processed_attachments
            except Exception as e:
                logging.warning(f"Error processing attachments for chat_detail {item.get('id')}: {e}")
                pass

            data.append(item)

    # Process source_documents to match ask endpoint format
    for index, item in enumerate(data):
        # set options to data array - safely convert to boolean
        is_browse_value = options.get("is_browse", False)
        is_company_value = options.get("is_company", False)
        is_general_value = options.get("is_general", False)
        
        data[index]["is_browse"] = to_bool(is_browse_value) if isinstance(is_browse_value, str) else bool(is_browse_value)
        data[index]["is_company"] = to_bool(is_company_value) if isinstance(is_company_value, str) else bool(is_company_value)
        data[index]["is_general"] = to_bool(is_general_value) if isinstance(is_general_value, str) else bool(is_general_value)

        source_documents = item.get('source_documents')
        processed_source_docs = []
        
        if source_documents:
            import json
            try:
                docs = json.loads(source_documents) if isinstance(source_documents, str) else source_documents
                if isinstance(docs, list):
                    for doc in docs:
                        if isinstance(doc, dict):
                            # Extract metadata first for title priority
                            metadata = doc.get("metadata", {})
                            
                            # Extract title with proper priority: metadata.Title > doc.title > fallback
                            title = (metadata.get("Title") or 
                                   metadata.get("title") or 
                                   doc.get("title") or 
                                   "Document Source")
                            
                            # Extract URL from the stored document format
                            url = doc.get("url", "")
                            
                            # If no URL or it's not a web source, try to build document download link
                            if not url or not url.startswith('http'):
                                # Check if it has document_id in metadata
                                document_id = metadata.get("document_id", "")
                                
                                if document_id:
                                    # Build download link using our public endpoint
                                    base_url = request.host_url.rstrip('/').replace('http://', 'https://')
                                    url = f"{base_url}/storage/{document_id}"
                                elif not url:
                                    # Skip documents without valid URLs
                                    continue
                            
                            # Create document entry matching ask endpoint format
                            processed_doc = {
                                "title": title,
                                "url": url
                            }
                            processed_source_docs.append(processed_doc)
                            
            except (json.JSONDecodeError, TypeError) as e:
                logging.warning(f"Error processing source documents for session {chat_id}: {e}")
                # If parsing fails, set empty list
                pass

        # Update the source_documents field with processed data
        item['source_documents'] = processed_source_docs

    return jsonify({"message": "Berhasil mengambil riwayat percakapan", "data": data}), 200

# --- DELETE CHAT (by chat_id) ---
@chat_bp.route('/chats/<chat_id>', methods=['DELETE'])
@swag_from(yaml_path("chats_delete_single.yml"))
@require_auth
def chats_delete_single(chat_id, **kwargs):
    """
    Endpoint to delete a single chat session by session ID.
    It permanently removes all chat records for the specified session from the database.
    """
    user = kwargs['user']
    if not chat_id:
        return jsonify({"message": "Session ID tidak ditemukan pada URL"}), 400
    try:
        uuid.UUID(chat_id)
    except Exception:
        return jsonify({"message": "Session ID harus berupa UUID yang valid"}), 400

    # Hapus chat akan cascade menghapus chat_details (FK ON DELETE CASCADE)
    query = "DELETE FROM chats WHERE id = %s AND user_id = %s;"
    affected_rows, _ = safe_db_query(query, [chat_id, user["user_id"]])
    remove_folder_chat(f"data/documents/chats/{chat_id}")
    return jsonify({"message": "Berhasil menghapus riwayat chat"}), 200

# --- DELETE MULTIPLE CHAT (by chat_id) ---
@chat_bp.route('/chats/bulk-delete', methods=['POST'])
@swag_from(yaml_path("chats_delete_multi.yml"))
@require_auth
def chats_delete_multi(**kwargs):
    """
    Endpoint to delete multiple chat sessions based on session IDs provided in the request body.
    It permanently removes all chat records for the specified sessions from the database.
    """
    user = kwargs['user']
    data = request.get_json()
    chat_ids = data.get("chat_ids", [])
    if not isinstance(chat_ids, list) or not chat_ids:
        return jsonify({"message": "chat_ids harus berupa list dan tidak boleh kosong"}), 400
    for sid in chat_ids:
        try:
            uuid.UUID(sid)
        except Exception:
            return jsonify({"message": f"Session ID tidak valid: {sid}"}), 400

    query = "DELETE FROM chats WHERE id IN %s AND user_id = %s;"
    affected_rows, _ = safe_db_query(query, (tuple(chat_ids), user["user_id"]))
    for sid in chat_ids:
        remove_folder_chat(f"data/documents/chats/{sid}")
    return jsonify({"message": f"Berhasil menghapus {len(chat_ids)} sesi chat"}), 200

# --- DELETE ALL CHAT ---
@chat_bp.route('/chats', methods=['DELETE'])
@swag_from(yaml_path("chats_delete_all.yml"))
@require_auth
def chats_delete_all(**kwargs):
    """
    Endpoint to clear all chat history for the authenticated user.
    It permanently removes all chat records for the user from the database.
    """
    user = kwargs['user']
    query = "DELETE FROM chats WHERE user_id = %s;"
    affected_rows, _ = safe_db_query(query, [user["user_id"]])
    return jsonify({"message": f"Berhasil menghapus semua sesi chat ({affected_rows} sesi)"}), 200

# --- GET CHAT LIMITS INFO ---
@chat_bp.route('/chats/limits', methods=['GET'])
@swag_from(yaml_path("chats_limits.yml"))
@require_auth
def chat_limits(**kwargs):
    """
    Endpoint to get chat limits information for the authenticated user.
    Returns information about max_chat_topic and max_chats limits.
    """
    user = kwargs['user']
    
    limits_info = get_chat_limits_info(user_data=user)
    
    return jsonify({
        "message": "Berhasil mengambil informasi batasan chat",
        "data": limits_info
    }), 200
