from __future__ import annotations

import os
from urllib.parse import urlparse

import scrapy
from services.common.items import BlogItem, ImageItem, NewsItem
from services.scraper.discovery import UrlCandidate
from services.scraper.fetchers import ScraplingFetchClient
from services.scraper.policy import FetchPolicy, SourcePolicy
from services.scraper.surfaceweb.blog_scraper import BlogScraper
from services.scraper.surfaceweb.image_scraper import ImageScraper
from services.scraper.surfaceweb.news_scraper import NewsScraper
from services.shared.redis_metrics import RedisMetrics
from services.shared.url_frontier import UrlFrontier


class FrontierSpider(scrapy.Spider):
    name = "frontier"

    custom_settings = {
        "DEPTH_LIMIT": 1,
        "DOWNLOAD_DELAY": 1,
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def __init__(
        self,
        batch_size=None,
        frontier=None,
        source_policy=None,
        use_scrapling_fallback=False,
        scrapling_mode=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.batch_size = int(batch_size or os.getenv("FRONTIER_BATCH_SIZE", 25))
        self.frontier = frontier or UrlFrontier(metrics=RedisMetrics())
        self.source_policy = source_policy or SourcePolicy()
        self.use_scrapling_fallback = self.to_bool(use_scrapling_fallback)
        self.scrapling_mode = scrapling_mode
        self.fetch_policy = FetchPolicy()
        self.fetch_client = ScraplingFetchClient()

    def start_requests(self):
        candidates = self.frontier.dequeue_many(self.batch_size)
        if not candidates:
            self.logger.info("No candidates available in URL frontier")
            return

        for candidate_data in candidates:
            candidate = UrlCandidate.from_dict(candidate_data)
            if not candidate.is_web_url():
                self.frontier.move_to_dead_letter(candidate.to_dict(), reason="invalid_web_url")
                continue

            if not self.source_policy.is_allowed(candidate.url):
                self.frontier.move_to_dead_letter(candidate.to_dict(), reason="source_policy_rejected")
                continue

            yield scrapy.Request(
                url=candidate.url,
                callback=self.parse_candidate,
                errback=self.errback_candidate,
                cb_kwargs={"candidate_data": candidate.to_dict()},
                dont_filter=True,
            )

    def parse_candidate(self, response, candidate_data):
        candidate = UrlCandidate.from_dict(candidate_data)

        try:
            if candidate.source_type == "image":
                yielded = False
                for item in self.parse_image_candidate(response, candidate):
                    yielded = True
                    yield item

                if not yielded:
                    self.frontier.move_to_dead_letter(candidate.to_dict(), reason="no_images_extracted")
                return

            if candidate.source_type in {"blog", "think_tank"}:
                item = self.build_blog_item(response, candidate)
            else:
                item = self.build_news_item(response, candidate)

            if not item.get("title") and not item.get("text"):
                self.frontier.move_to_dead_letter(candidate.to_dict(), reason="empty_extraction")
                return

            yield item

        except Exception as error:
            self.frontier.move_to_dead_letter(candidate.to_dict(), reason=f"parse_error:{error.__class__.__name__}")
            raise

    def parse_image_candidate(self, response, candidate):
        scraper = ImageScraper(response)
        domain = scraper.get_domain()
        title = scraper.get_title()
        provenance = scraper.get_provenance()

        for image in scraper.extract_images():
            image_url = image.get("url", "")
            if not image_url:
                continue

            yield ImageItem(
                source_name=domain,
                source_type="image",
                page_url=response.url,
                image_url=image_url,
                image_urls=[image_url],
                images=[],
                title=title,
                alt=image.get("alt", ""),
                caption=image.get("caption", ""),
                metadata={
                    "status": response.status,
                    "domain": domain,
                    **provenance,
                    "frontier": candidate.to_dict(),
                },
            )

    def build_news_item(self, response, candidate):
        scraper = NewsScraper(response)
        data = self.maybe_refetch(response, candidate, scraper.get_data, NewsScraper)
        domain = self.get_domain(response.url)

        item = NewsItem()
        item["source_name"] = domain
        item["source_type"] = "video" if candidate.source_type == "video" else "news"
        item["url"] = response.url
        item["title"] = data.get("title", "")
        item["text"] = data.get("text", "")
        item["author"] = data.get("author", "")
        item["published_at"] = data.get("published_at", "")
        item["country_tags"] = candidate.country_tags
        item["topic_tags"] = self.merge_tags(candidate.topic_tags, data.get("keywords", []))
        item["metadata"] = {
            "status": response.status,
            "canonical_url": data.get("canonical_url", ""),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "images": data.get("images", []),
            "domain": data.get("domain", domain),
            "frontier": candidate.to_dict(),
            **data.get("provenance", {}),
        }
        return item

    def build_blog_item(self, response, candidate):
        scraper = BlogScraper(response)
        data = self.maybe_refetch(response, candidate, scraper.get_data, BlogScraper)
        domain = self.get_domain(response.url)

        item = BlogItem()
        item["source_name"] = domain
        item["source_type"] = "blog"
        item["url"] = response.url
        item["title"] = data.get("title", "")
        item["text"] = data.get("text", "")
        item["author"] = data.get("author", "")
        item["published_at"] = data.get("published_at", "")
        item["country_tags"] = candidate.country_tags
        item["topic_tags"] = self.merge_tags(
            candidate.topic_tags,
            data.get("tags", []),
            data.get("categories", []),
        )
        item["metadata"] = {
            "status": response.status,
            "canonical_url": data.get("canonical_url", ""),
            "description": data.get("description", ""),
            "language": data.get("language", ""),
            "images": data.get("images", []),
            "featured_image": data.get("featured_image", ""),
            "modified_at": data.get("modified_at", ""),
            "domain": data.get("domain", domain),
            "original_source_type": candidate.source_type,
            "frontier": candidate.to_dict(),
            **data.get("provenance", {}),
        }
        return item

    def maybe_refetch(self, response, candidate, get_data, scraper_class):
        data = get_data()
        fallback_allowed = self.use_scrapling_fallback or self.candidate_allows_fallback(candidate)
        should_fallback, reason = self.fetch_policy.should_fallback(
            response,
            data.get("text", ""),
            fallback_allowed,
        )

        if not should_fallback:
            return data

        result = self.fetch_client.fetch(response.url, self.scrapling_mode)
        if not result.ok:
            provenance = data.setdefault("provenance", {})
            provenance.update({
                "fallback_used": False,
                "fallback_reason": f"{reason}; fallback_failed={result.error}",
            })
            return data

        fallback_response = response.replace(
            url=result.url or response.url,
            body=result.html.encode("utf-8"),
        )
        fallback_data = scraper_class(fallback_response).get_data()
        provenance = fallback_data.setdefault("provenance", {})
        provenance.update({
            "fetcher": result.fetcher,
            "fallback_used": True,
            "fallback_reason": reason,
        })
        return fallback_data

    def candidate_allows_fallback(self, candidate):
        registry_metadata = candidate.metadata.get("source_registry", {})
        return bool(registry_metadata.get("scrapling_fallback_allowed"))

    def errback_candidate(self, failure):
        candidate_data = failure.request.cb_kwargs.get("candidate_data", {})
        candidate = UrlCandidate.from_dict(candidate_data)
        self.frontier.move_to_dead_letter(candidate.to_dict(), reason=f"fetch_failed:{failure.value.__class__.__name__}")

    def merge_tags(self, *tag_lists):
        tags = []
        seen = set()

        for tag_list in tag_lists:
            for tag in tag_list or []:
                text = str(tag).strip()
                key = text.lower()
                if text and key not in seen:
                    seen.add(key)
                    tags.append(text)

        return tags

    def get_domain(self, url):
        return urlparse(url).netloc.replace("www.", "")

    def to_bool(self, value):
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
