import scrapy
from urllib.parse import urlparse
from services.common.text_cleaner import clean_text

class ImageScraper:
    def __init__(self, response):
        self.response = response

    def get_title(self):
        title = (
            self.response.css("title::text").get()
            or self.response.css("h1::text").get()
            or self.response.css("meta[property='og:title']::attr(content)").get()
            or ""
        )
        return clean_text(title)

    def get_domain(self):
        return urlparse(self.response.url).netloc.replace("www.", "")

    def extract_images(self):
        """Extract images with metadata (alt, caption, source)."""
        for img in self.response.css("img"):
            url = img.css("::attr(src)").get()
            if not url or url.startswith("data:image"):
                continue
            
            yield {
                "url": self.response.urljoin(url),
                "alt": clean_text(img.css("::attr(alt)").get() or ""),
                "caption": clean_text(img.xpath("./ancestor::figure//figcaption/text()").get() or ""),
                "source": self.response.url
            }
