"""
Global Environment Variables Loader
Centralized utility untuk loading environment variables dari .env file.
Menggunakan singleton pattern untuk memastikan load_dotenv() hanya dipanggil sekali.
"""

import os
import logging
from typing import Optional

# Global flag untuk tracking apakah environment sudah di-load
_env_loaded = False
_env_file_path = None

def env_load(env_file: str = '.env', force_reload: bool = False) -> bool:
    """
    Memastikan environment variables dari file .env sudah ter-load.
    
    Args:
        env_file: Path ke file .env (default: '.env')
        force_reload: Paksa reload meskipun sudah pernah di-load (default: False)
        
    Returns:
        bool: True jika berhasil load environment variables
    """
    global _env_loaded, _env_file_path
    
    try:
        # Jika sudah pernah di-load dan tidak force reload, skip
        if _env_loaded and not force_reload and _env_file_path == env_file:
            logging.debug(f"Environment variables already loaded from {env_file}")
            return True
            
        # Import dotenv hanya ketika dibutuhkan
        from dotenv import load_dotenv
        
        # Check if .env file exists
        if not os.path.exists(env_file):
            logging.warning(f"Environment file {env_file} not found, using system environment variables only")
            _env_loaded = True
            _env_file_path = env_file
            return True
            
        # Load environment variables
        success = load_dotenv(env_file, override=force_reload)
        
        if success:
            _env_loaded = True
            _env_file_path = env_file
            logging.info(f"✅ Environment variables loaded from {env_file}")
            
            # Debug logging untuk beberapa key environment variables
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            logging.debug(f"Environment check - DB_HOST: {db_host}, DB_PORT: {db_port}")
            
            return True
        else:
            logging.error(f"❌ Failed to load environment variables from {env_file}")
            return False
            
    except ImportError:
        logging.error("python-dotenv package not found. Please install it: pip install python-dotenv")
        return False
    except Exception as e:
        logging.error(f"Unexpected error loading environment variables: {e}")
        return False


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """
    Helper function untuk mendapatkan environment variable dengan auto-loading.
    
    Args:
        key: Environment variable key
        default: Default value jika key tidak ditemukan
        required: Raise exception jika key tidak ditemukan dan tidak ada default
        
    Returns:
        str: Value dari environment variable
        
    Raises:
        ValueError: Jika required=True dan key tidak ditemukan
    """
    # Auto-ensure environment loaded
    env_load()
    
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"Required environment variable '{key}' not found")
        
    return value


def get_database_config() -> dict:
    """
    Helper untuk mendapatkan konfigurasi database dari environment variables.
    
    Returns:
        dict: Database configuration
    """
    env_load()
    
    return {
        'host': get_env('DB_HOST', 'localhost'),
        'port': get_env('DB_PORT', '5432'),
        'database': get_env('DB_DATABASE'),
        'username': get_env('DB_USERNAME'),
        'password': get_env('DB_PASSWORD'),
    }


def reload_env(env_file: str = '.env') -> bool:
    """
    Force reload environment variables dari file .env.
    
    Args:
        env_file: Path ke file .env
        
    Returns:
        bool: True jika berhasil reload
    """
    return env_load(env_file, force_reload=True)


def is_env_loaded() -> bool:
    """
    Check apakah environment variables sudah di-load.
    
    Returns:
        bool: True jika sudah di-load
    """
    return _env_loaded


# Auto-load environment variables ketika modul di-import
# Ini memastikan backward compatibility dengan kode yang sudah ada
env_load()