import hashlib
from dataclasses import dataclass
from urllib.parse import urljoin
import httpx
from backend.app.security.network import resolve_public

MAX_REDIRECTS = 5
SECRET_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization", "x-api-key"}

@dataclass
class FetchResult:
    requested_url: str; final_url: str; status_code: int; content_type: str; headers: dict; body: bytes; redirect_chain: list[str]

def sanitized_headers(headers): return {k: v for k, v in headers.items() if k.lower() not in SECRET_HEADERS}

def fetch(url: str, allowed_domains: list[str], *, headers: dict | None = None, max_bytes: int = 10 * 1024 * 1024, timeout: float = 20.0) -> FetchResult:
    current = url; chain = []
    with httpx.Client(follow_redirects=False, timeout=timeout, verify=True, headers={"User-Agent": "TRINETRA-OSINT-Collector/0.1", **(headers or {})}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            resolve_public(current, allowed_domains)
            response = client.get(current, follow_redirects=False)
            if response.is_redirect:
                chain.append(current); current = urljoin(current, response.headers.get("location", "")); continue
            body = response.content
            if len(body) > max_bytes: raise ValueError("response exceeds configured size limit")
            return FetchResult(url, str(response.url), response.status_code, response.headers.get("content-type", "").split(";", 1)[0].lower(), sanitized_headers(response.headers), body, chain)
    raise ValueError("redirect limit exceeded")

def sha256(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
