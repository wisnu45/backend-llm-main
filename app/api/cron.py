import os
import sys

# Ensure the project root (which contains the `app` package) is importable when the
# script is executed directly, e.g., `python app/api/cron.py`.

# Ensure project root is in Python path for proper module imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load portal pull logic
from app.utils.database import safe_db_query

import shutil
import logging
import uuid

def configure_logging() -> None:
    """Configure logging outputs for cron job."""
    if getattr(configure_logging, "_configured", False):
        return

    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(os.path.join(log_dir, 'cron.log'))
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s | (%(name)s) | [%(levelname)s] | %(message)s'))
    root_logger.addHandler(file_handler)

    configure_logging._configured = True

configure_logging()

def chats_delete_expired():
    """
    Endpoint triggered by cron job to automatically delete expired chat sessions.  
    It removes chat records that have passed their expiration date, 
    determined by role-specific settings or the default expiration policy.
    """

    default = 30
    setting_name = "chat_topic_expired_days"

    logging.info(
        "Memulai cron penghapusan chat kadaluarsa"
    )

    # Ambil data all chat expired
    # Filter Pinned dan Expired days berdasarkan urutan settings_roles.value, settings.value, 30 (default)
    query_chat = """
        SELECT c.id AS chat_id
        FROM chats c
        JOIN users u ON u.id = c.user_id
        LEFT JOIN LATERAL (
            SELECT MAX(cd.created_at) AS last_chat_at
            FROM chat_details cd
            WHERE cd.chat_id = c.id
        ) last_cd ON TRUE
        LEFT JOIN (
            SELECT rs.roles_id, CAST(rs.value AS INTEGER) AS expire_days
            FROM roles_settings rs
            JOIN settings s ON s.id = rs.settings_id
            WHERE s.name = %s
        ) rs ON rs.roles_id = u.roles_id
        LEFT JOIN (
            SELECT CAST(s.value AS INTEGER) AS expire_days
            FROM settings s
            WHERE s.name = %s
            LIMIT 1
        ) s_default ON TRUE
        WHERE c.pinned = false
        AND COALESCE(last_cd.last_chat_at, c.created_at) <= CURRENT_TIMESTAMP - (COALESCE(rs.expire_days, s_default.expire_days, %s) * INTERVAL '1 day')
    """

    # Mengambil data chat yang sudah expired
    deleted_chat = []
    try:
        chats, _ = safe_db_query(query_chat, [setting_name, setting_name, default])
        if chats is None:
            logging.warning("Hasil query chat kadaluarsa kosong/null")
            chats = []

        if chats and isinstance(chats, list) and len(chats) > 0:
            for chat in chats:
                chats_id = chat[0]
                deleted_chat.append(chats_id)
            logging.info("Total chat kadaluarsa yang siap dihapus: %s", len(deleted_chat))
        else:
            logging.info("Tidak ditemukan chat kadaluarsa yang perlu dihapus")

    except Exception as e:
        logging.error("Gagal memproses request", exc_info=True)

    # Cek dulu jika jumlah chat yang akan di delete ada
    if(len(deleted_chat) > 0) :
        try: 
            query = "DELETE FROM chats WHERE id = ANY(%s::uuid[]) AND pinned = false"
            params = (list(deleted_chat),)

            delete_result, _ = safe_db_query(query, params)
            logging.info(
                "Berhasil menjalankan penghapusan database untuk %s chat kadaluarsa",
                len(deleted_chat),
            )
            logging.debug("Response penghapusan database: %s", delete_result)
        except Exception as e:
            logging.error("Gagal menghapus chat kadaluarsa dari database", exc_info=True)
            sys.exit(1)
        
        # Hapus Folder Chat berdasarkan Chat ID
        for chat_id in deleted_chat:
            logging.debug("Menghapus folder chat untuk ID %s", chat_id)
            remove_folder(f"data/documents/chats/{chat_id}")

        logging.info(
            "Cron selesai: %s chat kadaluarsa dihapus beserta folder pendukungnya",
            len(deleted_chat),
        )
    else : 
        logging.info(
            "Cron selesai: tidak ada chat kadaluarsa yang dihapus karena daftar kosong"
        )

def remove_folder(path):
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
            shutil.rmtree(normalized_path)  # hapus folder + semua isinya
            logging.info("Folder chat %s berhasil dihapus", normalized_path)
        else:
            logging.debug("Folder chat %s tidak ditemukan saat penghapusan", normalized_path)
    except Exception as e:
        logging.error("Terjadi kesalahan saat menghapus folder %s", path, exc_info=True)


chats_delete_expired()
