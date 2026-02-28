"""Utility tools that can be exposed to LLM agents."""
from typing import Optional

try:
    from langchain_core.tools import tool as lc_tool
except ImportError:  # pragma: no cover - handled gracefully when dependency missing
    lc_tool = None  # type: ignore[assignment]

from app.utils.time_provider import get_current_datetime_string


def _current_datetime_impl(
    offset_hours: Optional[float] = None,
    fmt: str = "%Y-%m-%d %H:%M:%S %Z",
) -> str:
    # Project standard: always UTC. Ignore offset_hours.
    return get_current_datetime_string(fmt)


def _get_current_context_impl() -> str:
    """Get current datetime context optimized for LLM prompts."""
    current_time = get_current_datetime_string("%A, %B %d, %Y at %H:%M %Z")
    year = get_current_datetime_string("%Y")
    return f"Current time: {current_time} (Year: {year})"


if lc_tool is not None:

    @lc_tool
    def current_datetime_tool(
        offset_hours: Optional[float] = None,
        fmt: str = "%Y-%m-%d %H:%M:%S %Z",
    ) -> str:
        """Return the current datetime string in the requested format."""
        return _current_datetime_impl(offset_hours=offset_hours, fmt=fmt)

    @lc_tool  
    def current_context_tool() -> str:
        """Get comprehensive current datetime context for LLM conversations."""
        return _get_current_context_impl()

else:  # pragma: no cover - dependency guard
    current_datetime_tool = None
    current_context_tool = None


__all__ = [
    name
    for name, value in globals().items()
    if name.endswith("_tool") and value is not None
]
