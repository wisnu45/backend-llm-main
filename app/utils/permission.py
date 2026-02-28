"""
Permission Helper Module

Modul ini menyediakan fungsi helper untuk mengecek permission secara dinamis
berdasarkan konfigurasi general dan feature settings.

Prioritas:
1. Feature setting (dari roles_settings) - prioritas tinggi
2. General setting (dari settings table) - prioritas rendah

Cara kerja:
- Auto-detect user context dari Flask request (JWT token)
- Jika ada setting di roles_settings untuk role tertentu, gunakan nilai tersebut
- Jika tidak ada di roles_settings, gunakan nilai default dari settings table
- Jika tidak ada keduanya, return None
"""

import logging
from typing import Union, Optional, Any
from flask import request, g, has_request_context
import jwt
import os
from app.utils.database import safe_db_query

def _get_current_user() -> Optional[dict]:
    """
    Auto-detect user dari Flask request context (JWT token)
    
    Returns:
        Optional[dict]: User data atau None jika tidak ada user
    """
    try:
        # Cek apakah kita dalam Flask request context
        if not has_request_context():
            return None
            
        # Cek apakah user sudah ada di Flask g object (dari middleware/decorator)
        if hasattr(g, 'user') and g.user:
            return g.user
            
        # Ambil token dari Authorization header
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return None
            
        token_value = token.split(" ", 1)[1]
        
        # Decode JWT token
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            return None
            
        payload = jwt.decode(token_value, secret_key, algorithms=["HS256"])
        
        # Pastikan ini access token
        if payload.get("type") != "access":
            return None
            
        # Ambil user dari database
        user_id = payload.get("user_id")
        if not user_id:
            return None
            
        query = """
            SELECT
                u.id,
                u.roles_id,
                u.name,
                u.username,
                u.is_portal,
                r.name as role_name
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.id = %s
        """
        
        results, _ = safe_db_query(query, [user_id])
        if results and len(results) > 0:
            row = results[0]
            user_data = {
                "user_id": str(row[0]),
                "roles_id": row[1],
                "name": row[2],
                "username": row[3],
                "is_portal": row[4],
                "role_name": row[5]
            }
            
            # Cache di Flask g untuk request ini
            g.user = user_data
            return user_data
            
        return None
        
    except Exception as e:
        logging.debug(f"Error getting current user: {e}")
        return None

def check_permission(setting_name: str, user_data: dict = None, role_id: str = None) -> Optional[Any]:
    """
    Helper untuk mengecek permission secara dinamis
    
    Args:
        setting_name (str): Nama setting yang ingin dicek
        user_data (dict, optional): Data user manual (opsional, auto-detect jika kosong)
        role_id (str, optional): Role ID manual (opsional, auto-detect jika kosong)
        
    Returns:
        Any: Nilai setting berdasarkan prioritas (feature > general), atau None jika tidak ditemukan
        
    Examples:
        # Auto-detect dari JWT token (recommended)
        result = check_permission("attachment")
        
        # Manual user data (jika diperlukan)
        user = {"roles_id": "uuid-role", "name": "John"}
        result = check_permission("attachment", user_data=user)
        
        # Manual role_id
        result = check_permission("attachment", role_id="uuid-role")
        
        # Untuk general setting tanpa user context
        result = check_permission("chat_max_text")
    """
    
    if not setting_name:
        logging.error("setting_name is required")
        return None
    
    # Auto-detect user jika tidak diberikan manual
    if not user_data and not role_id:
        user_data = _get_current_user()
    
    # Ambil role_id dari user_data jika tidak diberikan langsung
    if not role_id and user_data:
        role_id = user_data.get('role_id', user_data.get('roles_id', None))
    
    try:
        # Prioritas 1: Cek feature setting dari roles_settings (jika ada role_id)
        if role_id:
            feature_value = _get_role_setting_value(role_id, setting_name)
            if feature_value is not None:
                return _parse_setting_value(feature_value)
        
        # Prioritas 2: Cek general setting dari settings table
        general_value = _get_general_setting_value(setting_name)
        if general_value is not None:
            return _parse_setting_value(general_value)
            
        # Tidak ditemukan di manapun
        logging.warning(f"Setting '{setting_name}' not found in any configuration")
        return None
        
    except Exception as e:
        logging.error(f"Error checking permission for setting '{setting_name}': {e}")
        return None

def _get_role_setting_value(role_id: str, setting_name: str) -> Optional[str]:
    """
    Ambil nilai setting dari roles_settings untuk role tertentu
    
    Args:
        role_id (str): ID role
        setting_name (str): Nama setting
        
    Returns:
        Optional[str]: Nilai setting atau None jika tidak ditemukan
    """
    query = """
        SELECT rs.value 
        FROM roles_settings rs
        JOIN settings s ON rs.settings_id = s.id
        WHERE rs.roles_id = %s AND s.name = %s
        LIMIT 1
    """
    
    try:
        results, columns = safe_db_query(query, (role_id, setting_name))
        if results and len(results) > 0:
            return results[0][0]  # Return value column
        return None
    except Exception as e:
        logging.error(f"Error getting role setting value: {e}")
        return None

def _get_general_setting_value(setting_name: str) -> Optional[str]:
    """
    Ambil nilai setting dari settings table (general configuration)
    
    Args:
        setting_name (str): Nama setting
        
    Returns:
        Optional[str]: Nilai setting atau None jika tidak ditemukan
    """
    query = """
        SELECT value 
        FROM settings 
        WHERE name = %s
        LIMIT 1
    """
    
    try:
        results, columns = safe_db_query(query, (setting_name,))
        if results and len(results) > 0:
            return results[0][0]  # Return value column
        return None
    except Exception as e:
        logging.error(f"Error getting general setting value: {e}")
        return None

def _parse_setting_value(value: str) -> Any:
    """
    Parse nilai setting sesuai dengan tipe datanya
    
    Args:
        value (str): String value dari database
        
    Returns:
        Any: Parsed value sesuai tipe (boolean, int, list, atau string)
    """
    if not value:
        return value
        
    # Handle boolean values
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    
    # Handle integer values
    if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
        return int(value)
    
    # Handle array/list values (JSON format)
    if value.startswith('[') and value.endswith(']'):
        try:
            import json
            return json.loads(value)
        except json.JSONDecodeError:
            logging.warning(f"Failed to parse JSON array: {value}")
            return value
    
    # Return as string for other cases
    return value

def get_user_permissions(user_data: dict = None, role_id: str = None) -> dict:
    """
    Ambil semua permissions untuk user/role tertentu
    
    Args:
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        dict: Dictionary berisi semua setting dan nilainya untuk user/role tersebut
    """
    
    # Auto-detect user jika tidak diberikan
    if not user_data and not role_id:
        user_data = _get_current_user()
    
    if not role_id and user_data:
        role_id = user_data.get('roles_id')
    
    permissions = {}
    
    try:
        # Ambil semua settings yang tersedia
        all_settings_query = "SELECT name FROM settings"
        results, columns = safe_db_query(all_settings_query)
        
        # Loop untuk setiap setting dan cek nilainya
        for row in results:
            setting_name = row[0]
            permissions[setting_name] = check_permission(
                setting_name=setting_name,
                user_data=user_data, 
                role_id=role_id
            )
            
    except Exception as e:
        logging.error(f"Error getting user permissions: {e}")
        
    return permissions

def check_menu_access(menu_name: str, user_data: dict = None, role_id: str = None) -> bool:
    """
    Helper khusus untuk mengecek akses menu
    
    Args:
        menu_name (str): Nama menu (chat, user, document, setting)
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        bool: True jika user memiliki akses, False jika tidak
    """
    if not menu_name:
        return False
        
    # Format nama setting untuk menu
    setting_name = f"menu_{menu_name}"
    
    result = check_permission(setting_name=setting_name, user_data=user_data, role_id=role_id)
    
    # Default False jika tidak ditemukan setting
    return bool(result) if result is not None else False

def check_feature_access(feature_name: str, user_data: dict = None, role_id: str = None) -> bool:
    """
    Helper khusus untuk mengecek akses feature
    
    Args:
        feature_name (str): Nama feature (attachment, max_chat_topic, dll)
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        bool: True jika feature aktif, False jika tidak
    """
    if not feature_name:
        return False
        
    result = check_permission(setting_name=feature_name, user_data=user_data, role_id=role_id)
    
    # Default False jika tidak ditemukan setting
    return bool(result) if result is not None else False

def get_setting_value(setting_name: str, default_value: Any = None, user_data: dict = None, role_id: str = None) -> Any:
    """
    Helper untuk ambil nilai setting dengan default value
    
    Args:
        setting_name (str): Nama setting
        default_value (Any): Nilai default jika setting tidak ditemukan
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        Any: Nilai setting atau default_value jika tidak ditemukan
    """
    result = check_permission(setting_name=setting_name, user_data=user_data, role_id=role_id)
    return result if result is not None else default_value

# Shortcut functions untuk kemudahan penggunaan
def has_permission(setting_name: str) -> bool:
    """Shortcut untuk check permission sebagai boolean"""
    return bool(check_permission(setting_name))

def can_access_menu(menu_name: str) -> bool:
    """Shortcut untuk check menu access"""
    return check_menu_access(menu_name)

def is_feature_enabled(feature_name: str) -> bool:
    """Shortcut untuk check feature access"""
    return check_feature_access(feature_name)

def get_setting(setting_name: str, default=None) -> Any:
    """Shortcut untuk get setting value"""
    return get_setting_value(setting_name, default)

# Helper functions untuk batasan chat
def check_chat_limits(user_data: dict = None, role_id: str = None, chat_id: str = None) -> dict:
    """
    Helper untuk mengecek batasan chat berdasarkan konfigurasi max_chats dan max_chat_topic
    
    Args:
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        chat_id (str, optional): ID chat session untuk cek max_chats dalam sesi tertentu
        
    Returns:
        dict: Status batasan chat dengan informasi detail
        {
            "can_create_topic": bool,
            "can_ask_question": bool,
            "current_topics": int,
            "max_topics": int,
            "current_chats_in_session": int,
            "max_chats": int,
            "limits_info": {
                "max_chat_topic_enabled": bool,
                "max_chats_enabled": bool
            }
        }
    """
    
    # Auto-detect user jika tidak diberikan
    if not user_data and not role_id:
        user_data = _get_current_user()
    
    if not role_id and user_data:
        role_id = user_data.get('roles_id')
        
    user_id = user_data.get('user_id') if user_data else None
    
    result = {
        "can_create_topic": True,
        "can_ask_question": True,
        "current_topics": 0,
        "max_topics": 0,
        "current_chats_in_session": 0,
        "max_chats": 0,
        "limits_info": {
            "max_chat_topic_enabled": False,
            "max_chats_enabled": False
        }
    }
    
    try:
        # Ambil konfigurasi max_chat_topic
        max_topics_config = check_permission("max_chat_topic", user_data=user_data, role_id=role_id)
        if max_topics_config is not None and isinstance(max_topics_config, int):
            result["max_topics"] = max_topics_config
            result["limits_info"]["max_chat_topic_enabled"] = True
            
            # Hitung jumlah topic/sesi yang sudah ada untuk user
            if user_id:
                topic_query = "SELECT COUNT(*) FROM chats WHERE user_id = %s"
                topic_results, _ = safe_db_query(topic_query, [user_id])
                if topic_results and len(topic_results) > 0:
                    result["current_topics"] = topic_results[0][0]
                    
                # Cek apakah user masih bisa membuat topic baru
                result["can_create_topic"] = result["current_topics"] < result["max_topics"]
        
        # Ambil konfigurasi max_chats
        max_chats_config = check_permission("max_chats", user_data=user_data, role_id=role_id)
        if max_chats_config is not None and isinstance(max_chats_config, int):
            result["max_chats"] = max_chats_config
            result["limits_info"]["max_chats_enabled"] = True
            
            # Hitung jumlah chat dalam sesi tertentu jika chat_id diberikan
            if user_id and chat_id:
                chat_query = "SELECT COUNT(*) FROM chat_details WHERE chat_id = %s"
                chat_results, _ = safe_db_query(chat_query, [chat_id])
                if chat_results and len(chat_results) > 0:
                    result["current_chats_in_session"] = chat_results[0][0]
                    
                # Cek apakah user masih bisa bertanya dalam sesi ini
                result["can_ask_question"] = result["current_chats_in_session"] < result["max_chats"]
        
        return result
        
    except Exception as e:
        logging.error(f"Error checking chat limits: {e}")
        return result

def can_create_chat_topic(user_data: dict = None, role_id: str = None) -> bool:
    """
    Helper untuk mengecek apakah user bisa membuat topic/sesi chat baru
    
    Args:
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        bool: True jika bisa membuat topic baru, False jika sudah mencapai limit
    """
    limits = check_chat_limits(user_data=user_data, role_id=role_id)
    return limits["can_create_topic"]

def can_ask_question_in_session(chat_id: str, user_data: dict = None, role_id: str = None) -> bool:
    """
    Helper untuk mengecek apakah user bisa bertanya dalam sesi chat tertentu
    
    Args:
        chat_id (str): ID chat session
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        bool: True jika bisa bertanya, False jika sudah mencapai limit
    """
    limits = check_chat_limits(user_data=user_data, role_id=role_id, chat_id=chat_id)
    return limits["can_ask_question"]

def get_chat_limits_info(user_data: dict = None, role_id: str = None) -> dict:
    """
    Helper untuk mendapatkan informasi lengkap tentang batasan chat user
    
    Args:
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        dict: Informasi lengkap batasan chat
    """
    return check_chat_limits(user_data=user_data, role_id=role_id)

def validate_chat_request(chat_id: str = None, is_new_topic: bool = False, user_data: dict = None, role_id: str = None) -> dict:
    """
    Helper untuk memvalidasi request chat dengan mengecek semua batasan
    
    Args:
        chat_id (str, optional): ID chat session untuk pertanyaan dalam sesi yang ada
        is_new_topic (bool): True jika ingin membuat topic/sesi baru
        user_data (dict, optional): Data user manual (auto-detect jika kosong)
        role_id (str, optional): Role ID manual (auto-detect jika kosong)
        
    Returns:
        dict: Status validasi dan informasi error jika ada
        {
            "valid": bool,
            "can_proceed": bool,
            "error_message": str,
            "error_code": str,
            "limits": dict
        }
    """
    
    result = {
        "valid": True,
        "can_proceed": True,
        "error_message": None,
        "error_code": None,
        "limits": {}
    }
    
    try:
        limits = check_chat_limits(user_data=user_data, role_id=role_id, chat_id=chat_id)
        result["limits"] = limits
        
        # Validasi untuk topic baru
        if is_new_topic:
            if limits["limits_info"]["max_chat_topic_enabled"] and not limits["can_create_topic"]:
                result["valid"] = False
                result["can_proceed"] = False
                result["error_code"] = "MAX_TOPIC_EXCEEDED"
                result["error_message"] = f"Anda telah mencapai batas maksimum {limits['max_topics']} topic chat. Silakan hapus beberapa topic lama untuk membuat yang baru."
                return result
        
        # Validasi untuk pertanyaan dalam sesi
        if chat_id:
            if limits["limits_info"]["max_chats_enabled"] and not limits["can_ask_question"]:
                result["valid"] = False
                result["can_proceed"] = False
                result["error_code"] = "MAX_CHATS_EXCEEDED"
                result["error_message"] = f"Anda telah mencapai batas maksimum {limits['max_chats']} pertanyaan dalam sesi ini. Silakan buat sesi chat baru."
                return result
        
        return result
        
    except Exception as e:
        logging.error(f"Error validating chat request: {e}")
        result["valid"] = False
        result["can_proceed"] = False
        result["error_code"] = "VALIDATION_ERROR"
        result["error_message"] = "Terjadi kesalahan saat memvalidasi request chat"
        return result
