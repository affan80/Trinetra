from urllib.parse import urlparse

def validate_source_config(allowed_domains: list[str], config: dict) -> None:
    for key in ("url", "endpoint", "base_url"):
        value = config.get(key)
        if value:
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or (allowed_domains and parsed.hostname not in allowed_domains):
                raise ValueError("source URL is not allowed")
