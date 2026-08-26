from __future__ import annotations

import asyncio
import logging
import os
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
import trafilatura
from lxml import html as lxml_html

from services.ingestion.scraper.policy.source_registry import SourceRegistry, SourceRegistryEntry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DefenceCollector")

USER_AGENT = os.getenv("COLLECTOR_USER_AGENT", "TrinetraCollector/1.0 (public source monitoring)")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
KAFKA_TOPIC_RAW = os.getenv("KAFKA_TOPIC", "scraped_data_raw")
MAX_PAGES_PER_SOURCE = int(os.getenv("COLLECTOR_MAX_PAGES", "10"))
REQUEST_TIMEOUT = float(os.getenv("COLLECTOR_TIMEOUT", "30"))

LISTING_KEYWORDS = ("press", "release", "news", "announcement", "update", "whats-new", "media")


class RobotsCache:
    def __init__(self):
        self._cache: dict[str, RobotFileParser] = {}

    async def allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._cache:
            parser = RobotFileParser()
            try:
                resp = await client.get(f"{base}/robots.txt")
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                else:
                    parser.allow_all = True
                    parser.disallow_all = False
            except Exception:
                parser.allow_all = True
            self._cache[base] = parser
        return self._cache[base].can_fetch(USER_AGENT, url)


def make_message(entry: SourceRegistryEntry, url: str, title: str, extracted: dict) -> dict:
    return {
        "source_name": entry.source_name,
        "source_type": entry.source_type,
        "url": url,
        "title": title or extracted.get("title") or "",
        "text": extracted.get("text") or "",
        "author": extracted.get("author"),
        "published_at": extracted.get("date"),
        "topic_tags": entry.topic_tags,
        "metadata": {"robots_obey": True, "collector": "defence_collector"},
    }


def extract_article(page_html: str) -> dict:
    data = trafilatura.bare_extraction(
        page_html,
        include_comments=False,
        include_tables=True,
        with_metadata=True,
    )
    return data or {}


def same_domain(base_url: str, url: str) -> bool:
    base_domain = urlparse(base_url).netloc.removeprefix("www.").lower()
    link_domain = urlparse(url).netloc.removeprefix("www.").lower()
    return bool(link_domain) and (link_domain == base_domain or link_domain.endswith("." + base_domain))


def looks_like_listing(href_path: str) -> bool:
    return any(keyword in href_path.lower() for keyword in LISTING_KEYWORDS)


async def collect_rss(client: httpx.AsyncClient, robots: RobotsCache, entry: SourceRegistryEntry) -> list[dict]:
    messages = []
    for feed_url in entry.rss_urls:
        try:
            resp = await client.get(feed_url)
            feed = feedparser.parse(resp.text)
        except Exception as error:
            logger.warning("%s: RSS fetch failed for %s: %s", entry.source_name, feed_url, error)
            continue

        logger.info("%s: %d items from %s", entry.source_name, len(feed.entries), feed_url)

        for item in feed.entries[:MAX_PAGES_PER_SOURCE]:
            link = getattr(item, "link", "")
            if not link or not await robots.allowed(client, link):
                continue

            try:
                page = await client.get(link)
                page.raise_for_status()
                extracted = extract_article(page.text)
            except Exception as error:
                logger.warning("%s: article fetch failed %s: %s", entry.source_name, link, error)
                extracted = {}

            messages.append(make_message(entry, link, getattr(item, "title", ""), extracted))
            await asyncio.sleep(entry.download_delay)

    return messages


async def collect_listings(client: httpx.AsyncClient, robots: RobotsCache, entry: SourceRegistryEntry) -> list[dict]:
    if not entry.listing_urls or not entry.base_url:
        return []

    article_links: list[str] = []
    seen: set[str] = set()
    listing_urls_seen: set[str] = set()

    for listing_path in entry.listing_urls:
        listing_url = urljoin(entry.base_url, listing_path)
        if not await robots.allowed(client, listing_url):
            logger.info("%s: robots.txt disallows %s", entry.source_name, listing_url)
            continue

        try:
            resp = await client.get(listing_url)
        except Exception as error:
            logger.warning("%s: listing fetch failed %s: %s", entry.source_name, listing_url, error)
            continue

        doc = lxml_html.fromstring(resp.text)
        listing_urls_seen.add(listing_url)
        for href in doc.xpath("//a/@href"):
            absolute = urljoin(listing_url, href).split("#")[0]
            path = urlparse(absolute).path
            if path.lower().endswith((".pdf", ".jpg", ".png", ".zip")):
                continue
            if absolute not in seen and same_domain(entry.base_url, absolute) and looks_like_listing(path):
                seen.add(absolute)
                article_links.append(absolute)

        await asyncio.sleep(entry.download_delay)

    article_links = [url for url in article_links if url not in listing_urls_seen]
    article_links = article_links[:MAX_PAGES_PER_SOURCE]
    logger.info("%s: %d candidate pages from listings", entry.source_name, len(article_links))

    messages = []
    for url in article_links:
        if not await robots.allowed(client, url):
            continue
        try:
            page = await client.get(url)
            extracted = extract_article(page.text)
            title = extracted.get("title") or ""
        except Exception as error:
            logger.warning("%s: article fetch failed %s: %s", entry.source_name, url, error)
            continue

        if extracted.get("text"):
            messages.append(make_message(entry, url, title, extracted))
        await asyncio.sleep(entry.download_delay)

    return messages


def listing_urls_first(entry: SourceRegistryEntry) -> str:
    return entry.listing_urls[0] if entry.listing_urls else ""


async def collect_all() -> list[dict]:
    registry = SourceRegistry.from_file()
    defence_sources = [
        entry
        for entry in registry.enabled_entries
        if entry.source_type in {"government", "corporate"} and "IN" in entry.country_tags
    ]

    robots = RobotsCache()
    all_messages: list[dict] = []

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=REQUEST_TIMEOUT,
    ) as client:
        for entry in defence_sources:
            logger.info("Collecting from %s (%s)", entry.source_name, entry.base_url)
            rss_messages = await collect_rss(client, robots, entry)
            listing_messages = await collect_listings(client, robots, entry)
            collected = rss_messages + listing_messages
            logger.info("%s: %d messages collected", entry.source_name, len(collected))

            seen_urls = {msg["url"] for msg in all_messages}
            all_messages.extend(msg for msg in collected if msg["url"] not in seen_urls)
            await asyncio.sleep(1.0)

    return all_messages


def publish_to_kafka(messages: list[dict]) -> int:
    if not messages:
        logger.warning("No messages to publish")
        return 0

    from kafka import KafkaProducer

    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BOOTSTRAP_SERVERS],
        value_serializer=lambda value: json_dumps(value),
    )

    sent = 0
    for message in messages:
        producer.send(KAFKA_TOPIC_RAW, value=message)
        sent += 1
    producer.flush()
    producer.close()
    logger.info("Published %d messages to %s", sent, KAFKA_TOPIC_RAW)
    return sent


def json_dumps(value: dict) -> bytes:
    import json

    return json.dumps(value, default=str).encode("utf-8")


def main():
    started = time.time()
    messages = asyncio.run(collect_all())
    published = publish_to_kafka(messages)
    logger.info(
        "Done: %d sources processed, %d messages published in %.1fs",
        len({m["source_name"] for m in messages}),
        published,
        time.time() - started,
    )


if __name__ == "__main__":
    main()
