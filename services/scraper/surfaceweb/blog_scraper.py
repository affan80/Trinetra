import json
import re
from urllib.parse import urlparse

from services.common.text_cleaner import clean_text
from services.common.date_time import parse_date


class BlogScraper:
    BLOCKED_PHRASES = {
        "advertisement", "subscribe", "newsletter", "read more",
        "related posts", "related articles", "you may also like",
        "share this", "share on", "follow us", "follow me",
        "sign up", "login", "log in", "leave a comment",
        "post a comment", "comments", "cookie policy",
        "privacy policy", "terms of service", "all rights reserved",
        "copyright",
    }

    TEXT_SELECTORS = [
        "article .entry-content *::text",
        "article .post-content *::text",
        "article .blog-content *::text",
        "article .content *::text",
        ".entry-content *::text",
        ".post-content *::text",
        ".blog-post-content *::text",
        ".blog-content *::text",
        ".single-post-content *::text",
        ".article-content *::text",
        ".content-area article *::text",
        "article *::text",
        "main *::text",
    ]

    def __init__(self, response):
        self.response = response
        self._json_ld = self._load_json_ld()

    def first_css(self, selectors):
        for selector in selectors:
            value = self.response.css(selector).get()
            if value:
                return value
        return ""

    def unique_add(self, items, seen, value):
        value = clean_text(str(value))
        key = value.lower()

        if value and key not in seen:
            seen.add(key)
            items.append(value)

    def get_title(self):
        return clean_text(
            self.first_css([
                "h1.entry-title::text",
                "h1.post-title::text",
                "h1.blog-title::text",
                "article h1::text",
                "main h1::text",
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
            parts = [
                clean_text(part)
                for part in self.response.css(selector).getall()
            ]

            parts = [
                part for part in parts
                if self.is_valid_content_text(part)
            ]

            if len(parts) >= 1:
                return clean_text(" ".join(parts))

        return ""

    def is_valid_content_text(self, text):
        if not text or len(text) < 20:
            return False

        text = text.lower()
        return not any(phrase in text for phrase in self.BLOCKED_PHRASES)

    def get_author(self):
        author = (
            self.first_css([
                "meta[name='author']::attr(content)",
                "meta[property='article:author']::attr(content)",
                "[rel='author']::text",
                ".author-name::text",
                ".post-author::text",
                ".blog-author::text",
                ".entry-author::text",
                ".byline .author::text",
                ".byline::text",
            ])
            or self.get_json_ld_author()
            or ""
        )

        author = re.sub(r"^by\s+", "", clean_text(author), flags=re.I)
        return clean_text(author)

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
                "time.published::attr(datetime)",
                ".published::attr(datetime)",
                ".post-date::attr(datetime)",
                ".entry-date::attr(datetime)",
                "time::text",
                ".published::text",
                ".post-date::text",
                ".entry-date::text",
                "meta[property='article:published_time']::attr(content)",
                "meta[name='pubdate']::attr(content)",
                "meta[name='publishdate']::attr(content)",
                "meta[name='date']::attr(content)",
            ])
            or self.get_json_ld_value("datePublished")
            or ""
        )

        return parse_date(date_text)

    def get_modified_date(self):
        date_text = (
            self.first_css([
                "time.updated::attr(datetime)",
                ".updated::attr(datetime)",
                "meta[property='article:modified_time']::attr(content)",
                "meta[name='lastmod']::attr(content)",
                "meta[name='last-modified']::attr(content)",
            ])
            or self.get_json_ld_value("dateModified")
            or ""
        )

        return parse_date(date_text)

    def get_description(self):
        return clean_text(
            self.first_css([
                "meta[name='description']::attr(content)",
                "meta[property='og:description']::attr(content)",
                "meta[name='twitter:description']::attr(content)",
                ".entry-summary::text",
                ".post-excerpt::text",
                ".blog-excerpt::text",
            ])
            or self.get_json_ld_value("description")
            or ""
        )

    def get_canonical_url(self):
        url = self.first_css([
            "link[rel='canonical']::attr(href)",
            "meta[property='og:url']::attr(content)",
        ])

        return self.response.urljoin(url or self.response.url)

    def get_language(self):
        return self.first_css([
            "html::attr(lang)",
            "meta[property='og:locale']::attr(content)",
        ])

    def get_tags(self):
        tags = []
        seen = set()

        keywords = self.first_css(["meta[name='keywords']::attr(content)"])

        for tag in keywords.split(","):
            self.unique_add(tags, seen, tag)

        for selector in [
            ".tags a::text",
            ".post-tags a::text",
            ".entry-tags a::text",
            ".tag-links a::text",
            "a[rel='tag']::text",
        ]:
            for tag in self.response.css(selector).getall():
                self.unique_add(tags, seen, tag)

        json_keywords = self.get_json_ld_value("keywords")

        if isinstance(json_keywords, str):
            json_keywords = json_keywords.split(",")

        if isinstance(json_keywords, list):
            for tag in json_keywords:
                self.unique_add(tags, seen, tag)

        return tags

    def get_categories(self):
        categories = []
        seen = set()

        for selector in [
            ".category a::text",
            ".categories a::text",
            ".post-categories a::text",
            ".entry-categories a::text",
            ".cat-links a::text",
            "a[rel='category tag']::text",
        ]:
            for category in self.response.css(selector).getall():
                self.unique_add(categories, seen, category)

        section = self.get_json_ld_value("articleSection")

        if isinstance(section, str):
            section = [section]

        if isinstance(section, list):
            for category in section:
                self.unique_add(categories, seen, category)

        return categories

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
            ".entry-content img::attr(src)",
            ".entry-content img::attr(data-src)",
            ".post-content img::attr(src)",
            ".post-content img::attr(data-src)",
            ".blog-content img::attr(src)",
            ".blog-content img::attr(data-src)",
        ]:
            candidates.extend(self.response.css(selector).getall())

        for image in candidates:
            image = clean_text(image)
            if image:
                full_url = self.response.urljoin(image)
                self.unique_add(images, seen, full_url)

        return images

    def get_featured_image(self):
        images = self.get_images()
        return images[0] if images else ""

    def get_domain(self):
        return urlparse(self.response.url).netloc.replace("www.", "")

    def _load_json_ld(self):
        data = []

        scripts = self.response.css(
            "script[type='application/ld+json']::text"
        ).getall()

        for script in scripts:
            try:
                script = script.strip()
                if script:
                    data.append(json.loads(script))
            except Exception:
                continue

        return data

    def get_json_ld(self):
        return self._json_ld

    def get_json_ld_value(self, key):
        for data in self._json_ld:
            value = self.find_key_recursive(data, key)
            if value:
                return value
        return None

    def find_key_recursive(self, data, target_key):
        if isinstance(data, dict):
            if target_key in data:
                return data[target_key]

            for value in data.values():
                result = self.find_key_recursive(value, target_key)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self.find_key_recursive(item, target_key)
                if result:
                    return result

        return None

    def get_blog_data(self):
        images = self.get_images()

        return {
            "title": self.get_title(),
            "text": self.get_text(),
            "author": self.get_author(),
            "published_at": self.get_published_date(),
            "modified_at": self.get_modified_date(),
            "description": self.get_description(),
            "canonical_url": self.get_canonical_url(),
            "language": self.get_language(),
            "tags": self.get_tags(),
            "categories": self.get_categories(),
            "images": images,
            "featured_image": images[0] if images else "",
            "domain": self.get_domain(),
            "json_ld": self.get_json_ld(),
        }

    def get_data(self):
        return self.get_blog_data()

    def get_article_data(self):
        return self.get_blog_data()
