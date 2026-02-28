"""
Portal integration utilities for Combiphar portal authentication and token management.
"""
import os
import requests
import logging
from datetime import timedelta

from base64 import b64decode, b64encode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from app.utils.time_provider import get_current_datetime

try:
    from zoneinfo import ZoneInfo  # py3.9+
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _to_jakarta(dt_utc) -> object:
    """Convert an aware UTC datetime to Asia/Jakarta.

    Portal token generation for GetEmployeeInfo is time-sensitive and typically
    expects Jakarta local time.
    """

    try:
        if ZoneInfo is not None:
            return dt_utc.astimezone(ZoneInfo("Asia/Jakarta"))
    except Exception:
        pass

    # Fallback: fixed UTC+7 offset
    return dt_utc + timedelta(hours=7)

def create_portal_token(username, password):
    """
    (Note : belum bisa diimplementasikan karena endpoint portal tidak tersedia)
    Generate portal token menggunakan Rijndael (AES) 256 CBC.
    Kombinasi: username|password (pipe delimiter).
    Key & IV diambil dari environment variable/config table.
    Output: token terenkripsi (base64).
    """
    # Ambil key dan IV dari environment/config
    aes_key_b64 = os.getenv("PORTAL_KEY_RJ256")
    aes_iv_b64 = os.getenv("PORTAL_KEY_IV")

    if not aes_key_b64 or not aes_iv_b64:
        logging.error("Environment variables RJ256Key or RJ256IV not set")
        raise ValueError("Environment variables RJ256Key or RJ256IV not set")

    key = b64decode(aes_key_b64)
    iv = b64decode(aes_iv_b64)

    # Gabungkan string dengan pipe delimiter
    combination = f"{username}|{password}"

    # Convert ke bytes dan padding PKCS7
    data_bytes = combination.encode('utf-8')
    padded_data = pad(data_bytes, AES.block_size)

    # Encrypt dengan AES-256 CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded_data)

    # Konversi ke base64
    token = b64encode(encrypted).decode('utf-8')
    logging.info("Generated portal token: %s...", token[:20])
    return token

def create_user_token(username='subhan.pradana'):
    """
    Fungsi untuk membuat token portal yang terenkripsi dengan AES-ECB.
    Token ini berisi username dan timestamp (tick) yang digunakan untuk autentikasi.
    """
    # Data awal
    key_base64 = os.getenv("PORTAL_KEY_BASE64")
    aes_key_b64 = os.getenv("PORTAL_KEY_AES")

    if not key_base64 or not aes_key_b64:
        logging.error("Environment variables PORTAL_KEY_BASE64 or PORTAL_KEY_AES not set")
        raise ValueError("Environment variables PORTAL_KEY_BASE64 or PORTAL_KEY_AES not set")

    # Format timestamp (tick) - portal typically expects Jakarta time
    now_utc = get_current_datetime()
    now_local = _to_jakarta(now_utc)
    tick = now_local.strftime('%Y-%m-%d %H:%M:%S')

    # Gabungkan string seperti di JS
    combination = f"userId={username}&tick={tick}&key={key_base64}"

    # Decode key dari base64
    key = b64decode(aes_key_b64)

    # Convert ke bytes dan padding (PKCS7)
    data_bytes = combination.encode('utf-8')
    padded_data = pad(data_bytes, AES.block_size)

    # Encrypt dengan AES-ECB mode
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted = cipher.encrypt(padded_data)

    # Konversi ke hex
    token = encrypted.hex()
    logging.info("Generated portal token: %s...", token[:20])
    return token

def validate_portal_token(token):
    """
    Validasi Token melalui Portal Combiphar
    Url : https://portal.combiphar.com/security/IsTokenValid2?id=[token]
    Return string pipe delimited => [True/False] | Message | userid
    """
    try:
        url = f"https://portal.combiphar.com/security/IsTokenValid2?id={token}"

        logging.info(f"Validating portal token: {token[:20]}...")

        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Akan melempar http status kode 4xx/5xx

        # Parse response: [True/False]|Message|userId
        # Portal may return a JSON string or plain text.
        try:
            payload = response.json()
            response_text = payload if isinstance(payload, str) else (response.text or "")
        except ValueError:
            response_text = response.text or ""

        response_text = response_text.strip()
        logging.info("Portal token validation response prefix: %r", response_text[:200])

        # Split response dengan pipe delimiter
        parts = response_text.split('|')
        if len(parts) == 3:
            is_valid_str = parts[0].lower()
            message = parts[1]
            username = parts[2]
            is_valid = is_valid_str == 'true'

            if is_valid:
                logging.info(f"Portal token validation successful for user: {username}")
                return {
                    'is_valid': True,
                    'username': username,
                    'message': message,
                }
            else:
                # Token invalid dari portal (is_valid_str == 'false')
                logging.info(f"Portal token validation failed: {message}")
                return {
                    'is_valid': False,
                    'message': message
                }
        else:
            # Format response tidak sesuai
            logging.error(f"Invalid portal response format: {response_text}")
            return {
                'is_valid': False,
                'message': f"Invalid response format from portal: {response_text}"
            }

    except requests.exceptions.Timeout:
        logging.warning(f"Portal token validation timeout for token: {token[:20]}...")
        return {
            'is_valid': False,
            'message': "Portal connection timeout. Please try again later."
        }
    except requests.exceptions.ConnectionError:
        logging.warning(f"Portal connection error for token: {token[:20]}...")
        return {
            'is_valid': False,
            'message': "Could not connect to Portal. Please check network connection or portal status."
        }
    except requests.exceptions.HTTPError as e:
        logging.warning(f"Portal HTTP error for token: {token[:20]}... - {e.response.status_code} {e.response.text}")
        return {
            'is_valid': False,
            'message': f"Portal HTTP error: {e.response.status_code} {e.response.text}"
        }
    except Exception as e:
        logging.error(f"An unexpected error occurred during portal token validation for token: {token[:20]}... - {e}", exc_info=True)
        return {
            'is_valid': False,
            'message': f"An unexpected validation error occurred: {e}"
        }

def get_profile_token(username):
    """
    Fungsi untuk mengambil data profile berdasarkan username

    Args:
        username (string): username portal account

    Returns:
        object: data profile from portal account or error
    """
    try:
        token = create_user_token(username)
        url = f"https://portal.combiphar.com/Employee/GetEmployeeInfo?q={token}"
        response = requests.get(
            url,
            timeout=10,
            headers={
                "Accept": "application/json",
                "User-Agent": "backend-llm/portal-client",
            },
        )
        if response.status_code == 200:
            try:
                data = response.json()
                return {
                    "status": True,
                    "data": data,
                }
            except ValueError:
                logging.error("Gagal parsing JSON dari portal")
                return {"status": True, "error": "Username tidak ditemukan"}
        else:
            logging.warning(f"Portal response {response.status_code}: {response.text}")
            return {
                "status": False,
                "error": f"Portal error {response.status_code}: {response.text}",
            }
    except requests.Timeout:
        logging.error("Timeout saat menghubungi portal")
        return {"status": False, "error": "Timeout saat menghubungi portal"}
    except requests.RequestException as e:
        logging.error(f"Request error: {e}")
        return {"status": False, "error": f"Request error: {e}"}
