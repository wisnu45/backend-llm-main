from flask import Blueprint, request, jsonify
from flasgger import swag_from
import os

from app.utils.database import safe_db_query
from app.utils.auth import (
    require_auth,
    create_jwt_token,
    validate_jwt_token,
    create_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    revoke_all_refresh_tokens,
    blacklist_token,
    passwd_check,
)
from app.utils.time_provider import get_datetime_from_timestamp
from app.utils.portal import create_user_token, validate_portal_token
from app.utils.general import yaml_path
from app.utils.portal_document import sync_user_portal_document

import requests
import logging
import json

auth_bp = Blueprint("auth", __name__)

# --- HELPER FUNCTIONS ---

def get_refresh_token_cookie_settings():
    """
    Get refresh token cookie settings based on environment variables
    """
    expire_days = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    max_age = expire_days * 24 * 60 * 60  # Convert days to seconds
    is_secure = os.getenv("COOKIE_SECURE", "true").lower() == "true"
    cookie_domain = os.getenv("COOKIE_DOMAIN", "")  # Empty string means no domain
    
    params = {
        'httponly': True,
        'secure': is_secure,
        'samesite': 'None' if is_secure else 'Lax',  # None requires Secure=True
        'max_age': max_age,
        'path': '/',
    }

    # Add domain only if specified in environment
    if cookie_domain:
        params['domain'] = cookie_domain

    return params

# --- AUTH ENDPOINTS ---

def employee_portal_info(user_id):
    """
    Mendapatkan info employee dari portal eksternal menggunakan portal token.
    Mengembalikan dict dengan kunci 'success', 'data', dan/atau 'error'.
    """
    try:
        token = create_user_token(user_id)
        url = f"https://portal.combiphar.com/Employee/GetEmployeeInfo?q={token}"
        response = requests.get(
            url,
            timeout=10,
            headers={
                "Accept": "application/json",
                "User-Agent": "backend-llm/portal-client",
            },
        )

        if response.status_code != 200:
            logging.warning("Portal response %s: %s", response.status_code, (response.text or "")[:500])
            return {
                "success": False,
                "error": f"Portal error {response.status_code}: {response.text}",
            }

        # status_code == 200
        try:
            data = response.json()
        except ValueError:
            raw_text = response.text or ""
            if (not raw_text) and (response.content or b""):
                try:
                    raw_text = (response.content or b"").decode("utf-8", errors="replace")
                except Exception:
                    raw_text = ""

            raw = raw_text.strip()

            if not raw:
                # Portal occasionally replies 200 with empty body (still sets JSON content-type).
                logging.warning(
                    "Portal returned empty body for employee info (user=%s, content_len=%s)",
                    user_id,
                    len(response.content or b""),
                )
                return {"success": False, "error": "Data portal kosong atau user tidak ditemukan"}

            # Fallback: some portal responses include non-JSON wrapper/prefix.
            # Try extracting the first JSON object from the response body.
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    data = json.loads(raw[start : end + 1])
                except Exception:
                    data = None
            else:
                data = None

            if data is None:
                content_type = response.headers.get("Content-Type", "")
                logging.error(
                    "Gagal parsing JSON dari portal (status=%s, content_type=%s, body_prefix=%r)",
                    response.status_code,
                    content_type,
                    raw[:200],
                )
                return {"success": False, "error": "Gagal parsing data dari portal"}

        # Some portal deployments return JSON-as-string (e.g. "{...}")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                logging.error("Gagal parsing JSON string dari portal (body_prefix=%r)", data[:200])
                return {"success": False, "error": "Gagal parsing data dari portal"}

        if not isinstance(data, dict):
            logging.error("Portal JSON unexpected type: %s", type(data))
            return {"success": False, "error": "Format data portal tidak sesuai"}

        return {
            "success": True,
            "data": {
                "name": data.get("OfficialName"),
                "username": data.get("UserId"),
            },
        }

    except requests.Timeout:
        logging.error("Timeout saat menghubungi portal")
        return {"success": False, "error": "Timeout saat menghubungi portal"}
    except requests.RequestException as e:
        logging.error("Request error: %s", e)
        return {"success": False, "error": f"Request error: {e}"}

def is_user_exists(userdata):
    """
    Memeriksa apakah user dengan username tertentu ada di database.
    Jika belum ada, daftarkan user baru.
    Return: dict user jika ada/berhasil daftar, None jika gagal.
    """
    try:
        user = userdata if isinstance(userdata, dict) else {}
        username = user.get("username", "").strip()
        name = user.get("name") or user.get("OfficialName")
        if not username:
            logging.warning("Username tidak boleh kosong")
            return None

        # Cek apakah user dengan username sudah ada
        # Use roles.name by joining roles table (users has roles_id)
        query = """
            SELECT u.id, u.name, u.username, r.id AS role_id, r.name AS role_name, u.is_portal, u.created_at, u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.username = %s
        """
        results, _ = safe_db_query(query, [username])

        if results and isinstance(results, list) and len(results) > 0:
            user_row = results[0]
            # User Portal terdaftar jalankan fungsi sync Dokumen
            sync_user_portal_document(user_row[0], user_row[2])
            return {
                "id": user_row[0],
                "name": user_row[1],
                "username": user_row[2],
                "role": {
                    "id": user_row[3],
                    "name": user_row[4],
                },
                "is_portal": user_row[5],
                "created_at": user_row[6].isoformat() if user_row[6] else None,
                "updated_at": user_row[7].isoformat() if user_row[7] else None,
            }

        # Jika belum ada, daftarkan user baru
        # Insert new user using roles_id reference (find role id for 'user')
        query = """
            INSERT INTO users (username, name, password,roles_id, is_portal)
            VALUES (%s, %s, %s, (SELECT id FROM roles WHERE name = %s LIMIT 1), %s)
        """

        params = [
            username,
            name,
            "",
            "user",  # Default role name is 'user' -> roles_id resolved by subquery
            True,  # is_portal True untuk user SSO
        ]

        results, _ = safe_db_query(query, params)

        sel_query = """
            SELECT 
                u.id,
                u.name,
                u.username,
                r.id AS role_id,
                r.name AS role_name,
                u.is_portal,
                u.created_at,
                u.updated_at
            FROM users u
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE u.username = %s
        """
        results2, _ = safe_db_query(sel_query, [username])
        new_user = (
            tuple(results2[0])
            if results2 and isinstance(results2, list) and len(results2) > 0
            else None
        )

        if not new_user:
            return None

        # User Portal Baru jalankan fungsi sync Dokumen
        sync_user_portal_document(new_user[0], new_user[2])

        return {
            "id": new_user[0],
            "name": new_user[1],
            "username": new_user[2],
            "role": {
                "id": new_user[3],
                "name": new_user[4],
            },
            "is_portal": new_user[5],
            "created_at": new_user[6].isoformat() if new_user[6] else None,
            "updated_at": new_user[7].isoformat() if new_user[7] else None,
        }
    except Exception as e:
        logging.error(f"Failed to check/register user: {e}")
        return None

# --- Login with username/password ---
@auth_bp.route("/auth/login", methods=["POST"])
@swag_from(yaml_path("auth_login.yml"))
def login():
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"message": "Username dan password diperlukan"}), 401

    # Select user with role name via join on roles
    query = """
        SELECT 
            u.id,
            u.name,
            u.username,
            u.password,
            r.id AS roles_id,
            r.name AS role_name,
            u.is_portal,
            u.created_at, u.updated_at
        FROM users u
        LEFT JOIN roles r ON u.roles_id = r.id
        WHERE u.username = %s
    """
    results, _ = safe_db_query(query, [username])
    user = (
        tuple(results[0])
        if results and isinstance(results, list) and len(results) > 0
        else None
    )

    if not user:
        return jsonify({"message": "Username atau password tidak valid"}), 401

    if not passwd_check(password, user[3]):  # user[3] adalah password
        return jsonify({"message": "Username atau password tidak valid"}), 401

    try:
        revoke_all_refresh_tokens(user[0])
        access_token = create_jwt_token(user[0], user[4])
        refresh_token = create_refresh_token(user[0])
        if not access_token or not refresh_token:
            return jsonify({"message": "Gagal membuat token"}), 500
        
        # Update last_login
        update_query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        safe_db_query(update_query, [user[0]])
        logging.info(f"User last_login updated: {user[0]}")

        if user[6]:
            sync_user_portal_document(user[0], user[2])

        response = jsonify(
            {
                "message": "Berhasil login",
                "data": {
                    "access_token": access_token,
                    "userdata": {
                        "id": user[0],
                        "name": user[1],
                        "username": user[2],
                        "role": {
                            "id": user[4],
                            "name": user[5],
                        },
                        "is_portal": user[6],
                        "created_at": user[7].isoformat() if user[7] else None,
                        "updated_at": user[8].isoformat() if user[8] else None,
                    },
                },
            }
        )
        
        # Set refresh token as HttpOnly Secure Cookie
        cookie_settings = get_refresh_token_cookie_settings()
        response.set_cookie('refresh_token', refresh_token, **cookie_settings)
        
        return response, 200
    except Exception as e:
        logging.error(f"Login error: {e}")
        return jsonify({"message": "Gagal melakukan login"}), 500

# --- SSO Login with Portal Token ---
@auth_bp.route("/auth/sso-login", methods=["POST"])
@swag_from(yaml_path("auth_sso_login.yml"))
def sso_auth():
    """
    SSO Login endpoint untuk menerima token dari Portal Combiphar
    """
    try:
        data = request.get_json(silent=True) or {}
        portal_token = data.get("token")

        if not portal_token:
            return jsonify({"message": "SSO token is required"}), 400

        logging.info(f"SSO LOGIN: Processing token: {portal_token[:20]}...")

        # Validate token
        validation_result = validate_portal_token(portal_token)
        if not validation_result["is_valid"]:
            return jsonify(
                {
                    "message": f"Token validation failed: {validation_result.get('message', 'Invalid token')}"
                }
            ), 401

        # Get user data from portal
        username = validation_result["username"]
        user_info = employee_portal_info(username)

        if not user_info.get("success"):
            return jsonify(
                {
                    "message": f"User with username {username} not found. Please contact administrator."
                }
            ), 404

        # Check if user already exists or register if not
        user_db = is_user_exists(user_info["data"])

        if not user_db:
            return jsonify(
                {
                    "message": "User not registered in the system and failed to auto-register. Please contact administrator."
                }
            ), 404

        # Generate session tokens
        access_token = create_jwt_token(user_db["id"], user_db["role"]["id"])
        refresh_token = create_refresh_token(user_db["id"])
        user_data = user_db

        response = jsonify(
            {
                "message": "Berhasil login",
                "data": {
                    "access_token": access_token,
                    "userdata": {
                        "id": user_data["id"],
                        "name": user_data.get("name"),
                        "username": user_data.get("username"),
                        "role": {
                            "id": user_data["role"]["id"],
                            "name": user_data["role"]["name"],
                        },
                        "is_portal": user_data.get("is_portal"),
                        "created_at": user_data.get("created_at"),
                        "updated_at": user_data.get("updated_at"),
                    },
                },
            }
        )
        
        # Set refresh token as HttpOnly Secure Cookie
        cookie_settings = get_refresh_token_cookie_settings()
        response.set_cookie('refresh_token', refresh_token, **cookie_settings)
        
        return response, 200

    except Exception as e:
        logging.error(f"SSO LOGIN ERROR: {e}")
        return jsonify({"message": "SSO login failed due to internal error"}), 500

# --- Token Refresh ---
@auth_bp.route("/auth/refresh", methods=["POST"])
@swag_from(yaml_path("auth_refresh.yml"))
def refresh_token():
    """
    Endpoint untuk refresh access token menggunakan refresh token
    """
    try:
        # Read refresh token from cookie instead of request body
        refresh_token_value = request.cookies.get('refresh_token')

        if not refresh_token_value:
            return jsonify({"message": "Refresh token diperlukan"}), 400

        # Validasi refresh token
        token_data = validate_refresh_token(refresh_token_value)
        if not token_data:
            return jsonify(
                {"message": "Refresh token tidak valid atau sudah expired"}
            ), 401

        # Buat access token baru
        access_token = create_jwt_token(
            token_data["user_id"],
            token_data["role_id"],
        )

        return jsonify(
            {
                "message": "Token berhasil di-refresh",
                "data": {
                    "access_token": access_token,
                },
            }
        ), 200

    except Exception as e:
        logging.error(f"Refresh token error: {e}")
        return jsonify({"message": "Gagal refresh token"}), 500

# --- Logout ---
@auth_bp.route("/auth/logout", methods=["POST"])
@swag_from(yaml_path("auth_logout.yml"))
@require_auth
def logout(**kwargs):
    """
    Endpoint untuk logout user
    """
    try:
        user = kwargs.get("user")
        data = request.get_json() or {}
        # Read refresh token from cookie instead of request body
        refresh_token_value = request.cookies.get('refresh_token')
        revoke_all_tokens = data.get("revoke_all", False)  # Optional parameter

        # Ambil access token dari header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ", 1)[1]

            # Validasi token untuk mendapatkan expiration
            token_data = validate_jwt_token(access_token)
            if token_data and token_data.get("exp"):
                # Blacklist access token
                exp_datetime = get_datetime_from_timestamp(token_data["exp"])
                blacklist_token(access_token, exp_datetime)

        # Revoke refresh token jika diberikan
        if refresh_token_value:
            revoke_refresh_token(refresh_token_value)

        # Atau revoke semua refresh token untuk user ini jika diminta
        if revoke_all_tokens and user and "user_id" in user:
            revoke_all_refresh_tokens(user["user_id"])

        # Create response and clear refresh token cookie
        response = jsonify({"message": "Berhasil logout"})
        cookie_settings = get_refresh_token_cookie_settings()
        # Override for clearing cookie
        cookie_settings['max_age'] = 0
        response.set_cookie('refresh_token', '', **cookie_settings)
        
        return response, 200

    except Exception as e:
        logging.error(f"Logout error: {e}")
        return jsonify({"message": "Gagal logout"}), 500

# --- Logout from all devices ---
@auth_bp.route("/auth/logout-all", methods=["POST"])
@swag_from(yaml_path("auth_logout_all.yml"))
@require_auth
def logout_all(**kwargs):
    """
    Endpoint untuk logout dari semua device (revoke semua refresh token)
    """
    try:
        user = kwargs.get("user")

        if not user or not user.get("user_id"):
            return jsonify({"message": "User tidak valid"}), 401

        # Revoke semua refresh token untuk user ini
        success = revoke_all_refresh_tokens(user["user_id"])

        if not success:
            return jsonify({"message": "Gagal logout dari semua device"}), 500

        # Blacklist current access token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            access_token = auth_header.split(" ", 1)[1]

            token_data = validate_jwt_token(access_token)
            if token_data and token_data.get("exp"):
                exp_datetime = get_datetime_from_timestamp(token_data["exp"])
                blacklist_token(access_token, exp_datetime)

        # Create response and clear refresh token cookie
        response = jsonify({"message": "Berhasil logout dari semua device"})
        cookie_settings = get_refresh_token_cookie_settings()
        # Override for clearing cookie
        cookie_settings['max_age'] = 0
        response.set_cookie('refresh_token', '', **cookie_settings)
        
        return response, 200

    except Exception as e:
        logging.error(f"Logout all error: {e}")
        return jsonify({"message": "Gagal logout dari semua device"}), 500
