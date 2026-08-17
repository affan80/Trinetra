from __future__ import annotations

import argparse
import json
import os
from typing import Iterable

from services.scraper.discovery import UrlCandidate
from services.scraper.discovery.connectors import (
    BraveSearchConnector,
    CommonCrawlConnector,
    GdeltConnector,
    RedditConnector,
    RssConnector,
    SitemapConnector,
    YouTubeConnector,
)
from services.scraper.policy import SourceRegistry
from services.shared.redis_metrics import RedisMetrics
from services.shared.url_frontier import FRONTIER_METRICS, UrlFrontier


DEFAULT_CONNECTORS = ["rss", "sitemap"]


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class DiscoveryRunner:
    def __init__(
        self,
        registry: SourceRegistry | None = None,
        frontier: UrlFrontier | None = None,
        metrics: RedisMetrics | None = None,
        max_results: int | None = None,
    ):
        self.registry = registry or SourceRegistry.from_file()
        self.metrics = metrics
        self.frontier = frontier
        self.max_results = max_results or env_int("DISCOVERY_MAX_RESULTS", 50)

    def run(
        self,
        connector_names: Iterable[str] | None = None,
        queries: list[str] | None = None,
        dry_run: bool = False,
        common_crawl_index: str = "",
    ) -> dict:
        connector_names = set(connector_names or DEFAULT_CONNECTORS)
        summary = {
            "dry_run": dry_run,
            "connectors": sorted(connector_names),
            "discovered": 0,
            "enqueued": 0,
            "duplicates": 0,
            "rejected": 0,
            "errors": [],
            "candidates": [],
        }

        for candidate in self.discover(connector_names, queries or [], common_crawl_index, summary):
            enriched = self.registry.enrich_candidate(candidate)
            summary["discovered"] += 1
            self.track(FRONTIER_METRICS["discovered"])

            if dry_run:
                summary["candidates"].append(enriched.to_dict())
                continue

            if not self.frontier:
                self.frontier = UrlFrontier(metrics=self.metrics)

            enqueue_result = self.frontier.enqueue(enriched)
            if enqueue_result.accepted:
                summary["enqueued"] += 1
            elif enqueue_result.reason == "duplicate_url":
                summary["duplicates"] += 1
            else:
                summary["rejected"] += 1

        return summary

    def discover(self, connector_names: set[str], queries: list[str], common_crawl_index: str, summary: dict):
        if "rss" in connector_names:
            yield from self.run_rss(summary)

        if "sitemap" in connector_names:
            yield from self.run_sitemap(summary)

        search_queries = self.registry_queries() + queries

        if "brave_search" in connector_names:
            yield from self.run_brave(search_queries, summary)

        if "gdelt" in connector_names:
            yield from self.run_gdelt(search_queries, summary)

        if "common_crawl" in connector_names:
            yield from self.run_common_crawl(common_crawl_index, summary)

        if "youtube" in connector_names:
            yield from self.run_youtube(search_queries, summary)

        if "reddit" in connector_names:
            yield from self.run_reddit(search_queries, summary)

    def run_rss(self, summary: dict):
        connector = RssConnector(max_results=self.max_results)
        for entry in self.registry.enabled_entries:
            for feed_url in entry.rss_urls:
                result = connector.discover(
                    feed_url=feed_url,
                    source_type=entry.source_type,
                    priority=entry.priority,
                    country_tags=entry.country_tags,
                    topic_tags=entry.topic_tags,
                    max_results=self.max_results,
                )
                self.add_errors(summary, result)
                yield from result.candidates

    def run_sitemap(self, summary: dict):
        connector = SitemapConnector(max_results=self.max_results)
        for entry in self.registry.enabled_entries:
            for sitemap_url in entry.sitemap_urls:
                result = connector.discover(
                    sitemap_url=sitemap_url,
                    source_type=entry.source_type,
                    priority=entry.priority,
                    country_tags=entry.country_tags,
                    topic_tags=entry.topic_tags,
                    max_results=self.max_results,
                )
                self.add_errors(summary, result)
                yield from result.candidates

    def run_brave(self, queries: list[str], summary: dict):
        connector = BraveSearchConnector(max_results=self.max_results)
        for query in self.unique_values(queries):
            result = connector.discover(query=query, max_results=self.max_results)
            self.add_errors(summary, result)
            yield from result.candidates

    def run_gdelt(self, queries: list[str], summary: dict):
        connector = GdeltConnector(max_results=self.max_results)
        for query in self.unique_values(queries):
            result = connector.discover(query=query, max_results=self.max_results)
            self.add_errors(summary, result)
            yield from result.candidates

    def run_common_crawl(self, common_crawl_index: str, summary: dict):
        connector = CommonCrawlConnector(max_results=self.max_results)
        for entry in self.registry.enabled_entries:
            patterns = entry.common_crawl_patterns or ([f"{entry.domain}/*"] if entry.domain else [])
            for pattern in patterns:
                result = connector.discover(
                    url_pattern=pattern,
                    crawl=common_crawl_index,
                    source_type=entry.source_type,
                    max_results=self.max_results,
                )
                self.add_errors(summary, result)
                yield from result.candidates

    def run_youtube(self, queries: list[str], summary: dict):
        connector = YouTubeConnector(max_results=self.max_results)
        registry_queries = []
        for entry in self.registry.enabled_entries:
            registry_queries.extend(entry.youtube_queries)

        for query in self.unique_values([*registry_queries, *queries]):
            result = connector.discover(query=query, max_results=self.max_results)
            self.add_errors(summary, result)
            yield from result.candidates

    def run_reddit(self, queries: list[str], summary: dict):
        connector = RedditConnector(max_results=self.max_results)
        subreddits = []
        for entry in self.registry.enabled_entries:
            subreddits.extend(entry.reddit_subreddits)

        result = connector.discover(
            subreddits=self.unique_values(subreddits),
            query=" OR ".join(self.unique_values(queries)) if queries else "",
            limit=min(self.max_results, 100),
            pages=1,
        )
        self.add_errors(summary, result)
        yield from result.candidates

    def registry_queries(self) -> list[str]:
        queries = []
        for entry in self.registry.enabled_entries:
            queries.extend(entry.discovery_queries)
        return self.unique_values(queries)

    def add_errors(self, summary: dict, result) -> None:
        for error in result.errors:
            summary["errors"].append(error.to_dict())

    def track(self, name: str) -> None:
        if not self.metrics:
            return

        try:
            self.metrics.increment(name)
        except Exception:
            pass

    def unique_values(self, values: Iterable[str]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                result.append(text)
        return result


def parse_args():
    parser = argparse.ArgumentParser(description="Run Trinetra source discovery and enqueue URL candidates.")
    parser.add_argument("--connectors", default=",".join(DEFAULT_CONNECTORS), help="Comma-separated connector names.")
    parser.add_argument("--query", action="append", default=[], help="Additional discovery query. Can be repeated.")
    parser.add_argument("--registry", default="", help="Path to source registry JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Print candidates without enqueueing.")
    parser.add_argument("--max-results", type=int, default=env_int("DISCOVERY_MAX_RESULTS", 50))
    parser.add_argument("--common-crawl-index", default=os.getenv("COMMON_CRAWL_INDEX", ""))
    return parser.parse_args()


def main():
    args = parse_args()
    registry = SourceRegistry.from_file(args.registry or None)
    metrics = None if args.dry_run else RedisMetrics()
    frontier = None if args.dry_run else UrlFrontier(metrics=metrics)
    runner = DiscoveryRunner(
        registry=registry,
        frontier=frontier,
        metrics=metrics,
        max_results=args.max_results,
    )
    connector_names = [name.strip() for name in args.connectors.split(",") if name.strip()]
    summary = runner.run(
        connector_names=connector_names,
        queries=args.query,
        dry_run=args.dry_run,
        common_crawl_index=args.common_crawl_index,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
