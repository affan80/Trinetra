import scrapy
from urllib.parse import urlparse, urldefrag

# Updated imports to use local package structure
from services.common.items import NewsItem
from services.scraper.surfaceweb.news_scraper import NewsScraper


class NewsSpider(scrapy.Spider):
    name = "news"

    allowed_domains = [
        "bbc.com",
        "aljazeera.com",
        "youtube.com",
    ]

    start_urls = [
        "https://www.bbc.com/",
        "https://www.aljazeera.com/",
        "https://www.youtube.com/",
    ]

    custom_settings = {
        "DEPTH_LIMIT": 2,
        "DOWNLOAD_DELAY": 1,
        "ROBOTSTXT_OBEY": True,
    }

    article_paths = [
        "bbc.com/news",
        "bbc.com/news/articles",
        "aljazeera.com/news",
        "aljazeera.com/features",
        "aljazeera.com/economy",
        "aljazeera.com/sports",
    ]

    skip_extensions = (
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".pdf", ".mp4", ".mp3", ".zip", ".css", ".js"
    )

    def parse(self, response):
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
                    yield scrapy.Request(
                        url=full_url,
                        callback=self.parse_youtube_video
                    )
                continue

            # If it looks like a news article, scrape article data
            if self.is_article_url(full_url):
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse_article
                )
            else:
                # Continue finding more links from category/home pages
                yield scrapy.Request(
                    url=full_url,
                    callback=self.parse
                )

    def parse_article(self, response):
        scraper = NewsScraper(response)
        article_data = scraper.get_data()

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
        }

        yield item

    def parse_youtube_video(self, response):
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

        return False

    def is_youtube_url(self, url):
        domain = self.get_domain(url)
        return "youtube.com" in domain

    def is_file_url(self, url):
        lower_url = url.lower()
        return lower_url.endswith(self.skip_extensions)

    def get_domain(self, url):
        return urlparse(url).netloc.replace("www.", "")
      if netloc.startswith("www."):
            return netloc[4:]
        return netloc
