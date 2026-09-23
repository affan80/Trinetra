import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("scrapy", reason="legacy crawler dependencies are optional")

try:
    from services.ingestion.crawlers.spiders.blog_spider import BlogSpider
    from services.ingestion.crawlers.spiders.news_spider import NewsSpider
    from services.ingestion.crawlers.spiders.telegram_spider import TelegramSpider
    from services.ingestion.crawlers.spiders.image_spider import ImageSpider
    from services.ingestion.scraper.surfaceweb.blog_scraper import BlogScraper
    from services.ingestion.scraper.surfaceweb.news_scraper import NewsScraper
    from services.ingestion.scraper.surfaceweb.telegram_scraper import TelegramScraper
    from services.ingestion.scraper.surfaceweb.image_scraper import ImageScraper
    from services.ingestion.scraper.discovery import UrlCandidate
    from services.ingestion.scraper.discovery.connectors import RssConnector, SitemapConnector
    from services.ingestion.scraper.policy import SourceRegistry, SourceRegistryEntry
    from services.storage.shared.url_frontier import UrlFrontier
    from services.ingestion.crawlers.spiders.frontier_spider import FrontierSpider
    
    print(" All imports successful!")
    
    # Test instantiation (dummy response for scrapers would be needed for full test)
    print(" Classes identified correctly.")

except Exception as e:
    print(f" Import failed: {e}")
    sys.exit(1)
