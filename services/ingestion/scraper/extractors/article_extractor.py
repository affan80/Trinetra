
from services.common.date_time import parse_date
from services.common.text_cleaner import clean_text
from services.scraper.extractors.base import ScraplingExtractor


class ArticleExtractor(ScraplingExtractor):
    extractor_version = "scrapling_article_v1"

    TEXT_SELECTORS = [
        "article p::text",
        "article p *::text",
        ".article p::text",
        ".story p::text",
        ".content p::text",
        ".main-content p::text",
        ".article-body p::text",
        ".story-content p::text",
        ".post-content p::text",
        "main p::text",
        "p::text",
    ]

    BLOCKED_PHRASES = {
        "advertisement",
        "subscribe",
        "read more",
        "follow us",
        "share this",
        "click here",
        "sign up",
        "login",
        "log in",
        "copyright",
        "all rights reserved",
    }

    def __init__(self, html, url):
        super().__init__(html, url)
        self._json_ld = self.load_json_ld()

    def extract(self):
        if not self.page:
            return {}

        return {
            "title": self.get_title(),
            "text": self.get_text(),
            "author": self.get_author(),
            "published_at": self.get_published_date(),
            "description": self.get_description(),
            "canonical_url": self.get_canonical_url(),
            "language": self.get_language(),
            "keywords": self.get_keywords(),
            "images": self.get_images(),
            "domain": self.domain(),
            "json_ld": self._json_ld,
            "provenance": self.provenance(),
        }

    def get_title(self):
        return clean_text(
            self.first_css([
                "h1::text",
                "meta[property='og:title']::attr(content)",
                "meta[name='twitter:title']::attr(content)",
                "title::text",
            ])
            or self.get_json_ld_value("headline")
            or self.get_json_ld_value("name")
            or ""
        )

    def get_text(self):
        for selector in self.TEXT_SELECTORS:
            paragraphs = [
                clean_text(value)
                for value in self.all_css(selector)
                if self.is_valid_paragraph(clean_text(value))
            ]

            if len(paragraphs) >= 3:
                return clean_text(" ".join(paragraphs))

        return ""

    def is_valid_paragraph(self, paragraph):
        if not paragraph or len(paragraph) < 30:
            return False

        lower_text = paragraph.lower()
        return not any(phrase in lower_text for phrase in self.BLOCKED_PHRASES)

    def get_author(self):
        author = (
            self.first_css([
                "meta[name='author']::attr(content)",
                "meta[property='article:author']::attr(content)",
                "[rel='author']::text",
                ".author::text",
                ".byline::text",
                ".article-author::text",
                ".story-author::text",
            ])
            or self.get_json_ld_author()
            or ""
        )

        author = clean_text(author)
        return clean_text(author.removeprefix("By ").removeprefix("by "))

    def get_json_ld_author(self):
        author = self.get_json_ld_value("author")

        if isinstance(author, str):
            return author
        if isinstance(author, dict):
            return author.get("name", "")
        if isinstance(author, list):
            return ", ".join(
                item.get("name", "") if isinstance(item, dict) else str(item)
                for item in author
                if item
            )

        return ""

    def get_published_date(self):
        date_text = (
            self.first_css([
                "time::attr(datetime)",
                "time::text",
                "meta[property='article:published_time']::attr(content)",
                "meta[name='pubdate']::attr(content)",
                "meta[name='publishdate']::attr(content)",
                "meta[name='date']::attr(content)",
            ])
            or self.get_json_ld_value("datePublished")
            or ""
        )

        return parse_date(date_text)

    def get_description(self):
        return clean_text(
            self.first_css([
                "meta[name='description']::attr(content)",
                "meta[property='og:description']::attr(content)",
                "meta[name='twitter:description']::attr(content)",
            ])
            or self.get_json_ld_value("description")
            or ""
        )

    def get_canonical_url(self):
        url = self.first_css([
            "link[rel='canonical']::attr(href)",
            "meta[property='og:url']::attr(content)",
        ])

        return self.urljoin(url or self.url)

    def get_language(self):
        return self.first_css([
            "html::attr(lang)",
            "meta[property='og:locale']::attr(content)",
        ])

    def get_keywords(self):
        keywords = []
        seen = set()
        keyword_text = self.first_css([
            "meta[name='keywords']::attr(content)",
            "meta[property='article:tag']::attr(content)",
        ])

        for keyword in keyword_text.split(","):
            self.unique_add(keywords, seen, keyword)

        json_keywords = self.get_json_ld_value("keywords")
        if isinstance(json_keywords, str):
            json_keywords = json_keywords.split(",")
        if isinstance(json_keywords, list):
            for keyword in json_keywords:
                self.unique_add(keywords, seen, keyword)

        return keywords

    def get_images(self):
        images = []
        seen = set()
        candidates = [
            self.first_css(["meta[property='og:image']::attr(content)"]),
            self.first_css(["meta[name='twitter:image']::attr(content)"]),
        ]
        json_image = self.get_json_ld_value("image")

        if isinstance(json_image, str):
            candidates.append(json_image)
        elif isinstance(json_image, dict):
            candidates.append(json_image.get("url", ""))
        elif isinstance(json_image, list):
            for image in json_image:
                if isinstance(image, str):
                    candidates.append(image)
                elif isinstance(image, dict):
                    candidates.append(image.get("url", ""))

        for selector in [
            "article img::attr(src)",
            "article img::attr(data-src)",
            ".article img::attr(src)",
            ".article img::attr(data-src)",
        ]:
            candidates.extend(self.all_css(selector))

        for image in candidates:
            if image and not image.startswith("data:image"):
                self.unique_add(images, seen, self.urljoin(image))

        return images

    def get_json_ld_value(self, key):
        for data in self._json_ld:
            value = self.find_key_recursive(data, key)
            if value:
                return value
        return None

    def get_article_types(self):
        article_types = []

        for data in self._json_ld:
            value = self.find_key_recursive(data, "@type")
            if isinstance(value, str):
                article_types.append(value)
            elif isinstance(value, list):
                article_types.extend(str(item) for item in value)

        return article_types

    def is_article_like(self):
        article_types = {value.lower() for value in self.get_article_types()}
        if article_types.intersection({"newsarticle", "article", "blogposting"}):
            return True

        if self.first_css(["meta[property='article:published_time']::attr(content)"]):
            return True

        return len(self.get_text()) >= 250
