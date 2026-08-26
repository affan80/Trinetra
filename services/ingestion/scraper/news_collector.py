import feedparser
import httpx
import trafilatura

from .base_collector import BaseCollector
from .registry import SourceType


class NewsCollector(BaseCollector):
    def __init__(self):
        self.client = httpx.AsyncClient(follow_redirects=True)

    async def collect(self, feed_url: str):
        """Fetches RSS feed and extracts articles."""
        async with self.client.get(feed_url) as resp:
            feed = feedparser.parse(resp.text)
            articles = []
            for entry in feed.entries:
                # Direct fetch
                content = await self.fetch_article(entry.link)
                articles.append(self.prepare_item(
                    source_type=SourceType.NEWS.value,
                    url=entry.link,
                    title=entry.title,
                    **content
                ))
            return articles

    async def fetch_article(self, url):
        resp = await self.client.get(url)
        data = trafilatura.extract(resp.text, output_format="dict")
        return {
            "main_text": data.get("text"),
            "author": data.get("author"),
            "published_at": data.get("date"),
            "language": data.get("language")
        }
