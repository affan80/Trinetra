from services.common.text_cleaner import clean_text
from services.scraper.extractors.base import ScraplingExtractor


class ImageExtractor(ScraplingExtractor):
    extractor_version = "scrapling_image_v1"

    def get_title(self):
        return clean_text(
            self.first_css([
                "title::text",
                "h1::text",
                "meta[property='og:title']::attr(content)",
                "meta[name='twitter:title']::attr(content)",
            ])
        )

    def extract(self):
        if not self.page:
            return []

        images = []
        seen = set()

        for url in self.extract_meta_images():
            self.add_image(images, seen, url, "", "")

        for img in self.page.css("img"):
            url = self.first_image_url(img)
            if not url:
                continue

            caption = clean_text(
                " ".join(img.xpath("./ancestor::figure//figcaption//text()").getall())
            )
            self.add_image(
                images,
                seen,
                url,
                clean_text(str(img.attrib.get("alt", ""))),
                caption,
            )

        for source in self.page.css("picture source"):
            url = self.first_srcset_url(source.attrib.get("srcset", ""))
            self.add_image(images, seen, url, "", "")

        return images

    def extract_meta_images(self):
        selectors = (
            "meta[property='og:image']::attr(content)",
            "meta[property='og:image:url']::attr(content)",
            "meta[name='twitter:image']::attr(content)",
            "meta[name='twitter:image:src']::attr(content)",
        )

        for selector in selectors:
            for url in self.all_css(selector):
                if url and not url.startswith("data:image"):
                    yield url

    def add_image(self, images, seen, url, alt, caption):
        url = clean_text(url)

        if not url or url.startswith("data:image"):
            return

        absolute_url = self.urljoin(url)
        key = absolute_url.lower()

        if absolute_url and key not in seen:
            seen.add(key)
            images.append({
                "url": absolute_url,
                "alt": clean_text(alt),
                "caption": clean_text(caption),
                "source": self.url,
            })

    def first_image_url(self, img):
        for attr in ("src", "data-src", "data-original", "data-lazy-src", "data-url"):
            url = img.attrib.get(attr)
            if url:
                return url

        return self.first_srcset_url(img.attrib.get("srcset", ""))

    def first_srcset_url(self, srcset):
        if not srcset:
            return ""

        first_candidate = str(srcset).split(",")[0].strip()
        return first_candidate.split()[0] if first_candidate else ""
