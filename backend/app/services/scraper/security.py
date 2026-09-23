import asyncio
import ipaddress
import socket
from urllib.parse import urlparse


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only absolute HTTP(S) URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not allowed")
    try:
        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except OSError as exc:
        raise ValueError("URL host cannot be resolved") from exc
    if not addresses or any(
        not ipaddress.ip_address(item[4][0]).is_global for item in addresses
    ):
        raise ValueError("private or reserved URL host is not allowed")
    return url


async def validate_public_url_async(url: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, validate_public_url, url)
