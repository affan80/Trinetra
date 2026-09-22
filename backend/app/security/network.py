import ipaddress
import socket
from urllib.parse import urlsplit

BLOCKED_PORTS = {80, 443}

def resolve_public(url: str, allowed_domains: list[str] | None = None) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname: raise ValueError("URL must use HTTP or HTTPS")
    if parsed.port and parsed.port not in BLOCKED_PORTS: raise ValueError("port is not allowed")
    if allowed_domains and parsed.hostname.lower() not in {d.lower() for d in allowed_domains}: raise ValueError("hostname is outside the approved domain")
    for result in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(result[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast or address.is_reserved or address.is_unspecified:
            raise ValueError("destination resolves to a blocked address")
    return parsed.hostname
