"""
Authentication utilities for JWT tokens, passwords, and user permissions.
"""

from flask import request, jsonify, g
from functools import wraps
from datetime import datetime, timedelta, timezone
from .database import safe_db_query
from Crypto.Cipher import AES
from .time_provider import get_current_datetime
import os
import base64
import logging
import jwt
import json
import secrets


def require_auth(f):
    """
    Dekorator untuk memvalidasi Bearer token JWT pada endpoint.
    Jika token valid, user info akan diteruskan ke endpoint via kwargs['user'].
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        user = None

        if not token:
            return jsonify({"message": "Authorization header is required"}), 401

        # Validasi Bearer Token
        if token.startswith("Bearer "):
            try:
                token_value = token.split(" ", 1)[1]
                validated_token = validate_jwt_token(token_value)
                if not validated_token:
                    return jsonify({"message": "Invalid or expired token"}), 401

                # Pastikan ini access token
                if validated_token.get("type") != "access":
                    return jsonify({"message": "Invalid token type"}), 401

                # Ambil user dari database menggunakan safe_db_query
                query = """
                    SELECT
                        u.id,
                        r.id AS role_id,
                        r.name AS role_name,
                        u.name,
                        u.username,
                        u.is_portal,
                        u.created_at,
                        u.updated_at
                    FROM users u
                    LEFT JOIN roles r ON u.roles_id = r.id
                    WHERE u.id = %s
                """
                results, _ = safe_db_query(query, [validated_token["user_id"]])
                # safe_db_query untuk SELECT mengembalikan list rows; pastikan tipe list
                if isinstance(results, list) and results:
                    row = results[0]
                    # row order: id, name, username, role, is_portal, created_at, updated_at
                    user = {
                        "user_id": str(row[0]),
                        "role_id": row[1],
                        "role_name": row[2],
                        "name": row[3],
                        "username": row[4],
                        "is_portal": row[5],
                    }
                else:
                    return jsonify({"message": "User not found"}), 401

            except Exception as e:
                logging.error(f"Authentication error: {e}", exc_info=True)
                return jsonify(
                    {"message": f"Terjadi kesalahan autentikasi: {str(e)}"}
                ), 401
        else:
            return jsonify(
                {"message": "Authorization header must be Bearer token"}
            ), 401

        if user is None:
            return jsonify(
                {"message": "Autentikasi tidak valid atau tidak tersedia"}
            ), 401

        # Simpan user di kwargs agar bisa diakses dalam fungsi endpoint
        kwargs["user"] = user
        try:
            g.current_user = user
        except Exception:
            # g may not be available outside request context; ignore silently
            pass
        return f(*args, **kwargs)

    return decorated

def require_auth_with_exclude(exclude=None):
    exclude = exclude or []

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.endpoint in exclude:
                return f(*args, **kwargs)
            # fallback ke require_auth biasa
            return require_auth(f)(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(user):
    """
    Fungsi helper untuk memeriksa apakah user adalah admin berdasarkan roles_id dari table roles
    """
    if not user or not user.get("role_id"):
        return jsonify({"error": "Tidak diizinkan"}), 403
    
    try:
        # Query untuk mendapatkan nama role berdasarkan role_id
        query = """
            SELECT name FROM roles WHERE id = %s
        """
        results, _ = safe_db_query(query, [user["role_id"]])
        
        if not results or not isinstance(results, list) or len(results) == 0:
            return jsonify({"error": "Role tidak ditemukan"}), 403
        
        role_name = results[0][0]
        if role_name != "admin":
            return jsonify({"error": "Tidak diizinkan"}), 403
        
        return user
    except Exception as e:
        logging.error(f"Error checking admin role: {e}")
        return jsonify({"error": "Gagal memverifikasi role"}), 500


def require_access(user, check_access=None):
    """
    Helper function untuk mengambil akses setting berdasarkan user.

    Args:
        user (dict): Object user yang sedang login (berisi informasi user).
        check_access (str): Nama setting yang akan difilter.

    Returns:
        Union[List[dict], dict]:
            - Jika tidak ada check_access mengembalikan list of setting berdasarkan role.
            - Jika check_access spesifik → mengembalikan single object setting.
            - Jika tidak ditemukan → return None.
    """
    if not user or not user.get("user_id"):
        return jsonify({"error": "Tidak diizinkan"}), 401
    
    user_id = user.get("user_id")

    sel_query = """
        SELECT 
            s.id,
            s.type,
            s.name,
            s.description,
            s.data_type,
            s.unit,
            COALESCE(rs.value, s.value) AS value
        FROM users u
        JOIN settings s ON true
        LEFT JOIN roles_settings rs 
            ON s.id = rs.settings_id 
        AND rs.roles_id = u.roles_id
        WHERE u.id = %s
    """

    try:
        results, _ = safe_db_query(sel_query, [user_id])
        if results and isinstance(results, list) and len(results) < 1:
            return jsonify({"error": "Tidak diizinkan"}), 403

        settings = {}
        for row in results:
            setting_name = row[2]
            v = row[6]
            if v is not None:
                try:
                    dtype = (row[4] or '').strip().lower()
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
                    elif dtype in ('object', 'array'):
                        if isinstance(v, str):
                            try:
                                v = json.loads(v)
                            except json.JSONDecodeError:
                                # kalau string bukan JSON valid, biarkan raw
                                pass
                except Exception:
                    # fallback keep raw
                    pass

            setting_obj = {
                "id": row[0],
                "type": row[1],
                "name": row[2],
                "description": row[3],
                "data_type": row[4],
                "unit": row[5],
                "value": v,
            }

            settings[setting_name] = setting_obj

        if(check_access) :
            return settings[check_access] if settings.get(check_access) else None
        else :
            return settings
    except Exception as e:
        logging.error(f"Require access - query access error: {e}")
        return jsonify({"error": "Gagal memproses request"}), 500


def passwd_hash(password):
    """
    Fungsi untuk meng-hash password menggunakan SHA-256
    """
    from werkzeug.security import generate_password_hash

    if not password:
        raise ValueError("Password tidak boleh kosong")
    return generate_password_hash(password)


def passwd_check(password, hashed_password):
    """
    Fungsi untuk memeriksa apakah password yang diberikan cocok dengan hash
    """
    from werkzeug.security import check_password_hash

    if not password or not hashed_password:
        raise ValueError("Password atau hashed password tidak boleh kosong")
    return check_password_hash(hashed_password, password)


def create_jwt_token(user_id, role_id):
    """Membuat JWT access token dan mengembalikan token string."""
    if not user_id:
        raise ValueError("user_id tidak boleh kosong")
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        logging.warning("JWT_SECRET_KEY environment variable not set")
        raise ValueError("Environment variable JWT_SECRET_KEY not set")
    exp_minutes_str = os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
    exp_minutes = int(exp_minutes_str)
    expires_at = get_current_datetime() + timedelta(minutes=exp_minutes)
    payload = {
        "user_id": user_id,
        "role_id": role_id,
        "type": "access",
        "exp": expires_at,
        "iat": get_current_datetime(),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def validate_jwt_token(token):
    """
    Fungsi untuk memvalidasi JWT token dan mengecek apakah token ada di blacklist.
    """
    import jwt
    import hashlib
    from .database import safe_db_query

    if not token:
        raise ValueError("Token tidak boleh kosong")

    secret_key = os.getenv("JWT_SECRET_KEY")

    if not secret_key:
        logging.warning("JWT_SECRET_KEY environment variable not set")
        raise ValueError("Environment variable JWT_SECRET_KEY not set")

    try:
        # Decode token
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])

        # Hash token untuk cek blacklist
        jti = hashlib.sha256(token.encode()).hexdigest()

        # Cek apakah token ada di blacklist
        query = """
            SELECT id FROM token_revoked
            WHERE jti = %s AND expires_at > CURRENT_TIMESTAMP
        """
        results, _ = safe_db_query(query, [jti])

        if results:
            logging.warning("Token sudah di-blacklist (logout)")
            return None

        return {
            "user_id": payload["user_id"],
            "role_id": payload["role_id"],
            "type": payload.get("type", "access"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }
    except jwt.ExpiredSignatureError:
        logging.warning("Token telah kedaluwarsa")
        return None
    except jwt.InvalidTokenError as e:
        logging.error(f"Token tidak valid: {e}")
        return None


def create_refresh_token(user_id):
    """
    Membuat JWT refresh token dan menyimpan jti ke database.
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        logging.warning(
            "JWT_SECRET_KEY environment variable not set, using default key"
        )
        raise ValueError("Environment variable JWT_SECRET_KEY not set")
    jti = secrets.token_hex(32)
    exp_days_str = os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    exp_days = int(exp_days_str)
    expires_at = get_current_datetime() + timedelta(days=exp_days)
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": expires_at,
        "iat": get_current_datetime(),
        "jti": jti,
    }
    refresh_token = jwt.encode(payload, secret_key, algorithm="HS256")
    query = """
        INSERT INTO token_refresh (user_id, jti, expires_at)
        VALUES (%s, %s, %s)
        RETURNING id
    """
    # INSERT ... RETURNING akan dianggap SELECT oleh safe_db_query dan mengembalikan rows
    insert_results, _ = safe_db_query(query, [user_id, jti, expires_at])
    if not insert_results:
        logging.error("Gagal menyimpan refresh token (no returning row)")
        return None
    return refresh_token


def validate_refresh_token(refresh_token):
    """
    Validasi refresh token JWT dan cek jti di database
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        logging.warning("JWT_SECRET_KEY environment variable not set")
        raise ValueError("Environment variable JWT_SECRET_KEY not set")
    try:
        payload = jwt.decode(refresh_token, secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            return None
        jti = payload.get("jti")
        if not jti:
            return None
        # Cek jti di database
        query = """
            SELECT rt.user_id, r.id AS role_id, rt.expires_at, rt.is_revoked
            FROM token_refresh rt
            JOIN users u ON rt.user_id = u.id
            LEFT JOIN roles r ON u.roles_id = r.id
            WHERE rt.jti = %s AND rt.is_revoked = FALSE AND rt.expires_at > CURRENT_TIMESTAMP
            LIMIT 1
        """
        results, _ = safe_db_query(query, [jti])

        if results and isinstance(results, list) and len(results) > 0:
            user_data = results[0]
            return {
                "user_id": user_data[0],
                "role_id": user_data[1],
                "expires_at": user_data[2],
            }
    except jwt.ExpiredSignatureError:
        logging.warning("Refresh token telah kedaluwarsa")
        return None
    except jwt.InvalidTokenError as e:
        logging.error(f"Refresh token tidak valid: {e}")
        return None


def revoke_refresh_token(refresh_token):
    """
    Revoke refresh token (set is_revoked = TRUE berdasarkan jti)
    """
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        return False
    try:
        payload = jwt.decode(
            refresh_token,
            secret_key,
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        jti = payload.get("jti")
        if not jti:
            return False
        query = """
            UPDATE token_refresh
            SET is_revoked = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE jti = %s
        """
        updated_count, _ = safe_db_query(query, [jti])
        # Untuk UPDATE safe_db_query mengembalikan rowcount (int)
        return bool(updated_count and isinstance(updated_count, int) and updated_count > 0)
    except Exception as e:
        logging.error(f"Gagal revoke refresh token: {e}")
        return False


def revoke_all_refresh_tokens(user_id):
    """
    Revoke semua refresh token untuk user tertentu
    """
    query = """
        UPDATE token_refresh
        SET is_revoked = TRUE, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s AND is_revoked = FALSE
    """
    updated_count, _ = safe_db_query(query, [user_id])
    return bool(updated_count and isinstance(updated_count, int) and updated_count > 0)


def blacklist_token(token, expires_at):
    """
    Tambahkan token ke blacklist untuk logout
    """
    import hashlib
    from .database import safe_db_query

    jti = hashlib.sha256(token.encode()).hexdigest()

    query = """
        INSERT INTO token_revoked (jti, expires_at)
        VALUES (%s, %s)
        ON CONFLICT (jti) DO NOTHING
    """
    inserted_count, _ = safe_db_query(query, [jti, expires_at])
    # INSERT tanpa RETURNING mengembalikan rowcount int
    return bool(inserted_count and isinstance(inserted_count, int) and inserted_count > 0)


def cleanup_expired_tokens():
    """
    Membersihkan token yang sudah expired dari database
    """
    from .database import safe_db_query

    try:
        # Clean expired refresh tokens
        query1 = """
            DELETE FROM token_refresh
            WHERE expires_at < CURRENT_TIMESTAMP OR is_revoked = TRUE
        """

        # Clean expired blacklisted tokens
        query2 = """
            DELETE FROM token_revoked
            WHERE expires_at < CURRENT_TIMESTAMP
        """

        deleted_refresh, _ = safe_db_query(query1, [])
        deleted_blacklisted, _ = safe_db_query(query2, [])
        logging.info(
            f"Cleanup expired tokens completed: refresh={deleted_refresh}, blacklisted={deleted_blacklisted}"
        )

    except Exception as e:
        logging.error(f"Error during token cleanup: {e}")
        raise

# --- helper padding ---
def pad(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)

def unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    return data[:-pad_len]

# --- get key & iv from ENV ---
def get_key_iv(require: bool = True):
    """Return AES key/IV pair; optionally allow missing configuration."""
    key_b64 = os.getenv("LOCAL_KEY_AES")
    iv_b64 = os.getenv("LOCAL_KEY_IV")

    if not key_b64 or not iv_b64:
        if require:
            raise RuntimeError("LOCAL_KEY_AES/LOCAL_KEY_IV environment variables are not configured")
        return None, None

    try:
        key = base64.b64decode(key_b64)
        iv = base64.b64decode(iv_b64)
        return key, iv
    except Exception as exc:
        logging.warning(f"Failed to decode AES key/iv: {exc}")
        if require:
            raise
        return None, None

# --- encrypt ---
def encrypt_aes(plaintext: str) -> str:
    key, iv = get_key_iv(require=True)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode()))
    return base64.b64encode(ciphertext).decode()  # simpan di DB / JSON

# --- decrypt ---
def decrypt_aes(ciphertext_b64: str) -> str:
    if not ciphertext_b64:
        return ""

    key, iv = get_key_iv(require=False)
    if not key or not iv:
        logging.warning("Skipping AES decryption because LOCAL_KEY_AES/LOCAL_KEY_IV are not configured")
        return ""

    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = base64.b64decode(ciphertext_b64.encode())
        decrypted = cipher.decrypt(ciphertext)
        return unpad(decrypted).decode()
    except Exception as exc:
        logging.warning(f"Failed to decrypt payload: {exc}")
        return ""
