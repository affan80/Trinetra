import re

from services.common.date_time import parse_date
from services.common.text_cleaner import clean_text
from services.scraper.extractors.article_extractor import ArticleExtractor


class BlogExtractor(ArticleExtractor):
    extractor_version = "scrapling_blog_v1"

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

    def extract(self):
        data = super().extract()

        if not data:
            return {}

        data["modified_at"] = self.get_modified_date()
        data["tags"] = self.get_tags()
        data["categories"] = self.get_categories()
        data["featured_image"] = data["images"][0] if data.get("images") else ""
        data["provenance"] = self.provenance()
        return data

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

        author = re.sub(r"^by\s+", "", clean_text(author), flags=re.IGNORECASE)
        return clean_text(author)

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
            for tag in self.all_css(selector):
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
            for category in self.all_css(selector):
                self.unique_add(categories, seen, category)

        section = self.get_json_ld_value("articleSection")
        if isinstance(section, str):
            section = [section]
        if isinstance(section, list):
            for category in section:
                self.unique_add(categories, seen, category)

        return categories
