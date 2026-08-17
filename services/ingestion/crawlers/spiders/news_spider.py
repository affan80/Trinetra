import scrapy
from urllib.parse import urlparse, urldefrag

# Updated imports to use local package structure
from services.common.items import NewsItem
from services.scraper.surfaceweb.news_scraper import NewsScraper
from services.scraper.fetchers import ScraplingFetchClient
from services.scraper.policy import FetchPolicy


class NewsSpider(scrapy.Spider):
    name = "news"

    allowed_domains = [
        "bbc.com",
        "aljazeera.com",
    ]

    start_urls = [
        "https://www.bbc.com/",
        "https://www.aljazeera.com/",
    ]

    custom_settings = {
        "DEPTH_LIMIT": 5,
        "DOWNLOAD_DELAY": 0.5,
        "ROBOTSTXT_OBEY": False,
        "CONCURRENT_REQUESTS": 16,
        "USER_AGENT": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    }

    article_paths = [
        "bbc.com/news",
        "bbc.com/news/articles",
        "bbc.com/sport",
        "aljazeera.com/news",
        "aljazeera.com/features",
        "aljazeera.com/economy",
        "aljazeera.com/sports",
        "aljazeera.com/opinion",
        "aljazeera.com/video",
    ]

    skip_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".pdf", ".mp4", ".mp3", ".zip", ".css", ".js"
    )

    def __init__(
        self,
        urls=None,
        domains=None,
        max_pages=100,
        use_scrapling_fallback=False,
        scrapling_mode=None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        if urls:
            self.start_urls = [u.strip() for u in urls.split(",") if u.strip()]
        
        if domains:
            self.allowed_domains = [d.strip().replace("www.", "") for d in domains.split(",") if d.strip()]
        elif urls:
            self.allowed_domains = [urlparse(u).netloc.replace("www.", "") for u in self.start_urls]
            
        self.max_pages = int(max_pages)
        self.crawled_pages = 0
        self.scheduled_pages = 0
        self.use_scrapling_fallback = self.to_bool(use_scrapling_fallback)
        self.scrapling_mode = scrapling_mode
        self.fetch_policy = FetchPolicy()
        self.fetch_client = ScraplingFetchClient()

    def start_requests(self):
        for url in self.start_urls:
            request = self.build_request(url, self.parse)
            if request:
                yield request

    def parse(self, response):
        if self.crawled_pages >= self.max_pages:
            return
        self.crawled_pages += 1

        links = response.css("a::attr(href)").getall()

        for link in links:
            full_url = response.urljoin(link)
            full_url = urldefrag(full_url).url

            if not self.is_allowed_url(full_url):
                continue

            if self.is_file_url(full_url):
                continue

            # YouTube is not a normal article page
            if self.is_youtube_url(full_url):
                if "/watch" in full_url or "/shorts/" in full_url:
                    request = self.build_request(full_url, self.parse_youtube_video)
                    if request:
                        yield request
                continue

            # If it looks like a news article, scrape article data
            if self.is_article_url(full_url):
                request = self.build_request(full_url, self.parse_article)
            else:
                # Continue finding more links from category/home pages
                request = self.build_request(full_url, self.parse)

            if request:
                yield request

    def parse_article(self, response):
        if self.crawled_pages >= self.max_pages:
            return
        self.crawled_pages += 1

        scraper = NewsScraper(response)
        article_data = scraper.get_data()
        article_data = self.maybe_refetch_article(response, article_data)

        item = NewsItem()

        item["source_name"] = self.get_domain(response.url)
        item["source_type"] = "news"
        item["url"] = response.url

        item["title"] = article_data.get("title", "")
        item["text"] = article_data.get("text", "")
        item["author"] = article_data.get("author", "")
        item["published_at"] = article_data.get("published_at", "")

        item["country_tags"] = []
        item["topic_tags"] = article_data.get("keywords", [])

        item["metadata"] = {
            "status": response.status,
            "canonical_url": article_data.get("canonical_url", ""),
            "description": article_data.get("description", ""),
            "language": article_data.get("language", ""),
            "images": article_data.get("images", []),
            "domain": article_data.get("domain", self.get_domain(response.url)),
            **article_data.get("provenance", {}),
        }

        yield item

    def parse_youtube_video(self, response):
        if self.crawled_pages >= self.max_pages:
            return
        self.crawled_pages += 1

        item = NewsItem()

        title = (
            response.css("meta[property='og:title']::attr(content)").get()
            or response.css("title::text").get()
            or ""
        )

        description = (
            response.css("meta[property='og:description']::attr(content)").get()
            or response.css("meta[name='description']::attr(content)").get()
            or ""
        )

        image = response.css("meta[property='og:image']::attr(content)").get()

        item["source_name"] = "youtube.com"
        item["source_type"] = "video"
        item["url"] = response.url
        item["title"] = title
        item["text"] = description
        item["author"] = ""
        item["published_at"] = ""

        item["country_tags"] = []
        item["topic_tags"] = []

        item["metadata"] = {
            "status": response.status,
            "canonical_url": response.url,
            "description": description,
            "language": "",
            "images": [image] if image else [],
            "domain": "youtube.com",
        }

        yield item

    def is_allowed_url(self, url):
        domain = self.get_domain(url)

        for allowed_domain in self.allowed_domains:
            if domain == allowed_domain or domain.endswith("." + allowed_domain):
                return True

        return False

    def is_article_url(self, url):
        for path in self.article_paths:
            if path in url:
                return True

        parsed_path = urlparse(url).path.strip("/")
        parts = [part for part in parsed_path.split("/") if part]
        return len(parts) >= 2 and not parsed_path.lower().startswith((
            "tag",
            "tags",
            "search",
            "privacy",
            "terms",
            "about",
            "contact",
        ))

    def is_youtube_url(self, url):
        domain = self.get_domain(url)
        return "youtube.com" in domain

    def is_file_url(self, url):
        lower_url = url.lower()
        return lower_url.endswith(self.skip_extensions)

    def get_domain(self, url):
        return urlparse(url).netloc.replace("www.", "")

    def build_request(self, url, callback):
        if self.scheduled_pages >= self.max_pages:
            return None

        self.scheduled_pages += 1
        return scrapy.Request(url=url, callback=callback)

    def maybe_refetch_article(self, response, article_data):
        should_fallback, reason = self.fetch_policy.should_fallback(
            response,
            article_data.get("text", ""),
            self.use_scrapling_fallback,
        )

        if not should_fallback:
            return article_data

        result = self.fetch_client.fetch(response.url, self.scrapling_mode)
        if not result.ok:
            provenance = article_data.setdefault("provenance", {})
            provenance.update({
                "fallback_used": False,
                "fallback_reason": f"{reason}; fallback_failed={result.error}",
            })
            return article_data

        fallback_response = response.replace(
            url=result.url or response.url,
            body=result.html.encode("utf-8"),
        )
        fallback_data = NewsScraper(fallback_response).get_data()
        provenance = fallback_data.setdefault("provenance", {})
        provenance.update({
            "fetcher": result.fetcher,
            "fallback_used": True,
            "fallback_reason": reason,
        })
        return fallback_data

    def to_bool(self, value):
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
