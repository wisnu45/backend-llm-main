from app.utils.database import safe_db_query

import logging
import json

class ErrorHandler:
    _cache = {}  # optional cache biar gak query DB terus

    # Define default response error 
    offline="Maaf, Vita sedang offline"
    process="Saya mengalami error saat memproses pertanyaan Anda."
    token_empty="Maaf Vita perlu recharge. Silahkan hubungi Vita kembali nanti."
    ambiguous="Boleh jelaskan lebih spesifik maksudnya agar Vita bisa bantu lebih tepat?"
    insufficient_info="Saya tidak memiliki informasi yang cukup untuk menjawab pertanyaan tersebut."
    offline_website="Maaf, Vita tidak dapat mencari informasi dari website saat ini. Silakan coba lagi nanti atau gunakan pencarian dokumen internal."
    offline_internet="Maaf, sistem pencarian Vita sedang tidak tersedia. Silakan coba lagi nanti."
    no_information="Maaf, saya tidak menemukan informasi yang relevan untuk pertanyaan Anda. Silakan coba dengan pertanyaan yang berbeda atau lebih spesifik."
    
    @classmethod
    def get_all_message(cls):
        """
        Get all error messages from database settings or fallback to class defaults.
        
        Returns:
            Dictionary of error messages keyed by error code
        """
        keys = [
            "offline",
            "process",
            "token_empty",
            "ambiguous",
            "insufficient_info",
            "offline_internet",
            "offline_website",
            "no_information"
        ]

        try:
            query = "SELECT name, value FROM settings WHERE name = ANY(%s)"
            params = []
            for key in keys:
                params.append("message_" + key)

            results, _ = safe_db_query(query, (params,))
            tmp = {}
            value = {}

            for u in results:
               tmp[u[0][8:]] = u[1]

            for key in keys:
                if tmp.get(key) is not None:
                    value[key] = tmp[key]
                elif getattr(cls, key, None) is not None:
                    value[key] = getattr(cls, key)
                else:
                    value[key] = "Terjadi kesalahan"

            return value
        except Exception as e:
            logging.error(f"ErrorHandler DB error: {e}")
            # Return class defaults if database query fails
            return {key: getattr(cls, key, "Terjadi kesalahan") for key in keys}

    @classmethod
    def get_message(cls, code: str, default: str = "Terjadi kesalahan"):
        """
        Get error message from database settings or fallback to class default or provided default.
        
        Args:
            code: Error code (e.g., "token_empty", "offline", "process")
            default: Fallback message if database query fails
            
        Returns:
            Error message string from database or fallback
        """
        keys = [
            "offline",
            "process",
            "token_empty",
            "ambiguous",
            "insufficient_info",
            "offline_internet",
            "offline_website",
            "no_information"
        ]

        try:
            query = "SELECT name, value FROM settings WHERE name = ANY(%s)"
            params = []
            for key in keys:
                params.append("message_" + key)

            results, _ = safe_db_query(query, (params,))
            tmp = {}
            value = {}

            for u in results:
               tmp[u[0][8:]] = u[1]

            for key in keys:
                if tmp.get(key) is not None:
                    value[key] = tmp[key]
                elif getattr(cls, key, None) is not None:
                    value[key] = getattr(cls, key)
                else :
                    value[key] = default

            return value.get(code) if value.get(code) else default
        except Exception as e:
            logging.error(f"ErrorHandler DB error: {e}")
            # Return class default if available, otherwise use provided default
            class_default = getattr(cls, code, None)
            return class_default if class_default else default