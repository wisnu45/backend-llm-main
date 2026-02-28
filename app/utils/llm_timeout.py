import os
from typing import Any, Dict, List, Optional


def get_llm_timeout() -> Optional[float]:
    """Return request timeout (seconds) for LLM calls, or None when unset/invalid."""
    raw_value = os.getenv("LLM_REQUEST_TIMEOUT", os.getenv("OPENAI_TIMEOUT", "")).strip()
    if not raw_value:
        return None
    try:
        timeout_value = float(raw_value)
    except (TypeError, ValueError):
        return None
    if timeout_value <= 0:
        return None
    return timeout_value


def _build_timeout_variants(base_kwargs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return kwargs variants with timeout (if configured) and a no-timeout fallback."""
    base_copy = dict(base_kwargs)
    if "timeout" in base_copy or "request_timeout" in base_copy:
        without = dict(base_copy)
        without.pop("timeout", None)
        without.pop("request_timeout", None)
        return [base_copy, without]
    timeout_value = get_llm_timeout()
    if timeout_value is None:
        return [base_copy]
    with_timeout = dict(base_copy)
    with_timeout["timeout"] = timeout_value
    with_request_timeout = dict(base_copy)
    with_request_timeout["request_timeout"] = timeout_value
    return [with_timeout, with_request_timeout, base_copy]


def init_chat_openai(llm_kwargs: Dict[str, Any], max_tokens: Optional[int] = None) -> Any:
    """Initialize ChatOpenAI with optional timeout + max_tokens compatibility fallbacks."""
    from langchain_openai import ChatOpenAI

    variants = _build_timeout_variants(llm_kwargs)
    last_exc: Optional[TypeError] = None

    if max_tokens is not None:
        for kwargs in variants:
            try:
                return ChatOpenAI(max_tokens=max_tokens, **kwargs)
            except TypeError as exc:
                last_exc = exc
        for kwargs in variants:
            try:
                return ChatOpenAI(max_completion_tokens=max_tokens, **kwargs)
            except TypeError as exc:
                last_exc = exc

    for kwargs in variants:
        try:
            return ChatOpenAI(**kwargs)
        except TypeError as exc:
            last_exc = exc

    if last_exc is not None:
        raise last_exc
    raise TypeError("Failed to initialize ChatOpenAI with provided kwargs")
