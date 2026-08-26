import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scrapy.http import HtmlResponse, Request
from services.crawlers.spiders.frontier_spider import FrontierSpider
from services.crawlers.spiders.image_spider import ImageSpider
from services.parser.pipelines import OsintPipeline
from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors import (
    BraveSearchConnector,
    CommonCrawlConnector,
    GdeltConnector,
    RedditConnector,
    RssConnector,
    SitemapConnector,
    YouTubeConnector,
)
from services.scraper.extractors import ArticleExtractor, BlogExtractor
from services.scraper.fetchers import ScraplingFetchClient
from services.scraper.policy import (
    FetchPolicy,
    SourcePolicy,
    SourceRegistry,
    SourceRegistryEntry,
)
from services.scraper.surfaceweb.image_scraper import ImageScraper
from services.shared.url_frontier import UrlFrontier


def make_response(url, html):
    request = Request(url=url)
    return HtmlResponse(
        url=url,
        request=request,
        body=html.encode("utf-8"),
        encoding="utf-8",
    )


def test_image_scraper_extracts_common_sources():
    response = make_response(
        "https://example.com/page",
        """
        <html>
            <head>
                <meta property="og:image" content="/meta.jpg">
                <title>Example page</title>
            </head>
            <body>
                <figure>
                    <img src="/plain.jpg" alt="Plain image">
                    <figcaption>Plain caption</figcaption>
                </figure>
                <img data-src="/lazy.jpg" alt="Lazy image">
                <img srcset="/small.jpg 320w, /large.jpg 1024w" alt="Srcset image">
                <picture>
                    <source srcset="/picture-small.jpg 320w, /picture-large.jpg 1024w">
                </picture>
                <img src="data:image/png;base64,abc" alt="Skip data URL">
            </body>
        </html>
        """,
    )

    images = list(ImageScraper(response).extract_images())
    urls = [image["url"] for image in images]

    assert urls == [
        "https://example.com/meta.jpg",
        "https://example.com/plain.jpg",
        "https://example.com/lazy.jpg",
        "https://example.com/small.jpg",
        "https://example.com/picture-small.jpg",
    ]
    assert images[1]["alt"] == "Plain image"
    assert images[1]["caption"] == "Plain caption"


def test_image_spider_caps_scheduled_requests():
    spider = ImageSpider(urls="https://example.com/", max_pages=2)

    first = spider.build_request("https://example.com/")
    second = spider.build_request("https://example.com/a")
    third = spider.build_request("https://example.com/b")

    assert first is not None
    assert second is not None
    assert third is None
    assert spider.scheduled_pages == 2


def test_pipeline_validates_image_urls():
    pipeline = OsintPipeline()

    assert pipeline.is_valid_item({
        "source_type": "image",
        "image_url": "https://example.com/image.jpg",
    })
    assert not pipeline.is_valid_item({
        "source_type": "image",
        "image_url": "data:image/png;base64,abc",
    })
    assert not pipeline.is_valid_item({
        "source_type": "image",
        "image_url": "",
    })


def test_article_extractor_reads_metadata_and_text():
    html = """
    <html lang="en">
      <head>
        <title>Fallback title</title>
        <meta property="og:title" content="Article title">
        <meta name="author" content="Analyst Desk">
        <meta property="article:published_time" content="2026-06-15T08:00:00Z">
        <meta property="og:image" content="/article.jpg">
        <script type="application/ld+json">
          {"@type": "NewsArticle", "keywords": ["defence", "osint"]}
        </script>
      </head>
      <body>
        <article>
          <p>This is a substantial first paragraph with enough content for extraction.</p>
          <p>This is a substantial second paragraph with enough content for extraction.</p>
          <p>This is a substantial third paragraph with enough content for extraction.</p>
        </article>
      </body>
    </html>
    """

    data = ArticleExtractor(html, "https://example.com/news/story").extract()

    assert data["title"] == "Article title"
    assert data["author"] == "Analyst Desk"
    assert "substantial first paragraph" in data["text"]
    assert data["images"] == ["https://example.com/article.jpg"]
    assert data["provenance"]["extractor_version"] == "scrapling_article_v1"


def test_blog_extractor_reads_tags_categories_and_featured_image():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Blog title">
        <meta name="keywords" content="cyber, policy">
        <meta property="og:image" content="/blog.jpg">
        <script type="application/ld+json">
          {"@type": "BlogPosting", "articleSection": "Analysis"}
        </script>
      </head>
      <body>
        <article>
          <div class="entry-content">
            <p>This is a substantial blog paragraph that should pass content filtering.</p>
          </div>
        </article>
      </body>
    </html>
    """

    data = BlogExtractor(html, "https://example.com/blog/story").extract()

    assert data["title"] == "Blog title"
    assert data["tags"] == ["cyber", "policy"]
    assert data["categories"] == ["Analysis"]
    assert data["featured_image"] == "https://example.com/blog.jpg"
    assert data["provenance"]["extractor_version"] == "scrapling_blog_v1"


def test_fetch_policy_respects_fallback_switch():
    response = make_response("https://example.com/blocked", "")
    response = response.replace(status=403)
    policy = FetchPolicy()

    assert policy.should_fallback(response, "", spider_override=False) == (False, "")
    assert policy.should_fallback(response, "", spider_override=True) == (True, "blocked_status_403")


def test_scrapling_fetch_client_returns_structured_errors():
    client = ScraplingFetchClient()
    result = client.fetch("https://example.com", mode="unsupported")

    assert result.fetcher == "scrapling_unsupported"
    assert "Unsupported Scrapling fetch mode" in result.error


def test_url_candidate_normalizes_core_fields():
    candidate = UrlCandidate(
        url="HTTPS://Example.com/story/#frag",
        discovered_from="unknown_provider",
        source_type="bad_type",
        priority=250,
        country_tags=["IN", "in", ""],
        topic_tags=["defence", "Defence"],
    )

    assert candidate.url == "https://example.com/story/"
    assert candidate.discovered_from == "manual"
    assert candidate.source_type == "unknown"
    assert candidate.priority == 100
    assert candidate.country_tags == ["IN"]
    assert candidate.topic_tags == ["defence"]


def test_source_registry_enriches_candidates():
    registry = SourceRegistry([
        SourceRegistryEntry(
            source_name="Example Think Tank",
            source_type="think_tank",
            base_url="https://example.com",
            priority=85,
            country_tags=["IN"],
            topic_tags=["security"],
            allow_paths=["/analysis"],
        )
    ])

    candidate = registry.enrich_candidate({
        "url": "https://example.com/analysis/report",
        "discovered_from": "manual",
    })

    assert candidate.source_type == "think_tank"
    assert candidate.priority == 85
    assert candidate.country_tags == ["IN"]
    assert candidate.topic_tags == ["security"]
    assert candidate.metadata["source_registry"]["source_name"] == "Example Think Tank"


class FakeQueue:
    def __init__(self):
        self.items = []
        self.dead_letters = []

    def push(self, item):
        self.items.append(item)
        return len(self.items)

    def pop(self):
        return self.items.pop(0) if self.items else None

    def blocking_pop(self, timeout=5):
        return self.pop()

    def length(self):
        return len(self.items)

    def move_to_dead_letter(self, item, reason="processing_failed"):
        self.dead_letters.append({"reason": reason, "item": item})
        return len(self.dead_letters)

    def dead_letter_length(self):
        return len(self.dead_letters)

    def get_dead_letters(self, limit=20):
        return self.dead_letters[:limit]


class FakeDedupe:
    def __init__(self):
        self.seen = set()

    def is_new_url(self, url, source="global", ttl_seconds=None):
        key = (source, url)

        if key in self.seen:
            return False

        self.seen.add(key)
        return True


def test_url_frontier_enqueues_dedupes_and_dequeues():
    queue = FakeQueue()
    frontier = UrlFrontier(
        queue=queue,
        dedupe=FakeDedupe(),
        policy=SourcePolicy(allow_domains=["example.com"]),
    )

    candidate = {
        "url": "https://example.com/story#section",
        "discovered_from": "rss",
        "source_type": "news",
    }

    first = frontier.enqueue(candidate)
    second = frontier.enqueue(candidate)

    assert first.accepted
    assert first.reason == "enqueued"
    assert second.reason == "duplicate_url"
    assert frontier.length() == 1
    assert frontier.dequeue()["url"] == "https://example.com/story"


def test_url_frontier_rejects_policy_denied_urls():
    frontier = UrlFrontier(
        queue=FakeQueue(),
        dedupe=FakeDedupe(),
        policy=SourcePolicy(deny_domains=["example.com"]),
    )

    result = frontier.enqueue({
        "url": "https://example.com/story",
        "discovered_from": "manual",
    })

    assert not result.accepted
    assert result.reason == "source_policy_rejected"


def test_url_frontier_batch_and_dead_letters():
    queue = FakeQueue()
    frontier = UrlFrontier(
        queue=queue,
        dedupe=FakeDedupe(),
        policy=SourcePolicy(allow_domains=["example.com"]),
    )
    frontier.enqueue({"url": "https://example.com/a", "discovered_from": "manual"})
    frontier.enqueue({"url": "https://example.com/b", "discovered_from": "manual"})

    batch = frontier.dequeue_many(5)
    assert [item["url"] for item in batch] == ["https://example.com/a", "https://example.com/b"]
    assert frontier.length() == 0

    frontier.move_to_dead_letter({"url": "https://example.com/fail"}, reason="test_failure")
    assert frontier.dead_letter_length() == 1
    assert frontier.get_dead_letters()[0]["reason"] == "test_failure"


class FakeResponse:
    def __init__(self, data=None, text="", content=b"", status_code=200):
        self._data = data
        self.text = text
        self.content = content or text.encode("utf-8")
        self.status_code = status_code

    def json(self):
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({
            "url": url,
            "params": params or {},
            "headers": headers or {},
            "timeout": timeout,
        })
        if not self.responses:
            raise AssertionError("No fake response configured")
        return self.responses.pop(0)


def test_rss_connector_extracts_candidates():
    xml = """
    <rss><channel>
      <item>
        <title>Story title</title>
        <link>https://example.com/story</link>
        <pubDate>Mon, 15 Jun 2026 08:00:00 GMT</pubDate>
      </item>
    </channel></rss>
    """
    connector = RssConnector(session=FakeSession([FakeResponse(content=xml.encode("utf-8"))]))
    result = connector.discover("https://example.com/feed.xml")

    assert result.ok
    assert result.candidates[0].url == "https://example.com/story"
    assert result.candidates[0].metadata["title"] == "Story title"


def test_sitemap_connector_extracts_candidates():
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/a</loc><lastmod>recent</lastmod></url>
      <url><loc>https://example.com/b</loc></url>
    </urlset>
    """
    connector = SitemapConnector(session=FakeSession([FakeResponse(content=xml.encode("utf-8"))]))
    result = connector.discover("https://example.com/sitemap.xml", max_results=1)

    assert result.ok
    assert len(result.candidates) == 1
    assert result.candidates[0].url == "https://example.com/a"


def test_brave_connector_requires_key_and_maps_results():
    missing = BraveSearchConnector(api_key="", session=FakeSession([])).discover("test")
    assert missing.errors[0].code == "missing_credentials"

    data = {"web": {"results": [{"url": "https://example.com/story", "title": "Title", "description": "Desc"}]}}
    connector = BraveSearchConnector(api_key="token", session=FakeSession([FakeResponse(data=data)]))
    result = connector.discover("test")

    assert result.ok
    assert result.candidates[0].discovered_from == "brave_search"
    assert result.candidates[0].metadata["title"] == "Title"


def test_gdelt_common_crawl_youtube_and_reddit_connectors_map_results():
    gdelt = GdeltConnector(session=FakeSession([
        FakeResponse(data={"articles": [{"url": "https://news.example/story", "title": "News"}]})
    ]))
    assert gdelt.discover("border").candidates[0].source_type == "news"

    cc_text = '{"url":"https://example.com/old","timestamp":"abc","status":"200","mime":"text/html"}\n'
    common_crawl = CommonCrawlConnector(session=FakeSession([FakeResponse(text=cc_text)]))
    assert common_crawl.discover("example.com/*", crawl="CC-MAIN-test").candidates[0].discovered_from == "common_crawl"

    youtube_data = {
        "items": [{
            "id": {"videoId": "abc123"},
            "snippet": {"title": "Video", "channelId": "chan", "publishedAt": "now"},
        }]
    }
    youtube = YouTubeConnector(api_key="key", session=FakeSession([FakeResponse(data=youtube_data)]))
    assert youtube.discover("query").candidates[0].url == "https://www.youtube.com/watch?v=abc123"

    reddit_data = {
        "data": {
            "after": None,
            "children": [{
                "data": {
                    "id": "p1",
                    "title": "Cyber report",
                    "url": "https://example.com/reddit-link",
                    "subreddit": "worldnews",
                    "permalink": "/r/worldnews/comments/p1/story/",
                }
            }],
        }
    }
    reddit = RedditConnector(session=FakeSession([FakeResponse(data=reddit_data)]))
    assert reddit.discover(subreddits=["worldnews"]).candidates[0].metadata["provider"] == "reddit"


def test_source_registry_loads_json_config():
    registry = SourceRegistry.from_file()
    assert registry.enabled_entries
    assert any(entry.source_name == "Books To Scrape Test" for entry in registry.enabled_entries)


class FakeFrontier:
    def __init__(self, candidates=None):
        self.candidates = candidates or []
        self.dead_letters = []

    def dequeue_many(self, limit):
        batch = self.candidates[:limit]
        self.candidates = self.candidates[limit:]
        return batch

    def move_to_dead_letter(self, candidate, reason="crawl_failed"):
        self.dead_letters.append({"candidate": candidate, "reason": reason})
        return len(self.dead_letters)


def test_frontier_spider_builds_news_item_with_candidate_metadata():
    candidate = UrlCandidate(
        url="https://example.com/news/story",
        discovered_from="rss",
        query="border",
        source_type="news",
        priority=70,
        country_tags=["IN"],
        topic_tags=["security"],
    )
    spider = FrontierSpider(frontier=FakeFrontier(), source_policy=SourcePolicy(allow_domains=["example.com"]))
    response = make_response(
        candidate.url,
        """
        <html>
          <head><meta property="og:title" content="Frontier title"></head>
          <body><article>
            <p>This paragraph has enough article content for extraction and validation.</p>
            <p>This second paragraph has enough article content for extraction and validation.</p>
          </article></body>
        </html>
        """,
    )
    item = spider.build_news_item(response, candidate)

    assert item["source_type"] == "news"
    assert item["country_tags"] == ["IN"]
    assert "security" in item["topic_tags"]
    assert item["metadata"]["frontier"]["discovered_from"] == "rss"


def test_offline_discovery_frontier_spider_pipeline_flow():
    xml = """
    <rss><channel>
      <item>
        <title>Pipeline Story</title>
        <link>https://example.com/news/pipeline</link>
      </item>
    </channel></rss>
    """
    connector = RssConnector(session=FakeSession([FakeResponse(content=xml.encode("utf-8"))]))
    discovery_result = connector.discover("https://example.com/feed.xml", source_type="news")
    queue = FakeQueue()
    frontier = UrlFrontier(
        queue=queue,
        dedupe=FakeDedupe(),
        policy=SourcePolicy(allow_domains=["example.com"]),
    )
    enqueue_result = frontier.enqueue(discovery_result.candidates[0])
    candidate = UrlCandidate.from_dict(frontier.dequeue())
    spider = FrontierSpider(frontier=FakeFrontier(), source_policy=SourcePolicy(allow_domains=["example.com"]))
    response = make_response(
        candidate.url,
        """
        <html>
          <head><meta property="og:title" content="Pipeline title"></head>
          <body><article>
            <p>This pipeline paragraph has enough content for the extractor to return text.</p>
            <p>This second pipeline paragraph keeps the item valid for the pipeline.</p>
          </article></body>
        </html>
        """,
    )
    item = spider.build_news_item(response, candidate)
    article = dict(item)
    pipeline = OsintPipeline()

    assert enqueue_result.accepted
    assert pipeline.is_valid_item(article)
    pipeline.add_audit_metadata(article)
    assert article["metadata"]["validation_status"] == "valid"
    assert article["metadata"]["source_url"] == candidate.url


def main():
    tests = [
        test_image_scraper_extracts_common_sources,
        test_image_spider_caps_scheduled_requests,
        test_pipeline_validates_image_urls,
        test_article_extractor_reads_metadata_and_text,
        test_blog_extractor_reads_tags_categories_and_featured_image,
        test_fetch_policy_respects_fallback_switch,
        test_scrapling_fetch_client_returns_structured_errors,
        test_url_candidate_normalizes_core_fields,
        test_source_registry_enriches_candidates,
        test_url_frontier_enqueues_dedupes_and_dequeues,
        test_url_frontier_rejects_policy_denied_urls,
        test_url_frontier_batch_and_dead_letters,
        test_rss_connector_extracts_candidates,
        test_sitemap_connector_extracts_candidates,
        test_brave_connector_requires_key_and_maps_results,
        test_gdelt_common_crawl_youtube_and_reddit_connectors_map_results,
        test_source_registry_loads_json_config,
        test_frontier_spider_builds_news_item_with_candidate_metadata,
        test_offline_discovery_frontier_spider_pipeline_flow,
    ]

    for test in tests:
        test()
        print(f"PASS {test.__name__}")


if __name__ == "__main__":
    main()
