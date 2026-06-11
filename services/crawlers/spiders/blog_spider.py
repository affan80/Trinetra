import scrapy
from urllib.parse import urlparse, urldefrag

from services.common.items import BlogItem
from services.scraper.surfaceweb.blog_scraper import BlogScraper


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

    def parse(self, response):
        for url in self.extract_links(response):
            if not self.is_valid_url(url):
                continue

            if self.is_blog_url(url):
                yield scrapy.Request(url, callback=self.parse_blog)
            else:
                yield scrapy.Request(url, callback=self.parse)

    def parse_blog(self, response):
        scraper = BlogScraper(response)
        data = scraper.get_blog_data()

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
        return any(pattern in url for pattern in self.blog_patterns)

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

    def get_domain(self, url):
        return urlparse(url).netloc.replace("www.", "")
