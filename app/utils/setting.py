
from .text import to_snake_case, to_normal_text
from .database import safe_db_query
from .auth import get_key_iv
from .validation import is_openai_api_key
from .env_loader import env_load

# Ensure environment vars from .env are loaded once this module is imported
env_load()

import base64
import logging
import os
from typing import Optional, Tuple
import json
from Crypto.Cipher import AES


def resolve_api_key_value(raw_value: Optional[str]) -> Tuple[Optional[str], bool]:
    """Return decrypted API key (if encrypted) and flag indicating encryption."""
    if not raw_value or not isinstance(raw_value, str):
        return raw_value, False

    candidate = raw_value.strip()
    if not candidate:
        return candidate, False

    if is_openai_api_key(candidate):
        return candidate, False

    if len(candidate) % 4 != 0:
        return None, True

    try:
        decoded_bytes = base64.b64decode(candidate, validate=True)
    except Exception:
        # Not base64 → treat as plain text
        return None, False

    # Ciphertext from AES-CBC should be multiple of 16 bytes
    if len(decoded_bytes) == 0 or len(decoded_bytes) % 16 != 0:
        return None, True

    decrypted = _try_decrypt_api_key(decoded_bytes)
    if decrypted is not None:
        if is_openai_api_key(decrypted):
            return decrypted, True
        return None, True

    # If decryption fails (e.g., wrong key), treat as encrypted but unreadable so
    # downstream consumers can decide on fallback.
    return None, True


def mask_api_key(value: Optional[str]) -> str:
    """Return a masked version of the API key for display purposes."""
    if not value:
        return '*****'

    cleaned = value.strip()
    if not cleaned:
        return '*****'

    if len(cleaned) <= 6:
        return cleaned[0] + '*****' + cleaned[-1]

    if len(cleaned) > 18:
        prefix = cleaned[:13]
        suffix = cleaned[-5:]
    else:
        prefix = cleaned[: max(3, len(cleaned) // 2)]
        suffix = cleaned[-2:]

    return f"{prefix}*****{suffix}"


def _try_decrypt_api_key(cipher_bytes: bytes) -> Optional[str]:
    """Best-effort AES-CBC decryption without logging warnings."""
    key, iv = get_key_iv(require=False)
    if not key or not iv:
        return None

    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(cipher_bytes)
        pad_len = decrypted[-1]
        if pad_len < 1 or pad_len > 16:
            return None
        plain_bytes = decrypted[:-pad_len]
        return plain_bytes.decode("utf-8")
    except Exception:
        return None

def get_setting_value_by_name(setting_name):
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
        WHERE name = %s
    """
    try:
        results, _ = safe_db_query(sel_query, [setting_name])
        
        setting = (
            tuple(results[0])
            if results and isinstance(results, list) and len(results) > 0
            else None
        )

        if not setting or not setting[6]:
            return None

        raw_value = setting[6]

        if to_snake_case(setting_name) == 'api_key':
            resolved_value, _ = resolve_api_key_value(raw_value)
            v = resolved_value
        else:
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
                elif dtype in ('array', 'object'):
                    v = json.loads(str(v))

                return v
            except Exception:
                return None

        return None

    except Exception as e:
        return None
        

def get_openai_api_key() -> str:
    """Resolve the OpenAI API key, preferring the encrypted settings table."""
    # Ensure environment variables (including AES key/IV) are loaded before decrypting
    env_load()

    key = get_setting_value_by_name("api_key")

    if isinstance(key, str):
        key = key.strip()
        if key:
            if is_openai_api_key(key):
                return key
            else:
                raise ValueError("Invalid OpenAI API key in settings")
        else:
            raise ValueError("Empty OpenAI API key in settings")
    else:
        raise ValueError("OpenAI API key in settings is not a string")


def get_prompt(prompt_name: str, fallback: str = "") -> str:
    """
    Get prompt template from database.
    
    Args:
        prompt_name: Name of the prompt setting (e.g., 'default_rag', 'company_policy_rag')
        fallback: Fallback prompt if database query fails
        
    Returns:
        Prompt template string from database or fallback
    """
    try:
        prompt = get_setting_value_by_name(prompt_name)
        if prompt and isinstance(prompt, str):
            return prompt.strip()
        return fallback
    except Exception as e:
        logging.warning(f"Failed to get prompt '{prompt_name}' from database: {e}")
        return fallback
