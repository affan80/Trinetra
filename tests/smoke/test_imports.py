import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

try:
    from services.crawlers.spiders.blog_spider import BlogSpider
    from services.crawlers.spiders.news_spider import NewsSpider
    from services.crawlers.spiders.telegram_spider import TelegramSpider
    from services.crawlers.spiders.image_spider import ImageSpider
    from services.scraper.surfaceweb.blog_scraper import BlogScraper
    from services.scraper.surfaceweb.news_scraper import NewsScraper
    from services.scraper.surfaceweb.telegram_scraper import TelegramScraper
    from services.scraper.surfaceweb.image_scraper import ImageScraper
    from services.scraper.discovery import UrlCandidate
    from services.scraper.discovery.connectors import RssConnector, SitemapConnector
    from services.scraper.policy import SourceRegistry, SourceRegistryEntry
    from services.shared.url_frontier import UrlFrontier
    from services.crawlers.spiders.frontier_spider import FrontierSpider
    
    print(" All imports successful!")
    
    # Test instantiation (dummy response for scrapers would be needed for full test)
    print(" Classes identified correctly.")

except Exception as e:
    print(f" Import failed: {e}")
    sys.exit(1)
