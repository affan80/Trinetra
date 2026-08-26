from datetime import datetime
from typing import Any

import httpx
import trafilatura


class WebCollectionService:
    """Unified service for web collection via Direct HTTP and Scrapy."""

    def __init__(self, user_agent: str = "TrinetraCollector/1.0"):
        self.user_agent = user_agent
        self.client = httpx.AsyncClient(headers={"User-Agent": self.user_agent}, follow_redirects=True)

    async def fetch_and_extract(self, url: str) -> dict[str, Any]:
        """Method 2: Direct HTTP fetching and extraction using trafilatura."""
        try:
            response = await self.client.get(url, timeout=30.0)
            response.raise_for_status()
            
            html = response.text
            extracted_data = trafilatura.extract(
                html, 
                include_comments=False, 
                include_tables=True, 
                include_links=True,
                return_json=True
            )
            
            # Simple conversion to required schema
            data = trafilatura.extract(html, include_links=True, include_images=True, output_format="dict")
            
            return {
                "url": url,
                "title": data.get("title"),
                "description": data.get("description"),
                "main_text": data.get("text"),
                "html": html,
                "author": data.get("author"),
                "publication_date": data.get("date"),
                "language": data.get("language"),
                "links": data.get("links"),
                "images": data.get("images"),
                "collection_timestamp": datetime.utcnow().isoformat(),
                "source_type": "direct_http"
            }
        except Exception as e:
            return {"url": url, "error": str(e), "collection_timestamp": datetime.utcnow().isoformat()}

    def run_crawler(self, spider_name: str, start_urls: list):
        """Method 3: Trigger Scrapy crawling (Stub for future integration)."""
        # This would interface with the Scrapy CrawlerProcess

    async def close(self):
        await self.client.aclose()
