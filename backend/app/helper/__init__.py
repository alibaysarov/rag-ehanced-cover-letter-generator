"""Helper package exports for shared auth and utility helpers."""

from .browser import block_resources, get_body_from_page, scroll_page_bottom
from .flatten_list import flatten_list
from .url import get_domain_by_url

__all__ = [
    "CurrentUser",
    "WsUser",
    "flatten_list",
    "get_current_user",
    "get_domain_by_url",
    "get_body_from_page",
    "block_resources",
    "scroll_page_bottom",
]


def __getattr__(name):
    if name in {"CurrentUser", "get_current_user"}:
        from .user import CurrentUser, get_current_user

        return {"CurrentUser": CurrentUser, "get_current_user": get_current_user}[name]

    if name in {"WsUser", "get_current_user_ws"}:
        from .user import WsUser, get_current_user_ws

        return {"WsUser": WsUser, "get_current_user_ws": get_current_user_ws}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
