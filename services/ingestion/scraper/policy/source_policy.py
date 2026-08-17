import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

from services.scraper.config import env_bool, env_int


def env_list(name):
    value = os.getenv(name, "")
    return [item.strip().lower() for item in value.split(",") if item.strip()]


@dataclass
class SourcePolicy:
    allow_domains: list[str] = field(default_factory=lambda: env_list("SCRAPER_ALLOW_DOMAINS"))
    deny_domains: list[str] = field(default_factory=lambda: env_list("SCRAPER_DENY_DOMAINS"))
    max_depth: int = field(default_factory=lambda: env_int("SCRAPER_MAX_DEPTH", 2))
    max_pages: int = field(default_factory=lambda: env_int("SCRAPER_MAX_PAGES", 100))
    download_delay: float = 1.0
    fallback_enabled: bool = field(default_factory=lambda: env_bool("SCRAPLING_FETCH_FALLBACK_ENABLED", False))
    fallback_mode: str = field(default_factory=lambda: os.getenv("SCRAPLING_FETCH_MODE", "static").strip().lower())

    def is_allowed(self, url):
        domain = urlparse(url).netloc.replace("www.", "").lower()

        if not domain:
            return False

        if any(domain == denied or domain.endswith("." + denied) for denied in self.deny_domains):
            return False

        if not self.allow_domains:
            return True

        return any(domain == allowed or domain.endswith("." + allowed) for allowed in self.allow_domains)
