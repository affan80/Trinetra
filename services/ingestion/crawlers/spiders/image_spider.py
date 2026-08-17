import scrapy
from urllib.parse import urlparse, urldefrag
from services.common.items import ImageItem
from services.scraper.surfaceweb.image_scraper import ImageScraper
from services.scraper.fetchers import ScraplingFetchClient
from services.scraper.policy import FetchPolicy

class ImageSpider(scrapy.Spider):
    name = "images"
    
    custom_settings = {
        "DEPTH_LIMIT": 2,
        "DOWNLOAD_DELAY": 0.5,
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 16,
        "AUTOTHROTTLE_ENABLED": True,
    }

    skip_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".mp4", ".zip", ".css", ".js", ".ico")
    skip_paths = ("/login", "/signin", "/signup", "/register", "/privacy", "/terms", "/search")

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
        if not urls:
            raise ValueError("Pass URLs like: -a urls=https://example.com")
        
        self.start_urls = [u.strip() for u in urls.split(",") if u.strip()]
        self.allowed_domains = [d.strip().replace("www.", "") for d in (domains or "").split(",") if d.strip()]
        self.max_pages = int(max_pages)
        self.crawled_pages = 0
        self.scheduled_pages = 0
        self.seen_images = set()
        self.use_scrapling_fallback = self.to_bool(use_scrapling_fallback)
        self.scrapling_mode = scrapling_mode
        self.fetch_policy = FetchPolicy()
        self.fetch_client = ScraplingFetchClient()

        if not self.allowed_domains:
            self.allowed_domains = [urlparse(u).netloc.replace("www.", "") for u in self.start_urls]
        
        self.allowed_domains_set = set(self.allowed_domains)

    def start_requests(self):
        for url in self.start_urls:
            request = self.build_request(url)
            if request:
                yield request

    def parse(self, response):
        if self.crawled_pages >= self.max_pages:
            return

        self.crawled_pages += 1
        scraper = ImageScraper(response)
        response, scraper, fallback_metadata = self.maybe_refetch(response, scraper)
        domain = scraper.get_domain()
        page_title = scraper.get_title()
        provenance = scraper.get_provenance()
        provenance.update(fallback_metadata)

        for image in scraper.extract_images():
            if image["url"] not in self.seen_images:
                self.seen_images.add(image["url"])
                yield self.build_item(response, domain, page_title, image, provenance)

        # Logarithmic logging: log at 1, 2, 4, 8, 16... pages
        if (self.crawled_pages & (self.crawled_pages - 1) == 0):
            self.logger.info(f"Progress: Crawled {self.crawled_pages} pages, found {len(self.seen_images)} unique images")

        for link in response.css("a::attr(href)").getall():
            url = urldefrag(response.urljoin(link)).url.strip()
            request = self.build_request(url)
            if request:
                yield request

    def build_item(self, response, domain, page_title, image, provenance):
        return ImageItem(
            source_name=domain,
            source_type="image",
            page_url=response.url,
            image_url=image["url"],
            image_urls=[image["url"]],
            images=[],
            title=page_title,
            alt=image["alt"],
            caption=image["caption"],
            metadata={
                "status": response.status,
                "domain": domain,
                **provenance,
            }
        )

    def build_request(self, url):
        if self.scheduled_pages >= self.max_pages or not self.is_valid_url(url):
            return None

        self.scheduled_pages += 1
        return scrapy.Request(url, callback=self.parse)

    def is_valid_url(self, url):
        if not url.startswith(("http://", "https://")) or url.lower().endswith(self.skip_extensions):
            return False
        path = urlparse(url).path.lower()
        if any(skip in path for skip in self.skip_paths):
            return False
        domain = urlparse(url).netloc.replace("www.", "")
        return any(domain == d or domain.endswith("." + d) for d in self.allowed_domains_set)

    def maybe_refetch(self, response, scraper):
        if not self.fetch_policy.fallback_enabled(self.use_scrapling_fallback):
            return response, scraper, {}

        images = list(scraper.extract_images())
        should_fallback, reason = self.fetch_policy.should_fallback(
            response,
            " ".join(image.get("alt", "") for image in images),
            self.use_scrapling_fallback,
        )

        if not should_fallback:
            # Rebuild scraper so parse can stream images normally.
            return response, ImageScraper(response), {}

        result = self.fetch_client.fetch(response.url, self.scrapling_mode)
        if not result.ok:
            return response, ImageScraper(response), {
                "fallback_used": False,
                "fallback_reason": f"{reason}; fallback_failed={result.error}",
            }

        fallback_response = response.replace(
            url=result.url or response.url,
            body=result.html.encode("utf-8"),
        )
        return fallback_response, ImageScraper(fallback_response), {
            "fetcher": result.fetcher,
            "fallback_used": True,
            "fallback_reason": reason,
        }

    def to_bool(self, value):
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
