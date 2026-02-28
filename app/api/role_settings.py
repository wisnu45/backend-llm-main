from flask import Blueprint, request, jsonify
from flasgger import swag_from
from datetime import datetime
from werkzeug.security import generate_password_hash

from app.utils.database import safe_db_query
from app.utils.general import yaml_path
from app.utils.auth import require_auth, require_access, passwd_hash
from app.utils.portal import create_user_token

from app.utils.text import to_normal_text
from app.utils.validation import valid_setting_value

import logging
import requests
import json

role_settings_bp = Blueprint("role_settings", __name__)

@role_settings_bp.before_request
@require_auth
def check_access(**kwargs):
    # daftar exclude endpoint
    exclude = ["role_settings.list_roles_settings", "role_settings.list_roles_settings_by_id"]
    if request.endpoint in exclude:
        return 

    # ambil user dari kwargs
    user = kwargs.get('user')

    # cek akses menu_user
    access = require_access(user, 'menu_user')
    if not access or not access.get("value") : 
        return jsonify({"message": "Access tidak diizinkan"}), 403

@role_settings_bp.route("/role/settings/<role_id>", methods=["GET"])
@swag_from(yaml_path("role_settings_lists.yml"))
@require_auth
def list_roles_settings(role_id, **kwargs):
    try:
        sel_query = """
            SELECT 
                s.id,
                s.type,
                s.name,
                s.description,
                s.data_type,
                s.unit,
                COALESCE(rs.value, s.value) AS value
            FROM settings s
            LEFT JOIN roles_settings rs ON s.id = rs.settings_id AND rs.roles_id = %s
            ORDER BY s.name ASC
        """
        results, _ = safe_db_query(sel_query, [role_id])

        settings_list = []
        for u in results:
            v = u[6]
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

            settings_list.append({
                "role_id": role_id,
                "setting_id": u[0],
                "type": u[1],
                "name": to_normal_text(u[2]),
                "description": u[3],
                "data_type": u[4],
                "unit": u[5],
                "value": v,
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

@role_settings_bp.route("/role/settings/<role_id>/<type>", methods=["GET"])
@swag_from(yaml_path("role_settings_lists_by_type.yml"))
@require_auth
def list_roles_settings_by_id(role_id, type="feature", **kwargs):
    try:
        sel_query = """
            SELECT 
                s.id,
                s.type,
                s.name,
                s.description,
                s.data_type,
                s.unit,
                COALESCE(rs.value, s.value) AS value
            FROM settings s
            LEFT JOIN roles_settings rs ON s.id = rs.settings_id AND rs.roles_id = %s
            WHERE s.type = %s
            ORDER BY s.name ASC
        """
        results, _ = safe_db_query(sel_query, [role_id, type])

        settings_list = []
        for u in results:
            v = u[6]
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

            settings_list.append({
                "role_id": role_id,
                "setting_id": u[0],
                "type": u[1],
                "name": to_normal_text(u[2]),
                "description": u[3],
                "data_type": u[4],
                "unit": u[5],
                "value": v,
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

@role_settings_bp.route("/role/settings", methods=["POST"])
@swag_from(yaml_path("role_settings_create.yml"))
@require_auth
def create_roles_setting(**kwargs):
    data = request.get_json() or {}
    setting_id = data.get("setting_id") or False
    role_id = data.get("role_id") or False
    val = data.get("value")

    # validasi input awal
    if not role_id or not setting_id  or "value" not in data:
        return jsonify({"error": "Role, Feature, Value diperukan"}), 400

    sel_query = "SELECT id, data_type FROM settings WHERE id = %s"
    results, _ = safe_db_query(sel_query, [setting_id])

    setting = tuple(results[0]) if results else None
    if not setting:
        return jsonify({"error": "Setting tidak ditemukan"}), 404
    
    logging.error(f"Create role setting requested: type={setting[1]} value={val}")
    data_type = setting[1]

    if(not valid_setting_value(data_type, val)) :
        return jsonify({"error": f"Nilai yang diinputkan tidak valid"}), 400

    if (setting[1] == 'boolean'):
        value = int(val)
    elif (setting[1] == 'integer'):
        value = int(val)
    elif (setting[1] == 'array' or setting[1] == 'object') :
        value = json.dumps(val)

    sel_query = "SELECT id FROM roles WHERE id = %s"
    results, _ = safe_db_query(sel_query, [role_id])
    roles = tuple(results[0]) if results else None
    if not roles:
        return jsonify({"error": "Role tidak ditemukan"}), 404

    exist_query = "SELECT id FROM roles_settings WHERE roles_id = %s AND settings_id = %s"
    try:
        results, _ = safe_db_query(exist_query, [role_id, setting_id])
        exist = tuple(results[0]) if results else None

        if not exist:
            insert_query = """
                INSERT INTO roles_settings (roles_id, settings_id, value)
                VALUES (%s, %s, %s)
            """
            results, _ = safe_db_query(insert_query, [role_id, setting_id, value])
        else :
            update_query = "UPDATE roles_settings SET value = %s WHERE roles_id = %s AND settings_id = %s"
            results, _ = safe_db_query(update_query, [value, role_id, setting_id])

        if not results:
            return jsonify({"error": "Gagal membuat role setting"}), 500

        return (jsonify({"message": "Role setting berhasil dibuat"}),201)

    except Exception as e:
        logging.error(f"Create role error: {e}")
        return jsonify({"error": "Gagal membuat role setting"}), 500

@role_settings_bp.route("/role/settings/bulk", methods=["POST"])
@swag_from(yaml_path("role_settings_create_bulk.yml"))
@require_auth
def create_roles_setting_bulk(**kwargs):
    data = request.get_json() or {}

    # Cek apakah data berupa list
    if not isinstance(data, list):
        return jsonify({"error": "Request body harus berupa array of object"}), 400

    # Pengecekan data yang dikirimkan benar
    setting_ids = []
    role_ids = []
    settings_map = {}
    for idx, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            return jsonify({"error": f"Role, Feature, Value diperukan"}), 400

        if not all(k in item for k in ("setting_id", "role_id", "value")):
            return jsonify({"error": f"Role, Feature, Value diperukan"}), 400

        # Menampung UUID dan temporary data untuk di validasi data_type dan valuenya
        setting_uuid = item["setting_id"]
        role_uuid = item["role_id"]
        
        role_ids.append(role_uuid)
        setting_ids.append(setting_uuid)
        
        settings_map[setting_uuid] = {
            "setting_id": item["setting_id"],
            "role_id": item["role_id"],
            "value": item["value"]
        }

    # Ambil data setting ke database
    sel_query = """
        SELECT id, name, data_type
        FROM settings
        WHERE id = ANY(%s::uuid[])
    """
    results, _ = safe_db_query(sel_query, (setting_ids,))
    
    if len(results) != len(list(set(setting_ids))) : 
        return jsonify({"error": f"Terdapat setting yang tidak ditemukan"}), 404

    sel_query = """
        SELECT id
        FROM roles
        WHERE id = ANY(%s::uuid[])
    """
    results2, _ = safe_db_query(sel_query, (role_ids,))

    if len(results2) != len(list(set(role_ids))) : 
        return jsonify({"error": f"Terdapat role yang tidak ditemukan"}), 404

    unique_map = {}
    error = []
    for u in results:
        id = u[0]
        name = u[1]
        data_type = u[2]
        role_id = settings_map[id]['role_id']
        setting_id = settings_map[id]['setting_id']
        val = settings_map[id]['value']

        # Cek value sesuai data_type
        if(not valid_setting_value(data_type, val)) :
            error.append(to_normal_text(name))
        
        # Cek value sesuai data_type
        if val is not None:
            try:
                if data_type == 'boolean':
                    # accept 1/0, true/false strings, bool
                    if isinstance(val, bool):
                        val = val
                    elif isinstance(val, (int, float)):
                        val = bool(int(val))
                    elif isinstance(val, str):
                        val = val.strip().lower() in ('1', 'true', 'yes')
                elif data_type == 'integer':
                    if isinstance(val, (int, float)):
                        val = int(val)
                    elif isinstance(val, str) and val.strip().lstrip('-').isdigit():
                        val = int(val)
            except Exception:
                # fallback keep raw
                pass

            unique_map[(role_id, setting_id)] = (
                role_id,
                setting_id,
                val
            )

    # Kembalikan Error jika ada inputan yang error
    if(len(error) > 0) :
        invalid_fields = ", ".join(error)
        return jsonify({"error": f"Nilai {invalid_fields} yang diinputkan tidak valid"}), 400

    try:
        # Kirim values dalam bentuk batch
        query = """
        INSERT INTO roles_settings (roles_id, settings_id, value)
        VALUES %s
        ON CONFLICT (roles_id, settings_id)
        DO UPDATE SET 
            value = EXCLUDED.value,
            updated_at = now();
        """
        values = list(unique_map.values())

        safe_db_query(query, values, many=True)

        return jsonify({"message": "Roles settings berhasil dibuat"}), 201

    except Exception as e:
        logging.error(f"Bulk save error: {e}")
        return jsonify({"error": "Gagal membuat role setting"}), 500