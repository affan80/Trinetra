import pytest


pytest.importorskip("scrapy")


def test_canonical_spiders_load_with_shared_items():
    from services.ingestion.crawlers.spiders.blog_spider import BlogSpider
    from services.ingestion.crawlers.spiders.frontier_spider import FrontierSpider
    from services.ingestion.crawlers.spiders.image_spider import ImageSpider
    from services.ingestion.crawlers.spiders.news_spider import NewsSpider

    assert {BlogSpider.name, FrontierSpider.name, ImageSpider.name, NewsSpider.name} == {
        "blogs",
        "frontier",
        "images",
        "news",
    }
