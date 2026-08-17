from urllib.parse import urlparse
from services.common.text_cleaner import clean_text
from services.scraper.extractors.image_extractor import ImageExtractor

class ImageScraper:
    def __init__(self, response):
        self.response = response
        self.extractor = ImageExtractor(response.text, response.url)

    def get_title(self):
        if self.extractor.available:
            return self.extractor.get_title()

        return clean_text(
            self.response.css("title::text").get()
            or self.response.css("h1::text").get()
            or self.response.css("meta[property='og:title']::attr(content)").get()
            or ""
        )

    def get_domain(self):
        return urlparse(self.response.url).netloc.replace("www.", "")

    def get_provenance(self):
        return self.extractor.provenance() if self.extractor.available else {
            "scraper_engine": "scrapy",
            "parser_engine": "scrapy",
            "fetcher": "scrapy",
            "fallback_used": False,
            "fallback_reason": "",
            "extractor_version": "legacy_image_v1",
        }

    def extract_images(self):
        """Extract images with metadata (alt, caption, source)."""
        if self.extractor.available:
            yield from self.extractor.extract()
            return

        seen = set()

        for url in self.extract_meta_images():
            if url in seen:
                continue
            seen.add(url)
            yield {
                "url": url,
                "alt": "",
                "caption": "",
                "source": self.response.url
            }

        for img in self.response.css("img"):
            url = self.first_image_url(img)
            if not url or url.startswith("data:image"):
                continue

            url = self.response.urljoin(url)
            if url in seen:
                continue
            seen.add(url)
            
            yield {
                "url": url,
                "alt": clean_text(img.css("::attr(alt)").get() or ""),
                "caption": clean_text(" ".join(img.xpath("./ancestor::figure//figcaption//text()").getall())),
                "source": self.response.url
            }

        for source in self.response.css("picture source"):
            url = self.first_srcset_url(source.css("::attr(srcset)").get())
            if not url or url.startswith("data:image"):
                continue

            url = self.response.urljoin(url)
            if url in seen:
                continue
            seen.add(url)
            yield {
                "url": url,
                "alt": "",
                "caption": "",
                "source": self.response.url
            }

    def extract_meta_images(self):
        selectors = (
            "meta[property='og:image']::attr(content)",
            "meta[property='og:image:url']::attr(content)",
            "meta[name='twitter:image']::attr(content)",
            "meta[name='twitter:image:src']::attr(content)",
        )

        for selector in selectors:
            for url in self.response.css(selector).getall():
                url = clean_text(url)
                if url and not url.startswith("data:image"):
                    yield self.response.urljoin(url)

    def first_image_url(self, img):
        for attr in ("src", "data-src", "data-original", "data-lazy-src", "data-url"):
            url = img.css(f"::attr({attr})").get()
            if url:
                return url

        return self.first_srcset_url(img.css("::attr(srcset)").get())

    def first_srcset_url(self, srcset):
        if not srcset:
            return ""

        first_candidate = srcset.split(",")[0].strip()
        return first_candidate.split()[0] if first_candidate else ""
