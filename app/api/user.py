from flask import Blueprint, request, jsonify
from flasgger import swag_from

from app.utils.database import safe_db_query
from app.utils.general import yaml_path
from app.utils.auth import require_auth, require_access, passwd_hash, require_access
from app.utils.portal import get_profile_token
from app.utils.portal_document import sync_user_portal_document
from app.utils.time_provider import get_current_datetime

from app.utils.text import to_snake_case

import logging
import uuid

user_bp = Blueprint("user", __name__)

@user_bp.before_request
@require_auth
def check_access(**kwargs):
    # daftar exclude endpoint
    exclude = ["user.get_user_profile"]

    if request.endpoint in exclude:
        return 

    # ambil user dari kwargs
    user = kwargs.get('user')

    # cek akses menu_user
    access = require_access(user, 'menu_user')
    if not access or not access.get("value") : 
        return jsonify({"message": "Access tidak diizinkan"}), 403

# --- Get User Profile ---
@user_bp.route("/user/profile", methods=["GET"])
@swag_from(yaml_path("user_profile.yml"))
@require_auth
def get_user_profile(**kwargs):
    """
    Mendapatkan profil user yang sedang login
    """

    try:
        user = kwargs.get("user")

        if not user:
            return jsonify({"message": "User tidak ditemukan"}), 404

        query = """
            SELECT u.id, u.name, u.username,r.id AS roles_id, u.is_portal, u.is_protected, u.created_at, u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.id = %s
        """
        results, _ = safe_db_query(query, [user.get("user_id")])

        if isinstance(results, (list, tuple)) and results:
            user_data = results[0]
        else:
            return jsonify({"message": "User tidak ditemukan"}), 404

        return jsonify(
            {
                "message": "Berhasil mendapatkan profil user",
                "data": {
                    "id": user_data[0],
                    "name": user_data[1],
                    "username": user_data[2],
                    "role_id": user_data[3],
                    "is_portal": user_data[4],
                    "is_protected": user_data[5],
                    "created_at": user_data[6].isoformat() if user_data[6] else None,
                    "updated_at": user_data[7].isoformat() if user_data[7] else None,
                },
            }
        ), 200

    except Exception as e:
        logging.error(f"Get user profile failed: {e}")
        return jsonify({"message": "Gagal mendapatkan profil user"}), 500

@user_bp.route("/user/portal", methods=["POST"])
@swag_from(yaml_path("user_portal.yml"))
@require_auth
def get_user_portal(**kwargs):
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    if not username :
        return jsonify({"error": "Username diperlukan"}), 400
    
    # cek apakah username sudah ada
    try:
        query_check = """
            SELECT id 
            FROM users 
            WHERE username = %s
        """
        results, _ = safe_db_query(query_check, [username])
        if results and isinstance(results, list) and len(results) > 0:
            return jsonify({"error": "User sudah terpakai di Sistem"}), 400
    except Exception as e:
        logging.error(f"Create user - check username error: {e}")
        return jsonify({"error": "Gagal memproses request"}), 500

    # cek apakah username valid employee
    check_profile = get_profile_token(username)
    if check_profile.get("status") and isinstance(check_profile.get("data"), dict) : 
        data = check_profile.get("data")
        return jsonify({
            "data": {
                "name": data.get("OfficialName"),
                "username": data.get("UserId")
            },
            "success": True
        }), 200
    elif check_profile.get('status') and check_profile.get('error') : 
        return jsonify({"error": check_profile.get('error')}), 404
    elif not check_profile.get('status') : 
        return jsonify({"error": check_profile.get('error')}), 500

@user_bp.route("/users", methods=["GET"])
@swag_from(yaml_path("user_lists.yml"))
@require_auth
def list_users(**kwargs):
    params = []
    count_params = []
    where_conditions = []
    users_list = []

    # Search param
    search = request.args.get('search', '').strip()
    user_type = request.args.get('user_type', '').strip() or None
    if user_type and user_type not in ["all", "portal", "local"]:
        return jsonify({"message": "User Type tidak valid"}), 400

    if user_type == "portal":
        user_type = 1
    elif user_type == "local":
        user_type = 0
    else:
        user_type = None

    role_id = request.args.get('role_id', '').strip() or None
    if role_id:
        try:
            uuid.UUID(role_id)
        except Exception:
            return jsonify({"message": "Role ID harus berupa UUID yang valid"}), 400
    
    base_query = """
        SELECT 
            u.id,
            u.name,
            u.username,
            u.password,
            r.id AS role_id,
            r.name AS role,
            u.is_portal,
            u.is_protected
        FROM users u
        LEFT JOIN roles r ON u.roles_id = r.id
    """

    count_query = """
        SELECT COUNT(*) 
        FROM users u
    """

    # Pagination params
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        if page < 1: page = 1
        if page_size < 1: page_size = 10
    except Exception:
        page, page_size = 1, 10

    if search:
        where_conditions.append('u.name ILIKE %s')
        params.append(f'%{search}%')
        count_params.append(f'%{search}%')
    
    if user_type in [0, 1]:
        where_conditions.append('u.is_portal = %s')
        params.append(user_type == 1)
        count_params.append(user_type == 1)
    
    if role_id:
        where_conditions.append('u.roles_id = %s')
        params.append(role_id)
        count_params.append(role_id)

    if where_conditions:
        where_clause = ' WHERE ' + ' AND '.join(where_conditions)
        base_query += where_clause
        count_query += where_clause

    base_query += ' ORDER BY u.created_at DESC LIMIT %s OFFSET %s'
    params.extend([page_size, (page-1)*page_size])

    try:
        results, _ = safe_db_query(base_query, params)
        for u in results:
            users_list.append({
                "id": u[0],
                "name": u[1],
                "username": u[2],
                "role_id": u[4],
                "role": u[5],
                "is_portal": u[6],
                "is_protected": u[7],
            })
        
        total_rows, _ = safe_db_query(count_query, count_params)
        if not isinstance(total_rows, list) or not total_rows:
            total = 0
        else:
            total = total_rows[0][0]

        return (
            jsonify({
                "message": "Berhasil mengambil List users",
                "data": users_list,
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
        logging.error(f"List users error: {e}")
        return jsonify({"error": "Gagal mengambil list user"}), 500

@user_bp.route("/user/<user_id>", methods=["GET"])
@swag_from(yaml_path("user_detail.yml"))
@require_auth
def detail_user(user_id,**kwargs):
    try:
        uuid.UUID(user_id)
    except Exception:
        return jsonify({"message": "User ID harus berupa UUID yang valid"}), 400

    try:
        sel_query = """
            SELECT 
                u.id,
                u.name,
                u.username,
                r.id AS roles_id,
                r.name AS role,
                u.is_portal,
                u.is_protected,
                u.created_at,
                u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.id = %s
        """
        results, _ = safe_db_query(sel_query, [user_id])
        user = (
            tuple(results[0])
            if results and isinstance(results, list) and len(results) > 0
            else None
        )

        if not user:
            return jsonify({"error": "User tidak ditemukan"}), 404

        return (
            jsonify(
                {
                    "message": "Data User",
                    "data": {
                        "id": user[0],
                        "name": user[1],
                        "username": user[2],
                        "role_id": user[3],
                        "role": user[4],
                        "is_portal": user[5],
                        "is_protected": user[6],
                        "created_at": user[7].isoformat() if user[7] else None,
                        "updated_at": user[8].isoformat() if user[8] else None,
                    },
                }
            ),
            201,
        )
    except Exception as e:
        logging.error(f"List users error: {e}")
        return jsonify({"error": "Gagal mengambil data user"}), 500

@user_bp.route("/user", methods=["POST"])
@swag_from(yaml_path("user_create.yml"))
@require_auth
def create_user(**kwargs):
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = to_snake_case((data.get("username") or "").strip(), allowStrip=True, allowDot=True)
    password = data.get("password") or ""
    roles_id = data.get("roles_id") or ""
    is_portal = data.get("is_portal")

    # validasi input
    if not username or not isinstance(is_portal, bool) or not roles_id:
        return jsonify({"error": "Username, Portal User, dan Role diperlukan"}), 400

    # cek apakah username sudah ada
    try:
        query_check = """
            SELECT id 
            FROM users 
            WHERE username = %s
        """
        results, _ = safe_db_query(query_check, [username])
        if results and isinstance(results, list) and len(results) > 0:
            return jsonify({"error": "Username sudah digunakan"}), 400
    except Exception as e:
        logging.error(f"Create user - check username error: {e}")
        return jsonify({"error": "Gagal memproses request"}), 500

    # check role is exist
    try:
        sel_query = "SELECT id FROM roles WHERE id = %s"
        results, _ = safe_db_query(sel_query, [roles_id])
        role_exist = tuple(results[0]) if results else None

        if not role_exist:
            return jsonify({"error": "Role tidak ditemukan"}), 404

    except Exception as e:
        logging.error(f"Create user - Role Error: {e}")
        return jsonify({"error": "Gagal memproses request"}), 500

    # logic local employee | portal employee
    check_profile = get_profile_token(username)
    if check_profile.get("status") and isinstance(check_profile.get("data"), dict) : 
        if is_portal is False:
            return jsonify({"error": "User Merupakan User Portal Valid"}), 400

        data = check_profile.get("data")
        name = data.get("OfficialName")
        password = None
    elif check_profile.get('status') and check_profile.get('error') : 
        if not name or not password:
            return jsonify({"error": "Official Name, Username, User Role, dan Password diperlukan"}), 400
        if is_portal is True:
            return jsonify({"error": "Masukkan User Portal Valid"}), 400
    elif not check_profile.get('status') : 
        return jsonify({"error": check_profile.get('error')}), 500

    # hash password jika bukan user portal
    if is_portal is False:
        try:
            hashed_password = passwd_hash(password)
        except Exception as e:
            logging.error(f"Create user - hash password error: {e}")
            return jsonify({"error": "Gagal memproses password"}), 500
    else:
        # For portal user, store empty string to satisfy NOT NULL constraint
        hashed_password = "" 
    
    now = get_current_datetime()
    insert_query = """
        INSERT INTO users (name, username, password, roles_id, is_portal, created_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """

    try:
        safe_db_query(insert_query, [name, username, hashed_password, roles_id, is_portal, now, now])

        # ambil kembali record yang baru dibuat untuk mengembalikan response yang konsisten
        sel_query = """
            SELECT 
                u.id,
                u.name,
                u.username,
                r.id AS role_id,
                u.is_portal,
                u.is_protected,
                u.created_at,
                u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.username = %s
        """
        results, _ = safe_db_query(sel_query, [username])
        user = (
            tuple(results[0])
            if results and isinstance(results, list) and len(results) > 0
            else None
        )

        if not user:
            return jsonify({"error": "Gagal membuat user"}), 500

        # Jika User Portal jalankan fungsi sync Dokumen
        if user[4] :
            sync_user_portal_document(user[0], user[2])

        return (
            jsonify(
                {
                    "message": "User berhasil dibuat",
                    "data": {
                        "id": user[0],
                        "name": user[1],
                        "username": user[2],
                        "role_id": user[3],
                        "is_portal": user[4],
                        "is_protected": user[5],
                        "created_at": user[6].isoformat() if user[6] else None,
                        "updated_at": user[7].isoformat() if user[7] else None,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        logging.error(f"Create user error: {e}")
        return jsonify({"error": "Gagal membuat user"}), 500

@user_bp.route("/user/<user_id>", methods=["PUT"])
@swag_from(yaml_path("user_update.yml"))
@require_auth
def update_user(user_id, **kwargs):
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    username = to_snake_case((data.get("username") or "").strip(), allowStrip=True, allowDot=True)
    password = (data.get("password") or "").strip() if data.get("password") else None
    roles_id = data.get("roles_id") or ""
    is_portal = data.get("is_portal")

    try:
        uuid.UUID(user_id)
    except Exception:
        return jsonify({"message": "User ID harus berupa UUID yang valid"}), 400

    # validasi input
    if not username or not isinstance(is_portal, bool) or not user_id or not roles_id:
        return jsonify({"error": "Username, dan Portal User, ID User, dan Role diperlukan"}), 400

    # cek apakah username sudah ada
    try:
        query_check = """
            SELECT id 
            FROM users 
            WHERE username = %s
            AND id <> %s
        """
        results, _ = safe_db_query(query_check, [username, user_id])
        if results and isinstance(results, list) and len(results) > 0:
            return jsonify({"error": "Username sudah digunakan"}), 400
    except Exception as e:
        logging.error(f"Create user - check username error: {e}")
        return jsonify({"error": "Gagal memproses request"}), 500

    # check role is exist
    try:
        sel_query = "SELECT id FROM roles WHERE id = %s"
        results, _ = safe_db_query(sel_query, [roles_id])
        role_exist = results[0] if results and len(results) > 0 else None

        if not role_exist:
            return jsonify({"error": "Role tidak ditemukan"}), 404
    except Exception as e:
        logging.error(f"Create user - Role Error: {e}")
        return jsonify({"error": "Gagal memproses request"}), 500


     # logic local employee | portal employee
    check_profile = get_profile_token(username)
    if check_profile.get("status") and isinstance(check_profile.get("data"), dict) : 
        if is_portal is False:
            return jsonify({"error": "User Merupakan User Portal Valid"}), 400

        data = check_profile.get("data")
        name = data.get("OfficialName")
        password = None
    elif check_profile.get('status') and check_profile.get('error') : 
        if not name:
            return jsonify({"error": "Official Name, Username, User Role diperlukan"}), 400
        if is_portal is True:
            return jsonify({"error": "Masukkan User Portal Valid"}), 400
    elif not check_profile.get('status') : 
        return jsonify({"error": check_profile.get('error')}), 500


    update_fields = []
    params = []

    update_fields.append("name = %s")
    params.append(name)

    update_fields.append("username = %s")
    params.append(username)

    update_fields.append("roles_id = %s")
    params.append(roles_id)

    # hash password jika bukan user portal dan mau edit password
    if is_portal is False and password:
        try:
            hashed_password = passwd_hash(password)
            update_fields.append("password = %s")
            params.append(hashed_password)

        except Exception as e:
            logging.error(f"Create user - hash password error: {e}")
            return jsonify({"error": "Gagal memproses password"}), 500
    else:
        # For portal user, store empty string to satisfy NOT NULL constraint
        hashed_password = ""

    params.append(get_current_datetime())  # updated_at
    params.append(user_id)  # WHERE id = %s

    query_update = f"UPDATE users SET {', '.join(update_fields)}, updated_at = %s WHERE id = %s"

    try:
        safe_db_query(query_update, params)

        sel_query = """
            SELECT u.id, u.name, u.username, r.id AS role_id, u.is_portal, u.is_protected, u.created_at, u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.id = %s
        """
        results, _ = safe_db_query(sel_query, [user_id])
        user_updated = tuple(results[0]) if results else None

        if not user_updated:
            return jsonify({"error": "User tidak ditemukan"}), 404

        return (
            jsonify({
                "message": "User berhasil diupdate",
                "data": {
                    "id": user_updated[0],
                    "name": user_updated[1],
                    "username": user_updated[2],
                    "role_id": user_updated[3],
                    "is_portal": user_updated[4],
                    "is_protected": user_updated[5],
                    "created_at": user_updated[6].isoformat() if user_updated[6] else None,
                    "updated_at": user_updated[7].isoformat() if user_updated[7] else None,
                },
            }),
            200,
        )

    except Exception as e:
        logging.error(f"Update user error: {e}")
        return jsonify({"error": "Gagal mengupdate user"}), 500

@user_bp.route("/user/<user_id>", methods=["DELETE"])
@swag_from(yaml_path("user_delete.yml"))
@require_auth
def delete_user(user_id, **kwargs):
    try:
        uuid.UUID(user_id)
    except Exception:
        return jsonify({"message": "User ID harus berupa UUID yang valid"}), 400

    try:
        sel_query = "SELECT id FROM users WHERE id = %s"
        results, _ = safe_db_query(sel_query, [user_id])
        user_to_delete = tuple(results[0]) if results else None

        if not user_to_delete:
            return jsonify({"error": "User tidak ditemukan"}), 404

        delete_query = "DELETE FROM users WHERE id = %s AND is_protected = FALSE"
        safe_db_query(delete_query, [user_id])

        return (
            jsonify({"message": "User berhasil dihapus"}),
            200,
        )

    except Exception as e:
        logging.error(f"Delete user error: {e}")
        return jsonify({"error": "Gagal menghapus user"}), 500
