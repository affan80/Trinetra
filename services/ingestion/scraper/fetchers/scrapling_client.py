import time

from services.scraper.config import get_scrapling_settings
from services.scraper.fetchers.fetch_result import FetchResult


class ScraplingFetchClient:
    def __init__(self, settings=None):
        self.settings = settings or get_scrapling_settings()

    def fetch(self, url, mode=None):
        mode = (mode or self.settings.fetch_mode or "static").lower()

        if mode == "static":
            return self.fetch_static(url)

        if mode == "dynamic":
            return self.fetch_dynamic(url)

        if mode == "stealth":
            return self.fetch_stealth(url)

        return FetchResult(
            url=url,
            fetcher=f"scrapling_{mode}",
            error=f"Unsupported Scrapling fetch mode: {mode}",
        )

    def fetch_static(self, url):
        started = time.monotonic()

        try:
            from scrapling.fetchers import Fetcher

            kwargs = self.common_kwargs()
            response = Fetcher.get(url, **kwargs)
            return self.to_result(response, "scrapling_static", started)
        except Exception as exc:
            return self.error_result(url, "scrapling_static", started, exc)

    def fetch_dynamic(self, url):
        started = time.monotonic()

        if not self.settings.browser_enabled:
            return FetchResult(
                url=url,
                fetcher="scrapling_dynamic",
                error="SCRAPLING_BROWSER_ENABLED is false",
            )

        try:
            from scrapling.fetchers import DynamicFetcher

            kwargs = self.browser_kwargs()
            response = DynamicFetcher.fetch(url, **kwargs)
            return self.to_result(response, "scrapling_dynamic", started)
        except Exception as exc:
            return self.error_result(url, "scrapling_dynamic", started, exc)

    def fetch_stealth(self, url):
        started = time.monotonic()

        if not self.settings.browser_enabled:
            return FetchResult(
                url=url,
                fetcher="scrapling_stealth",
                error="SCRAPLING_BROWSER_ENABLED is false",
            )

        try:
            from scrapling.fetchers import StealthyFetcher

            kwargs = self.browser_kwargs()
            response = StealthyFetcher.fetch(url, **kwargs)
            return self.to_result(response, "scrapling_stealth", started)
        except Exception as exc:
            return self.error_result(url, "scrapling_stealth", started, exc)

    def common_kwargs(self):
        kwargs = {
            "timeout": self.settings.timeout_ms / 1000,
            "selector_config": {
                "adaptive": self.settings.adaptive_enabled,
            },
        }

        if self.settings.proxy_url:
            kwargs["proxy"] = self.settings.proxy_url

        return kwargs

    def browser_kwargs(self):
        kwargs = {
            "timeout": self.settings.timeout_ms,
            "headless": True,
            "network_idle": True,
            "selector_config": {
                "adaptive": self.settings.adaptive_enabled,
            },
        }

        if self.settings.proxy_url:
            kwargs["proxy"] = self.settings.proxy_url

        return kwargs

    def to_result(self, response, fetcher, started):
        body = getattr(response, "body", b"") or b""

        if isinstance(body, bytes):
            encoding = getattr(response, "encoding", "utf-8") or "utf-8"
            html = body.decode(encoding, errors="replace")
        else:
            html = str(body)

        return FetchResult(
            url=getattr(response, "url", ""),
            status=int(getattr(response, "status", 0) or 0),
            html=html,
            fetcher=fetcher,
            headers=dict(getattr(response, "headers", {}) or {}),
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    def error_result(self, url, fetcher, started, exc):
        return FetchResult(
            url=url,
            fetcher=fetcher,
            error=f"{type(exc).__name__}: {exc}",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
