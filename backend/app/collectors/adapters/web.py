from backend.app.security.http_client import fetch

def collect(url: str, allowed_domains: list[str], max_bytes: int = 10 * 1024 * 1024):
    return fetch(url, allowed_domains, max_bytes=max_bytes)
