from services.common.text_cleaner import clean_text
from services.scraper.config import get_scrapling_settings


class FetchPolicy:
    def __init__(self, settings=None):
        self.settings = settings or get_scrapling_settings()

    def fallback_enabled(self, spider_override=False):
        return bool(spider_override or self.settings.fetch_fallback_enabled)

    def should_fallback(self, response, extracted_text="", spider_override=False):
        if not self.fallback_enabled(spider_override):
            return False, ""

        status = getattr(response, "status", 0) or 0
        if status in {403, 429, 503}:
            return True, f"blocked_status_{status}"

        body = getattr(response, "text", "") or ""
        if not clean_text(body):
            return True, "empty_response"

        text = clean_text(extracted_text)
        if len(text) < 120 and len(clean_text(body)) > 500:
            return True, "low_text_density"

        return False, ""
