import scrapy
from urllib.parse import urlparse, urldefrag

from services.common.items import BlogItem
from services.scraper.surfaceweb.blog_scraper import BlogScraper
from services.scraper.fetchers import ScraplingFetchClient
from services.scraper.policy import FetchPolicy


class BlogSpider(scrapy.Spider):
    name = "blogs"

    allowed_domains = [
        "blogger.com",
        "blogspot.com",
        "medium.com",
        "tumblr.com",
        "livejournal.com",
        "crisisgroup.org",
        "csis.org",
    ]

    start_urls = [
        "https://www.blogger.com/",
        "https://medium.com/",
        "https://www.tumblr.com/",
        "https://www.livejournal.com/",
        "https://www.crisisgroup.org/cmt/global/10-conflicts-watch-2026",
        "https://www.csis.org/blogs/examining-extremism",
    ]

    custom_settings = {
        "DEPTH_LIMIT": 2,
        "DOWNLOAD_DELAY": 1,
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    skip_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
        ".pdf", ".mp4", ".mp3", ".zip", ".css", ".js",
        ".ico", ".xml", ".json"
    )

    skip_paths = (
        "/login", "/signin", "/signup", "/register",
        "/search", "/tag/", "/tags/", "/archive",
        "/about", "/contact", "/privacy", "/terms",
        "/account", "/settings", "/help",
    )

    blog_patterns = (
        "medium.com/",
        "tumblr.com/post/",
        ".tumblr.com/post/",
        "livejournal.com/",
        "blogspot.com/",
        "crisisgroup.org/",
        "csis.org/blogs/",
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

        for url in self.extract_links(response):
            if not self.is_valid_url(url):
                continue

            if self.is_blog_url(url):
                request = self.build_request(url, self.parse_blog)
            else:
                request = self.build_request(url, self.parse)

            if request:
                yield request

    def parse_blog(self, response):
        if self.crawled_pages >= self.max_pages:
            return
        self.crawled_pages += 1

        scraper = BlogScraper(response)
        data = scraper.get_data()
        data = self.maybe_refetch_blog(response, data)

        if not data.get("title") and not data.get("text"):
            return

        item = BlogItem()

        item["source_name"] = self.get_domain(response.url)
        item["source_type"] = "blog"
        item["url"] = response.url

        item["title"] = data.get("title", "")
        item["text"] = data.get("text", "")
        item["author"] = data.get("author", "")
        item["published_at"] = data.get("published_at", "")

        item["country_tags"] = []
        item["topic_tags"] = self.merge_tags(
            data.get("tags", []),
            data.get("categories", [])
        )

        item["metadata"] = {
            "status": response.status,
            "canonical_url": data.get("canonical_url", ""),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "images": data.get("images", []),
            "featured_image": data.get("featured_image", ""),
            "modified_at": data.get("modified_at", ""),
            "domain": data.get("domain", self.get_domain(response.url)),
            **data.get("provenance", {}),
        }

        yield item

    def extract_links(self, response):
        urls = set()

        for link in response.css("a::attr(href)").getall():
            url = response.urljoin(link)
            url = urldefrag(url).url.strip()

            if url:
                urls.add(url)

        return urls

    def is_valid_url(self, url):
        if not url.startswith(("http://", "https://")):
            return False

        if self.is_file_url(url):
            return False

        if self.has_skip_path(url):
            return False

        domain = self.get_domain(url)

        return any(
            domain == allowed or domain.endswith("." + allowed)
            for allowed in self.allowed_domains
        )

    def is_blog_url(self, url):
        if any(pattern in url for pattern in self.blog_patterns):
            return True

        parsed_path = urlparse(url).path.strip("/")
        parts = [part for part in parsed_path.split("/") if part]
        return len(parts) >= 2 and not self.has_skip_path(url)

    def is_file_url(self, url):
        return url.lower().endswith(self.skip_extensions)

    def has_skip_path(self, url):
        path = urlparse(url).path.lower()
        return any(skip in path for skip in self.skip_paths)

    def merge_tags(self, *tag_lists):
        tags = []
        seen = set()

        for tag_list in tag_lists:
            for tag in tag_list:
                tag = str(tag).strip()
                key = tag.lower()

                if tag and key not in seen:
                    seen.add(key)
                    tags.append(tag)

        return tags

    def build_request(self, url, callback):
        if self.scheduled_pages >= self.max_pages:
            return None

        self.scheduled_pages += 1
        return scrapy.Request(url=url, callback=callback)

    def get_domain(self, url):
        return urlparse(url).netloc.replace("www.", "")

    def maybe_refetch_blog(self, response, data):
        should_fallback, reason = self.fetch_policy.should_fallback(
            response,
            data.get("text", ""),
            self.use_scrapling_fallback,
        )

        if not should_fallback:
            return data

        result = self.fetch_client.fetch(response.url, self.scrapling_mode)
        if not result.ok:
            provenance = data.setdefault("provenance", {})
            provenance.update({
                "fallback_used": False,
                "fallback_reason": f"{reason}; fallback_failed={result.error}",
            })
            return data

        fallback_response = response.replace(
            url=result.url or response.url,
            body=result.html.encode("utf-8"),
        )
        fallback_data = BlogScraper(fallback_response).get_data()
        provenance = fallback_data.setdefault("provenance", {})
        provenance.update({
            "fetcher": result.fetcher,
            "fallback_used": True,
            "fallback_reason": reason,
        })
        return fallback_data

    def to_bool(self, value):
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
