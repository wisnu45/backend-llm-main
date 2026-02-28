from flask import Blueprint, jsonify, request
from app.utils.auth import require_auth
from app.utils.document import process_document_for_vector_storage, data_path
from app.utils.database import safe_db_query
import os
import mimetypes
import logging

tools_bp = Blueprint("tools", __name__)

@tools_bp.route("/tools/cleanup", methods=["POST", "GET"])
@require_auth
def cleanup_documents(**kwargs):
    """Remove orphan files under portal/website that are not present in DB.
    Returns a summary dict.
    """
    summary = {"checked": 0, "deleted": 0, "kept": 0, "errors": []}

    try:
        rows, _ = safe_db_query(
            "SELECT stored_filename, storage_path, source_type FROM documents WHERE source_type IN ('portal','website')"
        )
        valid = set()
        for r in rows or []:
            stored = r[0]
            storage_path = r[1] if len(r) > 1 else None
            src = r[2] if len(r) > 2 else None
            if stored:
                valid.add((src or '', stored))
                if storage_path and os.path.isfile(storage_path):
                    valid.add((src or '', os.path.basename(storage_path)))

        targets = [("portal", data_path("documents", "portal")), ("website", data_path("documents", "website"))]
        for src, folder in targets:
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if not os.path.isfile(path) or name.startswith('.'):
                    continue
                summary["checked"] += 1
                if (src, name) in valid:
                    summary["kept"] += 1
                    continue
                try:
                    os.remove(path)
                    summary["deleted"] += 1
                    logging.info(f"🧹 Deleted orphan document file: {path}")
                except Exception as err:
                    msg = f"Failed to delete {path}: {err}"
                    logging.warning(msg)
                    summary["errors"].append(msg)
    except Exception as e:
        msg = f"Cleanup failed: {e}"
        logging.error(msg)
        summary["errors"].append(msg)

    logging.info(
        f"🧾 Cleanup summary — checked: {summary['checked']}, kept: {summary['kept']}, deleted: {summary['deleted']}, errors: {len(summary['errors'])}"
    )
    return jsonify({"message": "Cleanup completed", "summary": summary})


@tools_bp.route("/tools/embed-repair", methods=["POST"]) 
@require_auth
def embed_repair(**kwargs):
    """Diagnose and repair portal/website embeddings between DB and filesystem.
    - If file missing but DB row exists -> re-embed if file can be found via storage_path.
    - If file exists but no DB row -> create minimal DB row then embed.
    Optional body: { "dry_run": true }
    """
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run", False))

    summary = {
        "checked_db": 0,
        "checked_fs": 0,
        "reembedded_db_missing_file": 0,
        "reembedded_fs_missing_db": 0,
        "created_db_records": 0,
        "errors": []
    }

    try:
        # 1) Load DB records for portal/website
        rows, cols = safe_db_query(
            """
            SELECT id, source_type, original_filename, stored_filename, storage_path, mime_type, size_bytes, uploaded_by
            FROM documents
            WHERE source_type IN ('portal','website')
            """
        )
        by_key = {}
        for r in rows or []:
            doc = dict(zip(cols, r))
            key = (doc.get("source_type"), doc.get("stored_filename"))
            by_key[key] = doc

        # 2) Scan filesystem
        folders = {
            "portal": data_path("documents", "portal"),
            "website": data_path("documents", "website"),
        }

        # A) Handle DB rows with missing files
        for key, doc in by_key.items():
            src, stored = key
            folder = folders.get(src or "")
            if not folder:
                continue
            expected_path = os.path.join(folder, stored) if stored else None
            file_path = None
            if expected_path and os.path.isfile(expected_path):
                # File actually exists; nothing to fix
                continue
            # Try storage_path as fallback
            storage_path = doc.get("storage_path")
            if storage_path and os.path.isfile(storage_path):
                file_path = storage_path
            elif expected_path:
                file_path = expected_path  # might not exist; checked below

            summary["checked_db"] += 1
            if file_path and os.path.isfile(file_path):
                if dry_run:
                    logging.info(f"[dry-run] Re-embed DB-missing-file {src}:{stored} from {file_path}")
                    summary["reembedded_db_missing_file"] += 1
                    continue
                ok = process_document_for_vector_storage(
                    file_path=file_path,
                    document_name=doc.get("original_filename") or stored,
                    document_source=stored,
                    metadata={
                        "mime_type": doc.get("mime_type"),
                        "source_type": src,
                        "uploaded_by": doc.get("uploaded_by"),
                    },
                    document_id=doc.get("id"),
                    storage_path=doc.get("storage_path"),
                )
                if ok:
                    summary["reembedded_db_missing_file"] += 1
                else:
                    summary["errors"].append(f"Re-embed failed for {src}:{stored}")
            else:
                summary["errors"].append(f"File not found for {src}:{stored}")

        # B) Handle files with no DB rows
        for src, folder in folders.items():
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                path = os.path.join(folder, name)
                if not os.path.isfile(path) or name.startswith('.'):
                    continue
                summary["checked_fs"] += 1
                key = (src, name)
                if key in by_key:
                    continue

                # Need to create DB row then embed
                # Minimal fields
                mime, _ = mimetypes.guess_type(name)
                size_bytes = os.path.getsize(path)
                if dry_run:
                    logging.info(f"[dry-run] Create DB + re-embed FS-missing-DB {src}:{name}")
                    summary["reembedded_fs_missing_db"] += 1
                    summary["created_db_records"] += 1
                    continue

                try:
                    insert_q = """
                        INSERT INTO documents (source_type, original_filename, stored_filename, storage_path, mime_type, size_bytes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """
                    original_filename = name
                    storage_path_rel = os.path.relpath(path, '.')
                    rows_ins, cols_ins = safe_db_query(
                        insert_q,
                        (src, original_filename, name, storage_path_rel, mime or 'application/octet-stream', size_bytes)
                    )
                    new_id = rows_ins[0][0] if isinstance(rows_ins, list) and rows_ins else None
                    if new_id:
                        summary["created_db_records"] += 1
                        by_key[key] = {
                            "id": new_id,
                            "source_type": src,
                            "original_filename": original_filename,
                            "stored_filename": name,
                            "storage_path": storage_path_rel,
                            "mime_type": mime,
                            "size_bytes": size_bytes,
                        }
                except Exception as ins_err:
                    summary["errors"].append(f"Insert DB failed for {src}:{name}: {ins_err}")
                    continue

                ok = process_document_for_vector_storage(
                    file_path=path,
                    document_name=original_filename,
                    document_source=name,
                    metadata={"mime_type": mime, "source_type": src},
                    document_id=new_id,
                    storage_path=storage_path_rel,
                )
                if ok:
                    summary["reembedded_fs_missing_db"] += 1
                else:
                    summary["errors"].append(f"Re-embed failed for {src}:{name}")

        logging.info(
            f"Embed-repair: checked_db={summary['checked_db']} checked_fs={summary['checked_fs']} re_db_missing_file={summary['reembedded_db_missing_file']} re_fs_missing_db={summary['reembedded_fs_missing_db']} created={summary['created_db_records']} errors={len(summary['errors'])}"
        )
    except Exception as e:
        logging.exception("Embed-repair failed")
        summary["errors"].append(str(e))

    return jsonify({"message": "Embed repair completed", "summary": summary, "dry_run": dry_run})
