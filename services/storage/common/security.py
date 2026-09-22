import urllib.parse
import ipaddress
import socket
import logging

logger = logging.getLogger(__name__)

def is_safe_url(url: str) -> bool:
    """
    Validates a URL to prevent SSRF:
    1. Checks for HTTP/HTTPS scheme.
    2. Prevents access to private/loopback IP addresses.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname to IP
        ip = socket.gethostbyname(hostname)
        
        # Check against private/loopback ranges
        if ipaddress.ip_address(ip).is_private or ipaddress.ip_address(ip).is_loopback:
            logger.warning(f"Blocked SSRF attempt: {url} (resolved to {ip})")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validating URL {url}: {e}")
        return False
