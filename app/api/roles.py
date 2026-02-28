from flask import Blueprint, request, jsonify
from flasgger import swag_from
from werkzeug.security import generate_password_hash

from app.utils.database import safe_db_query
from app.utils.general import yaml_path
from app.utils.auth import require_auth, require_access, passwd_hash
from app.utils.portal import create_user_token
from app.utils.time_provider import get_current_datetime

import logging
import requests

roles_bp = Blueprint("roles", __name__)

@roles_bp.before_request
@require_auth
def check_access(**kwargs):
    # daftar exclude endpoint
    exclude = []

    if request.endpoint in exclude:
        return 

    # ambil user dari kwargs
    user = kwargs.get('user')

    # cek akses menu_user
    access = require_access(user, 'menu_user')
    if not access or not access.get("value") : 
        return jsonify({"message": "Access tidak diizinkan"}), 403


@roles_bp.route("/roles", methods=["GET"])
@swag_from(yaml_path("roles_lists.yml"))
@require_auth
def list_roles(**kwargs):
    params = []
    count_params = []
    where_conditions = []

    roles_list = []

    # Initiate Raw Query 
    base_query = """
        SELECT 
            id,
            name,
            description,
            is_protected,
            created_at,
            updated_at
        FROM roles
    """

    count_query = """
        SELECT COUNT(*) 
        FROM roles
    """

    # Search param
    search = request.args.get('search', '').strip()

    # Pagination params
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        if page < 1: page = 1
        if page_size < 1: page_size = 10
    except Exception:
        page, page_size = 1, 10

    if search:
        where_conditions.append('name ILIKE %s')
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')

    if where_conditions:
        where_clause = ' WHERE ' + ' AND '.join(where_conditions)
        base_query += where_clause
        count_query += where_clause

    base_query += ' ORDER BY created_at DESC LIMIT %s OFFSET %s'
    params.extend([page_size, (page-1)*page_size])

    try:
        results, _ = safe_db_query(base_query, params)
        for u in results:
            roles_list.append({
                "id": u[0],
                "name": u[1],
                "description": u[2],
                "is_protected": u[3],
                "created_at": u[4].isoformat() if u[4] else None,
                "updated_at": u[5].isoformat() if u[5] else None,
            })

        total_rows, _ = safe_db_query(count_query, count_params)
        if not isinstance(total_rows, list) or not total_rows:
            total = 0
        else:
            total = total_rows[0][0]

        return (
            jsonify({
                "message": "Berhasil mengambil List roles",
                "data": roles_list,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total // page_size) + (1 if total % page_size else 0)
                }
            }),
            200,
        )

    except Exception as e:
        logging.error(f"List roles error: {e}")
        return jsonify({"error": "Gagal mengambil list role"}), 500

@roles_bp.route("/role", methods=["POST"])
@swag_from(yaml_path("roles_create.yml"))
@require_auth
def create_role(**kwargs):
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    # validasi input
    if not name or not description:
        return jsonify({"error": "Name, dan Description diperlukan"}), 400

    # validasi special role
    if (name.lower()) in ["user", "admin"]:
        return jsonify({"error": f"Role dengan nama '{name}' tidak dapat dibuat"}), 400

    # validasi duplicate
    check_query =  """
        SELECT id
        FROM roles
        WHERE name ILIKE %s
    """
    try:
        checks, _ = safe_db_query(check_query, [name])
        exists = tuple(checks[0]) if checks else None
        if exists:
            return jsonify({"error": "Duplikat Nama Role"}), 400

    except Exception as e:
        logging.error(f"Create role error: {e}")
        return jsonify({"error": "Gagal membuat role"}), 500

    now = get_current_datetime()
    insert_query = """
        INSERT INTO roles (name, description, created_at, updated_at)
        VALUES (%s, %s, %s, %s)
    """

    try:
        results, _ = safe_db_query(insert_query, [name, description, now, now])

        if not results:
            return jsonify({"error": "Gagal membuat role"}), 500

        return jsonify({"message": "Role berhasil dibuat"}), 201

    except Exception as e:
        logging.error(f"Create role error: {e}")
        return jsonify({"error": "Gagal membuat role"}), 500

@roles_bp.route("/role/<role_id>", methods=["PUT"])
@swag_from(yaml_path("role_update.yml"))
@require_auth
def update_role(role_id, **kwargs):
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()

    # validasi input
    if not name or not description:
        return jsonify({"error": "Name, dan Description diperlukan"}), 400

    sel_query = "SELECT id, name FROM roles WHERE id = %s"
    results, _ = safe_db_query(sel_query, [role_id])
    role_to_update = tuple(results[0]) if results else None
    if not role_to_update:
        return jsonify({"error": "Role tidak ditemukan"}), 404

    if (role_to_update[1].lower()) in ["user", "admin"] :
        if(name != role_to_update[1]) :
            return jsonify({"error": f"Role dengan nama '{role_to_update[1]}' tidak dapat mengubah nama"}), 400
    
    # validasi duplicate
    check_query =  """
        SELECT id
        FROM roles
        WHERE id <> %s
        AND name ILIKE %s
    """
    try:
        checks, _ = safe_db_query(check_query, [role_id, name])
        exists = tuple(checks[0]) if checks else None
        if exists:
            return jsonify({"error": "Duplikat Nama Role"}), 400

    except Exception as e:
        logging.error(f"Create role error: {e}")
        return jsonify({"error": "Gagal membuat role"}), 500


    update_fields = []
    update_fields.append("name = %s")
    update_fields.append("description = %s")
    update_fields.append("updated_at = %s")

    params = []
    params.append(name)
    params.append(description)

    params.append(get_current_datetime())  # updated_at
    params.append(role_id)  # WHERE id = %s

    try:
        query_update = f"UPDATE roles SET {', '.join(update_fields)} WHERE id = %s"
        results, _ = safe_db_query(query_update, params)

        if not results:
            return jsonify({"error": "Gagal mengupdate role"}), 500

        return jsonify({"message": "Role berhasil diupdate"}), 200

    except Exception as e:
        logging.error(f"Edit role error: {e}")
        return jsonify({"error": "Gagal membuat role"}), 500

@roles_bp.route("/role/<role_id>", methods=["DELETE"])
@swag_from(yaml_path("role_delete.yml"))
@require_auth
def delete_role(role_id, **kwargs):
    try:
        # validasi user dengan roles yang ingin dihapus
        sel_query = "SELECT id FROM users WHERE roles_id = %s"
        check, _ = safe_db_query(sel_query, [role_id])
        user_in_roles = tuple(check[0]) if check else None
        if user_in_roles:
            return jsonify({"error": "Terdapat User yang merupakan Role Ini"}), 400

        # validasi roles ada
        sel_query = "SELECT id, name, is_protected FROM roles WHERE id = %s"
        delete_role, _ = safe_db_query(sel_query, [role_id])
        role_to_delete = tuple(delete_role[0]) if delete_role else None
        if not role_to_delete:
            return jsonify({"error": "Role tidak ditemukan"}), 404

        # validasi roles restricted (admin, user) dan protected
        if (role_to_delete[1].lower()) in ["user", "admin"] or role_to_delete[2] :
            return jsonify({"error": f"Role dengan nama '{role_to_delete[1]}' tidak dapat dihapus"}), 400

        # delete role
        delete_query = "DELETE FROM roles WHERE id = %s AND is_protected = FALSE"
        results, _ = safe_db_query(delete_query, [role_id])
        
        # delete setting role
        if results:
            delete_setting_query = "DELETE FROM roles_settings WHERE roles_id = %s"
            safe_db_query(delete_setting_query, [role_id])

        return (
            jsonify({"message": "Role berhasil dihapus"}),
            200,
        )

    except Exception as e:
        logging.error(f"Delete Role error: {e}")
        return jsonify({"error": "Gagal menghapus role"}), 500

@roles_bp.route("/role/<role_id>", methods=["GET"])
@swag_from(yaml_path("roles_detail.yml"))
@require_auth
def detail_role(role_id,**kwargs):
    try:
        sel_query = """
            SELECT
                id,
                name,
                description,
                is_protected,
                created_at,
                updated_at
            FROM roles
            WHERE id = %s
        """

        results, _ = safe_db_query(sel_query, [role_id])

        role = (
            tuple(results[0])
            if results and isinstance(results, list) and len(results) > 0
            else None
        )

        if not role:
            return jsonify({"error": "Gagal mengambil data role"}), 404

        return (
            jsonify(
                {
                    "message": "Data role",
                    "data": {
                        "id": role[0],
                        "name": role[1],
                        "description": role[2],
                        "is_protected": role[3],
                        "created_at": role[4].isoformat() if role[4] else None,
                        "updated_at": role[5].isoformat() if role[5] else None,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logging.error(f"Data roles error: {e}")
        return jsonify({"error": "Gagal mengambil data role"}), 404
