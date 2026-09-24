import feedparser
import httpx
from urllib.parse import urljoin, urlsplit
from backend.app.security.http_client import fetch

FEED_PATHS = ("/feed", "/feed/", "/rss", "/rss/", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml")

def valid_feed(body: bytes) -> tuple[bool, str | None]:
    parsed = feedparser.parse(body)
    if parsed.bozo and not parsed.entries: return False, None
    kind = "atom" if parsed.version and "atom" in parsed.version.lower() else "rss"
    return bool(parsed.entries or parsed.feed), kind

def discover(base_url: str, allowed_domains: list[str], *, fetcher=fetch, allowed_url=None, home_body: bytes | None = None) -> list[dict]:
    candidates = []
    body = home_body if home_body is not None else fetcher(base_url, allowed_domains).body
    text = body.decode("utf-8", errors="ignore")
    for match in __import__("re").finditer(r'<link[^>]+(?:type=["\']application/(?:rss|atom)\+xml["\'])[^>]+>', text, __import__("re").I):
        href = __import__("re").search(r'href=["\']([^"\']+)', match.group(0), __import__("re").I)
        if href: candidates.append(urljoin(base_url, href.group(1)))
    candidates.extend(urljoin(base_url, path) for path in FEED_PATHS)
    found = []
    seen = set()
    found_urls = set()
    for candidate in candidates:
        if candidate in seen or urlsplit(candidate).hostname not in allowed_domains: continue
        seen.add(candidate)
        try:
            if allowed_url and not allowed_url(candidate): continue
            response = fetcher(candidate, allowed_domains, max_bytes=10 * 1024 * 1024); ok, kind = valid_feed(response.body)
            if ok and response.final_url not in found_urls:
                found_urls.add(response.final_url)
                found.append({"rss_url": response.final_url, "rss_type": kind, "validation_status": "VALID", "discovery_method": "html_link" if candidate not in [urljoin(base_url, p) for p in FEED_PATHS] else "conventional_path"})
        except (ValueError, OSError, httpx.RequestError): continue
    return found
