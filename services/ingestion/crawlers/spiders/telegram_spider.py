import os

import scrapy
from dotenv import load_dotenv
from services.common.items import NewsItem
from services.scraper.surfaceweb.telegram_scraper import TelegramScraper


class TelegramSpider(scrapy.Spider):
    name = "telegram"

    custom_settings = {
        "CONCURRENT_REQUESTS": 1,
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, channels=None, limit=None, days_back=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        load_dotenv()

        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.session_name = os.getenv("TELEGRAM_SESSION", "telegram_session")

        env_channels = os.getenv("TELEGRAM_CHANNELS", "")
        env_allowed_channels = os.getenv("TELEGRAM_ALLOWED_CHANNELS", env_channels)
        self.allowed_channels = self.parse_channels(env_allowed_channels)
        self.channels = self.parse_channels(channels or env_channels)

        self.max_limit = int(os.getenv("TELEGRAM_MAX_LIMIT", 200))
        self.limit = min(int(limit or os.getenv("TELEGRAM_LIMIT", 50)), self.max_limit)
        self.days_back = int(days_back or os.getenv("TELEGRAM_DAYS_BACK", 7))

        if not self.api_id or not self.api_hash:
            raise ValueError("Missing TELEGRAM_API_ID or TELEGRAM_API_HASH")

        if not self.channels:
            raise ValueError("No Telegram channels provided")

        if self.allowed_channels:
            denied_channels = [channel for channel in self.channels if channel not in self.allowed_channels]
            if denied_channels:
                raise ValueError(f"Telegram channels are not allowlisted: {', '.join(denied_channels)}")

    def start_requests(self):
        yield scrapy.Request(
            url="data:text/plain,telegram-start",
            callback=self.parse,
            dont_filter=True,
        )

    def parse(self, response):
        scraper = TelegramScraper(
            api_id=self.api_id,
            api_hash=self.api_hash,
            session_name=self.session_name,
        )

        for data in scraper.scrape_channels(
            channels=self.channels,
            limit=self.limit,
            days_back=self.days_back,
        ):
            yield self.build_item(data)

    def build_item(self, data):
        item = NewsItem()

        item["source_name"] = data.get("channel_title", "telegram")
        item["source_type"] = "telegram"
        item["url"] = data.get("url", "")

        item["title"] = ""
        item["text"] = data.get("text", "")
        item["author"] = data.get("channel_username", "")
        item["published_at"] = data.get("published_at", "")

        item["country_tags"] = []
        item["topic_tags"] = []

        item["metadata"] = {
            "platform": "telegram",
            "channel_id": data.get("channel_id", ""),
            "channel_title": data.get("channel_title", ""),
            "channel_username": data.get("channel_username", ""),
            "message_id": data.get("message_id", ""),
            "views": data.get("views", 0),
            "forwards": data.get("forwards", 0),
            "replies": data.get("replies", 0),
            "reactions": data.get("reactions", {}),
            "media_type": data.get("media_type", ""),
            "source_policy": {
                "allowed_channels": self.allowed_channels,
                "limit": self.limit,
                "days_back": self.days_back,
            },
        }

        return item

    def parse_channels(self, channels):
        if not channels:
            return []

        parsed = [
            channel.strip().replace("@", "").replace("https://t.me/", "")
            for channel in channels.split(",")
            if channel.strip()
        ]

        result = []
        seen = set()
        for channel in parsed:
            key = channel.lower()
            if key not in seen:
                seen.add(key)
                result.append(channel)

        return result
