import json
import re

# Updated imports to use local package structure
from services.common.text_cleaner import clean_text
from services.common.date_time import parse_date


class NewsScraper:
    def __init__(self, response):
        self.response = response

    # 1. Extract title
    def get_title(self):
        title = (
            self.response.css("h1::text").get()
            or self.response.css("meta[property='og:title']::attr(content)").get()
            or self.response.css("meta[name='twitter:title']::attr(content)").get()
            or self.response.css("title::text").get()
            or ""
        )

        return clean_text(title)

    # 2. Extract article body text
    def get_text(self):
        selectors = [
            "article p::text",
            "article p *::text",
            ".article p::text",
            ".story p::text",
            ".content p::text",
            ".main-content p::text",
            ".article-body p::text",
            ".story-content p::text",
            ".post-content p::text",
            "p::text",
        ]

        all_paragraphs = []

        for selector in selectors:
            paragraphs = self.response.css(selector).getall()

            cleaned_paragraphs = []

            for paragraph in paragraphs:
                paragraph = clean_text(paragraph)

                if self.is_valid_paragraph(paragraph):
                    cleaned_paragraphs.append(paragraph)

            if len(cleaned_paragraphs) >= 3:
                all_paragraphs = cleaned_paragraphs
                break

        article_text = " ".join(all_paragraphs)

        return clean_text(article_text)

    def is_valid_paragraph(self, paragraph):
        if not paragraph:
            return False

        if len(paragraph) < 30:
            return False

        blocked_phrases = [
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
        ]

        lower_text = paragraph.lower()

        for phrase in blocked_phrases:
            if phrase in lower_text:
                return False

        return True

    # 3. Extract author
    def get_author(self):
        author = (
            self.response.css("meta[name='author']::attr(content)").get()
            or self.response.css("[rel='author']::text").get()
            or self.response.css(".author::text").get()
            or self.response.css(".byline::text").get()
            or self.response.css(".article-author::text").get()
            or self.response.css(".story-author::text").get()
            or ""
        )

        author = clean_text(author)

        author = author.replace("By ", "")
        author = author.replace("by ", "")

        return clean_text(author)

    # 4. Extract published date
    def get_published_date(self):
        date_text = (
            self.response.css("time::attr(datetime)").get()
            or self.response.css("time::text").get()
            or self.response.css("meta[property='article:published_time']::attr(content)").get()
            or self.response.css("meta[name='pubdate']::attr(content)").get()
            or self.response.css("meta[name='publishdate']::attr(content)").get()
            or self.response.css("meta[name='date']::attr(content)").get()
            or self.get_date_from_json_ld()
            or ""
        )

        return parse_date(date_text)

    def get_date_from_json_ld(self):
        scripts = self.response.css("script[type='application/ld+json']::text").getall()

        for script in scripts:
            try:
                data = json.loads(script.strip())

                if isinstance(data, dict):
                    date_value = self.find_key_recursive(data, "datePublished")
                    if date_value:
                        return date_value

                if isinstance(data, list):
                    for obj in data:
                        if isinstance(obj, dict):
                            date_value = self.find_key_recursive(obj, "datePublished")
                            if date_value:
                                return date_value

            except Exception:
                continue

        return None

    # 5. Extract description / summary
    def get_description(self):
        """
        Extract article summary or meta description.
        """

        description = (
            self.response.css("meta[name='description']::attr(content)").get()
            or self.response.css("meta[property='og:description']::attr(content)").get()
            or self.response.css("meta[name='twitter:description']::attr(content)").get()
            or ""
        )

        return clean_text(description)

    # 6. Extract canonical URL
    def get_canonical_url(self):
        canonical_url = (
            self.response.css("link[rel='canonical']::attr(href)").get()
            or self.response.css("meta[property='og:url']::attr(content)").get()
            or self.response.url
        )

        return self.response.urljoin(clean_text(canonical_url))

    # 7. Extract language
    def get_language(self):
        language = (
            self.response.css("html::attr(lang)").get()
            or self.response.css("meta[property='og:locale']::attr(content)").get()
            or ""
        )

        return clean_text(language)

    # 8. Extract keywords
    def get_keywords(self):
        keyword_text = (
            self.response.css("meta[name='keywords']::attr(content)").get()
            or self.response.css("meta[property='article:tag']::attr(content)").get()
            or ""
        )

        keyword_text = clean_text(keyword_text)

        if not keyword_text:
            return []

        keywords = keyword_text.split(",")

        cleaned_keywords = []

        for keyword in keywords:
            keyword = clean_text(keyword)
            if keyword:
                cleaned_keywords.append(keyword)

        return cleaned_keywords

    # 9. Extract image URLs
    def get_images(self):
        image_urls = []

        og_image = self.response.css("meta[property='og:image']::attr(content)").get()

        if og_image:
            image_urls.append(self.response.urljoin(og_image))

        article_images = self.response.css("article img::attr(src), .article img::attr(src)").getall()

        for image in article_images:
            full_image_url = self.response.urljoin(image)

            if full_image_url not in image_urls:
                image_urls.append(full_image_url)

        return image_urls

    # 10. Extract source domain
    def get_domain(self):
        return self.response.url.split("/")[2] if "://" in self.response.url else ""

    # 11. Extract JSON-LD data
    def get_json_ld(self):
        json_ld_data = []

        scripts = self.response.css("script[type='application/ld+json']::text").getall()

        for script in scripts:
            try:
                data = json.loads(script.strip())
                json_ld_data.append(data)
            except Exception:
                continue

        return json_ld_data

    # 12. Helper: recursive key finder
    def find_key_recursive(self, data, target_key):
        """
        Recursively search for a key inside dictionary/list JSON data.
        """

        if isinstance(data, dict):
            for key, value in data.items():
                if key == target_key:
                    return value

                result = self.find_key_recursive(value, target_key)
                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self.find_key_recursive(item, target_key)
                if result:
                    return result

        return None

    # 13. Return all extracted data together
    def get_data(self):
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
            "domain": self.get_domain(),
            "json_ld": self.get_json_ld(),
        }

    def get_article_data(self):
        return self.get_data()
