import time
from datetime import datetime, timedelta, timezone

from telethon.sync import TelegramClient
from telethon.errors import FloodWaitError, ChannelPrivateError, UsernameInvalidError

from services.common.text_cleaner import clean_text


class TelegramScraper:
    def __init__(self, api_id, api_hash, session_name="telegram_session", max_flood_wait=60):
        self.max_flood_wait = max_flood_wait
        self.client = TelegramClient(
            session_name,
            int(api_id),
            api_hash,
            flood_sleep_threshold=60,
        )

    def scrape_channels(self, channels, limit=50, days_back=7):
        since_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        with self.client:
            for channel in channels:
                yield from self.scrape_channel(channel, limit, since_date)

    def scrape_channel(self, channel, limit, since_date):
        try:
            entity = self.client.get_entity(channel)

            for message in self.client.iter_messages(entity, limit=limit):
                if message.date and message.date < since_date:
                    continue

                data = self.parse_message(message, entity)

                if data:
                    yield data

        except FloodWaitError as error:
            if error.seconds <= self.max_flood_wait:
                time.sleep(error.seconds)
            return

        except (ChannelPrivateError, UsernameInvalidError, ValueError):
            return

    def parse_message(self, message, entity):
        text = clean_text(message.message or "")

        if not text and not message.media:
            return None

        username = getattr(entity, "username", "") or ""

        return {
            "platform": "telegram",
            "channel_id": getattr(entity, "id", ""),
            "channel_title": getattr(entity, "title", ""),
            "channel_username": username,
            "message_id": message.id,
            "url": self.build_message_url(username, message.id),
            "text": text,
            "published_at": message.date.isoformat() if message.date else "",
            "views": getattr(message, "views", 0) or 0,
            "forwards": getattr(message, "forwards", 0) or 0,
            "replies": self.get_replies_count(message),
            "reactions": self.get_reactions(message),
            "media_type": self.get_media_type(message),
        }

    def build_message_url(self, username, message_id):
        if not username:
            return ""

        return f"https://t.me/{username}/{message_id}"

    def get_media_type(self, message):
        if not message.media:
            return ""

        return message.media.__class__.__name__

    def get_replies_count(self, message):
        replies = getattr(message, "replies", None)
        return getattr(replies, "replies", 0) if replies else 0

    def get_reactions(self, message):
        reactions = getattr(message, "reactions", None)

        if not reactions:
            return {}

        result = {}

        for reaction in reactions.results:
            emoji = getattr(reaction.reaction, "emoticon", "")
            count = getattr(reaction, "count", 0)

            if emoji:
                result[emoji] = count

        return result
