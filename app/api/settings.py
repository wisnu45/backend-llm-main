from flask import Blueprint, request, jsonify
from flasgger import swag_from
from werkzeug.security import generate_password_hash

from app.utils.database import safe_db_query
from app.utils.general import yaml_path
from app.utils.auth import require_auth, require_access, passwd_hash, encrypt_aes
from app.utils.portal import create_user_token
from app.utils.time_provider import get_current_datetime

from app.utils.text import to_snake_case, to_normal_text
from app.utils.validation import valid_setting_datatype, valid_setting_value, is_openai_api_key
from app.utils.setting import resolve_api_key_value, mask_api_key

import logging
import requests
import re
import json

settings_bp = Blueprint("settings", __name__)


def _is_special_sync_admin(user: dict) -> bool:
    """Allowed operator for document sync configuration."""
    if not user:
        return False
    return (
        user.get("username") == "subhan.pradana"
        and bool(user.get("is_portal"))
    )


def _ensure_setting_edit_permission(setting_name: str, user: dict):
    """
    Enforce business rules for critical settings.

    Raises:
        PermissionError: when the current user cannot modify the setting.
    """
    normalized = to_snake_case(setting_name or "")

    if normalized == "document_sync_allowed_users":
        if not _is_special_sync_admin(user):
            raise PermissionError(
                "Hanya user subhan.pradana (portal) yang dapat mengubah pengaturan ini"
            )

    if normalized == "default_assistant_with_help":
        raise PermissionError("Setting default_assistant_with_help tidak dapat diubah")

@settings_bp.before_request
@require_auth
def check_access(**kwargs):
    # daftar exclude endpoint
    exclude = ["settings.list_settings"]

    if request.endpoint in exclude:
        return 

    # ambil user dari kwargs
    user = kwargs.get('user')

    # cek akses menu_user
    access = require_access(user, 'menu_setting')
    if not access or not access.get("value") : 
        return jsonify({"message": "Access tidak diizinkan"}), 403

@settings_bp.route("/settings", methods=["GET"])
@swag_from(yaml_path("settings_lists.yml"))
@require_auth
def list_settings(**kwargs):
    try:
        sel_query = """
            SELECT 
                id,
                type,
                name,
                description,
                data_type,
                unit,
                value,
                is_protected
            FROM settings
            ORDER BY name ASC
        """
        results, _ = safe_db_query(sel_query, [type])

        settings_list = []
        for u in results:
            raw_value = u[6]
            v = raw_value
            if v is not None:
                try:
                    dtype = (u[4] or '').strip().lower()
                    if dtype == 'boolean':
                        # accept 1/0, true/false strings, bool
                        if isinstance(v, bool):
                            v = v
                        elif isinstance(v, (int, float)):
                            v = bool(int(v))
                        elif isinstance(v, str):
                            v = v.strip().lower() in ('1', 'true', 'yes')
                    elif dtype == 'integer':
                        if isinstance(v, (int, float)):
                            v = int(v)
                        elif isinstance(v, str) and v.strip().lstrip('-').isdigit():
                            v = int(v)
                except Exception:
                    # fallback keep raw
                    pass

            if to_snake_case(u[2]) == 'api_key':
                resolved_value, _ = resolve_api_key_value(raw_value)
                v = mask_api_key(resolved_value)

            settings_list.append({
                "id": u[0],
                "type": u[1],
                "name": to_normal_text(u[2]),
                "description": u[3],
                "data_type": u[4],
                "unit": u[5],
                "value": v,
                "is_protected": u[7],
            })

        return (
            jsonify({
                "message": "Berhasil mengambil List settings",
                "data": settings_list,
            }),
            200,
        )

    except Exception as e:
        logging.error(f"List settings error: {e}")
        return jsonify({"error": "Gagal mengambil list setting"}), 500

@settings_bp.route("/settings/<type>", methods=["GET"])
@swag_from(yaml_path("settings_lists_by_type.yml"))
@require_auth
def list_settings_by_type(type=None, **kwargs):
    sel_query = """
        SELECT 
            id,
            type,
            name,
            description,
            data_type,
            unit,
            value,
            is_protected
        FROM settings
        WHERE type = %s
        ORDER BY name ASC
    """

    try:
        results, _ = safe_db_query(sel_query, [type])

        settings_list = []
        for u in results:
            raw_value = u[6]
            v = raw_value
            if v is not None:
                try:
                    dtype = (u[4] or '').strip().lower()
                    if dtype == 'boolean':
                        # accept 1/0, true/false strings, bool
                        if isinstance(v, bool):
                            v = v
                        elif isinstance(v, (int, float)):
                            v = bool(int(v))
                        elif isinstance(v, str):
                            v = v.strip().lower() in ('1', 'true', 'yes')
                    elif dtype == 'integer':
                        if isinstance(v, (int, float)):
                            v = int(v)
                        elif isinstance(v, str) and v.strip().lstrip('-').isdigit():
                            v = int(v)
                except Exception:
                    # fallback keep raw
                    pass

            if to_snake_case(u[2]) == 'api_key':
                resolved_value, _ = resolve_api_key_value(raw_value)
                v = mask_api_key(resolved_value)

            settings_list.append({
                "id": u[0],
                "type": u[1],
                "name": to_normal_text(u[2]),
                "description": u[3],
                "data_type": u[4],
                "unit": u[5],
                "value": v,
                "is_protected": u[7],
            })

        return (
            jsonify({
                "message": "Berhasil mengambil List settings",
                "data": settings_list,
            }),
            200,
        )

    except Exception as e:
        logging.error(f"List settings error: {e}")
        return jsonify({"error": "Gagal mengambil list setting"}), 500

@settings_bp.route("/setting/<setting_id>", methods=["GET"])
@swag_from(yaml_path("settings_list_by_id.yml"))
@require_auth
def get_setting_by_id(setting_id, **kwargs):
    sel_query = """
        SELECT 
            id,
            type,
            name,
            description,
            data_type,
            unit,
            value,
            is_protected
        FROM settings
        WHERE id = %s
    """

    try:
        results, _ = safe_db_query(sel_query, [setting_id])
        
        setting = (
            tuple(results[0])
            if results and isinstance(results, list) and len(results) > 0
            else None
        )

        if not setting:
            return jsonify({"error": "Setting tidak ditemukan"}), 404
        
        raw_value = setting[6]
        v = raw_value
        if v is not None:
            try:
                dtype = (setting[4] or '').strip().lower()
                if dtype == 'boolean':
                    # accept 1/0, true/false strings, bool
                    if isinstance(v, bool):
                        v = v
                    elif isinstance(v, (int, float)):
                        v = bool(int(v))
                    elif isinstance(v, str):
                        v = v.strip().lower() in ('1', 'true', 'yes')
                elif dtype == 'integer':
                    if isinstance(v, (int, float)):
                        v = int(v)
                    elif isinstance(v, str) and v.strip().lstrip('-').isdigit():
                        v = int(v)
            except Exception:
                # fallback keep raw
                pass

        if to_snake_case(setting[2]) == 'api_key':
            resolved_value, _ = resolve_api_key_value(raw_value)
            v = resolved_value if resolved_value else ''

        return (
            jsonify(
                {
                    "message": "Data setting",
                    "data": {
                        "id": setting[0],
                        "type": setting[1],
                        "name": to_normal_text(setting[2]),
                        "description": setting[3],
                        "data_type": setting[4],
                        "unit": setting[5],
                        "value": v,
                        "is_protected": setting[7],
                    },
                }
            ),
            200,
        )

        return (
            jsonify({
                "message": "Berhasil mengambil List settings",
                "data": settings_list,
            }),
            200,
        )

    except Exception as e:
        logging.error(f"List settings error: {e}")
        return jsonify({"error": "Gagal mengambil data setting"}), 500

@settings_bp.route("/setting", methods=["POST"])
@swag_from(yaml_path("settings_create.yml"))
@require_auth
def create_setting(**kwargs):
    data = request.get_json() or {}

    name = to_snake_case((data.get("name") or "").strip())
    type = (data.get("type") or "").strip()
    description = (data.get("description") or "").strip()

    # Prefer data_type; fallback to legacy 'input' if provided
    data_type = (data.get("data_type") or data.get("input") or "").strip() if (data.get("data_type") or data.get("input")) else None
    unit = data.get("unit") if data.get("unit") else None
    value = data.get("value")

    # validasi input
    if not name or not data_type or not type or not description or "value" not in data:
        return jsonify({"error": "Nama, Data Type, Type, Value dan Description diperlukan"}), 400

    if not valid_setting_datatype(data_type):
        return jsonify({"error": "Data type wajib string, boolean, integer, array, object"}), 400

    if(not valid_setting_value(data_type, value)) :
        return jsonify({"error": f"Nilai yang diinputkan tidak valid"}), 400

    if name == 'api_key':
        if data_type != 'string':
            return jsonify({"error": "API key wajib bertipe string"}), 400
        if not is_openai_api_key(value):
            return jsonify({"error": "Format API key tidak valid. Harus menggunakan OpenAI API key."}), 400

    if (data_type == 'boolean' or data_type == 'integer') :
        value = int(value)
    elif (data_type == 'array' or data_type == 'object') :
        value = json.dumps(value)
    else :
        value = value

    if (name == 'api_key') :
        value = encrypt_aes(value)

    now = get_current_datetime()
    insert_query = """
        INSERT INTO settings (name, type, description, data_type, unit, value, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        results, _ = safe_db_query(insert_query, [name, type, description, data_type, unit, value, now, now])

        if not results:
            return jsonify({"error": "Gagal membuat setting"}), 500

        return (jsonify({"message": "setting berhasil dibuat",}),201)

    except Exception as e:
        logging.error(f"Create setting error: {e}")
        return jsonify({"error": "Gagal membuat setting"}), 500

@settings_bp.route("/setting/<setting_id>", methods=["PUT"])
@swag_from(yaml_path("setting_update.yml"))
@require_auth
def update_setting(setting_id, **kwargs):
    data = request.get_json() or {}
    user = kwargs.get("user") or {}
   
    name = to_snake_case((data.get("name") or "").strip())
    type = (data.get("type") or "").strip()
    description = (data.get("description") or "").strip()
    # Prefer data_type; fallback to legacy 'input'
    data_type = (data.get("data_type") or data.get("input") or "").strip()
    unit = (data.get("unit") or "").strip()
    value = data.get("value")

    # validasi input
    if not name or not data_type or not type or not description or "value" not in data:
        return jsonify({"error": "Nama, Data Type, Type, Value dan Description diperlukan"}), 400

    if not valid_setting_datatype(data_type):
        return jsonify({"error": "Data type wajib string, boolean, integer, array, object"}), 400

    if(not valid_setting_value(data_type, value)) :
        return jsonify({"error": f"Nilai yang diinputkan tidak valid"}), 400

    if name == 'api_key':
        if data_type != 'string':
            return jsonify({"error": "API key wajib bertipe string"}), 400
        if not is_openai_api_key(value):
            return jsonify({"error": "Format API key tidak valid. Harus menggunakan OpenAI API key."}), 400
    try:
        sel_query = "SELECT id, name FROM settings WHERE id = %s"
        results, _ = safe_db_query(sel_query, [setting_id])
        setting_to_update = tuple(results[0]) if results else None
        if not setting_to_update:
            return jsonify({"error": "setting tidak ditemukan"}), 404
    except Exception as e:
        logging.error(f"Edit setting error: {e}")
        return jsonify({"error": "Gagal membuat setting"}), 500

    try:
        _ensure_setting_edit_permission(setting_to_update[1], user)
    except PermissionError as perm_err:
        return jsonify({"error": str(perm_err)}), 403
        
    if (data_type == 'boolean' or data_type == 'integer') :
        value = int(value)
    elif (data_type == 'array' or data_type == 'object') :
        value = json.dumps(value)
    else :
        value = value

    if setting_to_update[1] == 'api_key' :
        value = encrypt_aes(value)

    update_fields = []
    update_fields.append("name = %s")
    update_fields.append("type = %s")
    update_fields.append("description = %s")
    update_fields.append("data_type = %s")
    update_fields.append("unit = %s")
    update_fields.append("value = %s")
    update_fields.append("updated_at = %s")

    params = []
    params.append(name)
    params.append(type)
    params.append(description)
    params.append(data_type)
    params.append(unit)
    params.append(value)
    params.append(get_current_datetime())  # updated_at
    params.append(setting_id)  # WHERE id = %s

    try:
        query_update = f"UPDATE settings SET {', '.join(update_fields)} WHERE id = %s"
        results, _ = safe_db_query(query_update, params)

        if not results:
            return jsonify({"error": "Gagal mengupdate setting"}), 500

        return (jsonify({"message": "setting berhasil diupdate",}), 200)

    except Exception as e:
        logging.error(f"Edit setting error: {e}")
        return jsonify({"error": "Gagal membuat setting"}), 500

@settings_bp.route("/setting/<setting_id>", methods=["DELETE"])
@swag_from(yaml_path("setting_delete.yml"))
@require_auth
def delete_setting(setting_id, **kwargs):
    try:
        sel_query = "SELECT id FROM settings WHERE id = %s AND is_protected = FALSE"
        results, _ = safe_db_query(sel_query, [setting_id])
        setting_to_delete = tuple(results[0]) if results else None

        if not setting_to_delete:
            return jsonify({"error": "setting tidak ditemukan"}), 404

        delete_query = "DELETE FROM settings WHERE id = %s AND is_protected = FALSE"
        safe_db_query(delete_query, [setting_id])

        return (
            jsonify({"message": "setting berhasil dihapus"}),
            200,
        )

    except Exception as e:
        logging.error(f"Delete setting error: {e}")
        return jsonify({"error": "Gagal menghapus setting"}), 500
