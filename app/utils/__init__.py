"""Utility package re-export helpers.

This module lazily exposes selected helpers from the various submodules under
``app.utils`` to preserve the historical ``from app.utils import foo`` import
style.  Imports are deferred until an attribute is first accessed so optional
dependencies (e.g. Flask) do not break unrelated use cases like running cron
jobs.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from typing import Callable, Dict, Iterable, Tuple


logger = logging.getLogger(__name__)

# Registry that maps exported attribute names to the underlying module and the
# optional dependency (if any) that powers that feature.
_EXPORT_REGISTRY: Dict[str, Tuple[str, str | None]] = {}
__all__: list[str] = []


def _register(module: str, names: Iterable[str], optional_dependency: str | None = None) -> None:
    """Register ``names`` to be provided by ``module`` when requested."""

    for name in names:
        _EXPORT_REGISTRY[name] = (module, optional_dependency)
        __all__.append(name)


_register(
    'auth',
    (
        'require_auth',
        'require_admin',
        'passwd_hash',
        'passwd_check',
        'create_jwt_token',
        'validate_jwt_token',
        'create_refresh_token',
        'validate_refresh_token',
        'revoke_refresh_token',
        'revoke_all_refresh_tokens',
        'blacklist_token',
        'cleanup_expired_tokens',
    ),
    optional_dependency='flask',
)

_register(
    'portal',
    (
        'create_portal_token',
        'create_user_token',
        'validate_portal_token',
    ),
)

_register(
    'document',
    (
        'validate_file_content',
        'extract_text_from_pdf',
        'extract_text_from_image_ocr',
        'extract_text_from_document',
        'process_document_for_vector_storage',
    ),
)

_register('pgvectorstore', ('get_vectorstore',))

_register('portal_pull', ('pull_from_portal_logic',))

_register('general', ('chatbot', 'yaml_path'))

_register(
    'env_loader',
    (
        'env_load',
        'get_env',
        'get_database_config',
        'reload_env',
        'is_env_loaded',
    ),
)

_register(
    'database',
    (
        'getConnection',
        'safe_db_operation',
        'with_db_connection',
        'safe_db_query',
        'Connection',
    ),
    optional_dependency='psycopg2',
)


def __getattr__(name: str):  # pragma: no cover - thin wrapper
    try:
        module_name, optional_dependency = _EXPORT_REGISTRY[name]
    except KeyError as exc:  # Maintain AttributeError semantics
        raise AttributeError(f"module 'app.utils' has no attribute '{name}'") from exc

    try:
        module = importlib.import_module(f'.{module_name}', __name__)
    except ModuleNotFoundError as exc:
        if optional_dependency and exc.name == optional_dependency:
            message = (
                f"Cannot load '{name}' because the optional dependency "
                f"'{optional_dependency}' is not installed. Install project "
                "requirements (e.g. `pip install -r requirements.txt`) to enable this feature."
            )
            logger.warning(message)
            raise ModuleNotFoundError(message) from exc
        raise

    attr = getattr(module, name)
    globals()[name] = attr  # Cache for subsequent access
    return attr


def __dir__() -> list[str]:  # pragma: no cover - debug helper
    available: set[str] = set(globals())
    for name in __all__:
        module_name, optional_dependency = _EXPORT_REGISTRY.get(name, (None, None))
        if optional_dependency and importlib.util.find_spec(optional_dependency) is None:
            continue
        available.add(name)
    return sorted(available)

