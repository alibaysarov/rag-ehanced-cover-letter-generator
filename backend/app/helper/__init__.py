"""Helper package exports for shared auth and utility helpers."""

from .flatten_list import flatten_list

__all__ = ["CurrentUser", "flatten_list", "get_current_user"]


def __getattr__(name):
    if name in {"CurrentUser", "get_current_user"}:
        from .user import CurrentUser, get_current_user

        return {"CurrentUser": CurrentUser, "get_current_user": get_current_user}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
