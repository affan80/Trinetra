import json
from urllib.parse import urljoin, urlparse

from services.common.text_cleaner import clean_text
from services.scraper.config import get_scrapling_settings

try:
    from scrapling import Selector
except Exception:  # pragma: no cover - exercised when dependency is absent
    Selector = None


class ScraplingExtractor:
    extractor_version = "scrapling_base_v1"

    def __init__(self, html, url):
        self.html = html or ""
        self.url = url or ""
        self.settings = get_scrapling_settings()
        self.page = self.build_page()

    @property
    def available(self):
        return self.page is not None

    def build_page(self):
        if not self.settings.parser_enabled or Selector is None:
            return None

        try:
            return Selector(
                self.html,
                url=self.url,
                adaptive=self.settings.adaptive_enabled,
            )
        except Exception:
            return None

    def first_css(self, selectors):
        if not self.page:
            return ""

        for selector in selectors:
            value = self.page.css(selector).get()
            if value:
                return clean_text(str(value))

        return ""

    def all_css(self, selector):
        if not self.page:
            return []

        return [clean_text(str(value)) for value in self.page.css(selector).getall()]

    def urljoin(self, value):
        value = clean_text(str(value or ""))
        return urljoin(self.url, value) if value else ""

    def domain(self):
        return urlparse(self.url).netloc.replace("www.", "")

    def unique_add(self, items, seen, value):
        value = clean_text(str(value or ""))
        key = value.lower()

        if value and key not in seen:
            seen.add(key)
            items.append(value)

    def load_json_ld(self):
        data = []

        for script in self.all_css("script[type='application/ld+json']::text"):
            try:
                if script:
                    data.append(json.loads(script))
            except Exception:
                continue

        return data

    def find_key_recursive(self, data, target_key):
        if isinstance(data, dict):
            if target_key in data:
                return data[target_key]

            for value in data.values():
                result = self.find_key_recursive(value, target_key)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self.find_key_recursive(item, target_key)
                if result:
                    return result

        return None

    def provenance(self, fetcher="scrapy", fallback_used=False, fallback_reason=""):
        return {
            "scraper_engine": "scrapy",
            "parser_engine": "scrapling" if self.available else "scrapy",
            "fetcher": fetcher,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "extractor_version": self.extractor_version,
        }
