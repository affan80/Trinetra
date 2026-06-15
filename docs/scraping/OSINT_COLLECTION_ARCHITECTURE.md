# OSINT Collection Architecture

## Purpose

This document explains how Trinetra should move from known-URL scraping to defence-grade OSINT discovery and crawling. The goal is not to "scrape the internet" blindly. The goal is to discover public sources lawfully, prioritize them, crawl bounded batches, extract structured records, validate them, preserve provenance, and queue them for analysis.

The target architecture builds on the current Scrapy/Scrapling/Redis stack:

```text
Discovery -> Frontier -> Crawl/Fetch -> Extract -> Validate -> Queue -> Analyze
```

## How Large Scrapers Actually Work

Large crawlers separate discovery from fetching.

- Discovery finds candidate URLs or platform records from search APIs, RSS feeds, sitemaps, public datasets, curated lists, and platform APIs.
- A frontier stores known URLs, deduplicates them, scores them, schedules them, and applies source policy.
- Crawlers fetch a bounded subset of the frontier instead of trying to exhaust the web.
- Extractors turn pages or API records into normalized items.
- Pipelines validate, dedupe, persist, queue, and add audit metadata.
- Analysis systems operate on validated records, not raw crawl noise.

Scrapy already models the crawl/fetch/extract pipeline well: spiders emit requests and items, the scheduler queues requests, the downloader fetches responses, and item pipelines validate/persist extracted items. For broad crawling, Scrapy guidance emphasizes many domains, time/page limits, slow per-domain politeness, parallelism across domains, and production-oriented logging/timeouts. Trinetra should use those ideas only after adding policy and frontier controls.

Apache Nutch and Heritrix show the same architectural lesson at web scale: seeds enter a crawl database/frontier, fetch lists are generated, pages are fetched in segments, links and content are parsed, and known URL state is updated for future rounds. Trinetra does not need to copy those systems, but it should adopt their separation of seed discovery, URL state, fetch scheduling, and post-processing.

## Current Trinetra Baseline

Current flow:

1. A Scrapy spider starts from one or more known URLs.
2. The spider filters links, enforces `max_pages`, and receives Scrapy responses.
3. A scraper helper extracts images, news, or blog content.
4. The spider builds `ImageItem`, `NewsItem`, or `BlogItem`.
5. `OsintPipeline` validates the item, adds audit metadata, and pushes valid records to Redis `raw_items` when Redis is available.
6. Scrapy feed export writes JSONL files when `-o` or `-O` is used.

Strengths:

- Scrapy is already the crawl orchestrator.
- Scrapling parsing/fetch fallback already exists behind flags.
- Redis queue, metrics, dedupe, and API stats helpers already exist.
- The current pipeline is a clean handoff point to downstream analysis.

Gap:

- There is no discovery layer or shared frontier. Current spiders crawl from known URLs, so coverage depends on manual seed selection.

## Target Collection Layers

### 1. Search API Discovery

Use Brave Search as the default web-search discovery provider. It supports web, news, image, and video-style discovery, freshness filtering, country/language targeting, and API-key authentication.

Use Google Custom Search JSON API only for legacy/existing customers or narrow existing engines. Current provider documentation marks it as a transition-risk option, so Brave Search should remain the default discovery provider.

Output:

- Public URLs that should be normalized into URL candidates.
- Query provenance, country/language parameters, and search provider metadata.

### 2. RSS Feed Discovery

Use RSS/Atom feeds for high-signal recurring sources such as newsrooms, government notices, think tanks, and blogs.

Output:

- Article URLs, titles, timestamps, feed source, and source tags.

### 3. Sitemap Discovery

Use XML sitemaps and sitemap indexes for domain-scoped discovery. Sitemaps are useful for finding official URLs and last-modified timestamps, but they are not a permission grant to crawl everything. Source policy and robots behavior still apply.

Output:

- Site URLs, optional `lastmod`, optional sitemap source, and domain tags.

### 4. GDELT Discovery

Use GDELT for global news monitoring, query-based article discovery, and near-real-time awareness across languages. GDELT is best for finding news URLs and topic bursts, not for replacing article extraction.

Output:

- News article URLs, title/metadata if available, query, time window, source language/domain metadata, and topic tags.

### 5. Common Crawl Discovery

Use Common Crawl CDXJ/index data for historical URL discovery and backfill. It is not a real-time monitoring source. It should feed historical candidates into a low-priority/backfill frontier queue with strict rate and storage controls.

Output:

- Historical captured URLs, timestamp, status, MIME type, digest, and crawl collection ID.

### 6. Curated Source Registry

Maintain a registry of high-value sources: official government domains, defence/security think tanks, regional media, public advisories, crisis-monitoring feeds, and approved research datasets.

Output:

- Seed URLs, feed URLs, sitemap URLs, domain policy, tags, and priority defaults.

### 7. Platform Connectors

Keep platform connectors separate from web crawling:

- YouTube: use the official Data API search/list flow first.
- Reddit: use bounded API/listing collectors instead of an infinite loop.
- Telegram: use API-style collection with explicit channel/source policy.

Output:

- Platform records plus canonical URLs where available.
- Platform IDs, channel/subreddit IDs, query metadata, timestamps, and rate-limit metadata.

### 8. Focused Crawlers

Scrapy spiders should remain focused crawlers. They take known URLs or frontier batches and extract page content under policy. Scrapling should improve parsing and fetch fallback, not become the discovery system.

## Normalized URL Candidate

Every discovery connector should emit:

```json
{
  "url": "https://example.com/story",
  "discovered_from": "brave_search|rss|sitemap|gdelt|common_crawl|manual|platform",
  "query": "india border security",
  "source_type": "news|blog|social|video|image|gov|think_tank|unknown",
  "priority": 0,
  "country_tags": [],
  "topic_tags": [],
  "discovered_at": "ISO-8601"
}
```

Recommended metadata extensions:

```json
{
  "metadata": {
    "provider": "brave_search",
    "provider_result_id": "",
    "title": "",
    "snippet": "",
    "published_at": "",
    "language": "",
    "domain": "example.com",
    "raw_source": "web|news|rss|sitemap|platform"
  }
}
```

## URL Frontier Responsibilities

The frontier is the scheduler and memory of known URLs.

Required responsibilities:

- Normalize URLs before storage.
- Reject non-HTTP/HTTPS web URLs unless they are platform IDs handled by platform collectors.
- Apply allowlist, denylist, skipped extension, and source-type policy.
- Deduplicate by normalized URL before enqueue.
- Optionally deduplicate by content hash after extraction.
- Store priority, tags, query, discovery source, and discovered timestamp.
- Schedule bounded batches for crawlers.
- Track retries, failures, dead letters, and last-attempt timestamps.
- Preserve enough provenance for audit and explainability.

Current reusable building blocks:

- `RedisQueue` for pending queues and dead-letter queues.
- `RedisDedupe` for URL/content hashes.
- `RedisMetrics` for counts.
- `SourcePolicy` for allow/deny and fetch fallback controls.

Future queue naming:

- `osint:queue:url_frontier`: pending crawl candidates.
- `osint:queue:url_frontier:dead_letter`: permanently failed or rejected candidates.
- `osint:dedupe:urls:<source>`: normalized URL dedupe.
- `osint:dedupe:content:<source>`: content dedupe.
- `osint:queue:raw_items`: existing validated item handoff.

## Crawl And Fetch Layer

Scrapy remains the default crawler.

Responsibilities:

- Obey robots settings for web crawling.
- Apply depth, page, delay, and concurrency limits.
- Fetch pages and pass responses to scraper helpers.
- Emit existing Scrapy items.
- Keep feed export available for JSONL testing.

Scrapling remains the parser/fetch fallback.

Responsibilities:

- Parse Scrapy response HTML when enabled.
- Retry blocked/empty/low-quality pages only when fallback is explicitly allowed.
- Use browser/stealth modes only when source policy permits them.
- Record fetcher, fallback state, fallback reason, and extractor version in item metadata.

## Extraction And Validation Layer

Extractors should produce existing item contracts first:

- `NewsItem`: title, text, author, published date, tags, URL, metadata.
- `BlogItem`: title, text, author, published date, tags, URL, metadata.
- `ImageItem`: image URL, page URL, title, alt text, caption, metadata.

Validation should continue in `OsintPipeline`:

- Reject empty article/blog items.
- Reject invalid image URLs.
- Add `collected_at`, `validation_status`, `source_url`, and `canonical_url`.
- Use Redis dedupe and metrics when Redis is available.

Future validation should add:

- URL scheme/domain policy checks.
- Minimum text quality thresholds.
- Canonical URL consistency.
- Content-hash dedupe.
- Required provenance metadata.

## Legal, Ethical, And Operational Constraints

Trinetra must collect lawful public OSINT.

Defaults:

- Respect robots.txt for ordinary web crawling.
- Respect API terms, quotas, and attribution requirements.
- Prefer official APIs and public feeds before HTML scraping.
- Do not bypass authentication, paywalls, CAPTCHAs, or access controls.
- Do not collect private, non-public, or unlawfully obtained data.
- Keep browser/stealth/proxy modes opt-in and source-policy controlled.
- Rate-limit all providers and domains.
- Keep bounded test runs as the default.
- Store audit metadata for every discovered candidate and extracted item.

Policy fields:

- `robots_obey`
- `api_terms_checked`
- `rate_limit_per_minute`
- `max_depth`
- `max_pages`
- `download_delay`
- `allowed_fetch_modes`
- `scrapling_fallback_allowed`
- `source_owner`
- `review_required`

## Failure Modes

| Failure | Expected behavior |
| --- | --- |
| API quota exceeded | Stop connector run, record provider error, keep existing frontier intact. |
| Redis unavailable | Discovery/frontier integration tests should fail clearly; direct Scrapy runs can still write JSONL. |
| Robots disallow | Reject or skip web crawl candidate with policy metadata. |
| Duplicate URL | Increment duplicate metric and do not enqueue. |
| Fetch blocked | Use Scrapling fallback only if policy allows it; otherwise skip with reason. |
| Extraction low quality | Record extraction failure or low-confidence metadata; do not silently emit junk. |
| Invalid item | Pipeline rejects item and increments invalid metric when Redis metrics are available. |

## Observability

Minimum metrics:

- `discovery_candidates_total`
- `frontier_enqueued_total`
- `frontier_duplicates_total`
- `frontier_policy_rejections_total`
- `crawl_attempts_total`
- `crawl_success_total`
- `crawl_failures_total`
- `pipeline_valid_items_total`
- `pipeline_invalid_items_total`
- `scrapling_fallback_attempted_total`
- `scrapling_fallback_used_total`
- `dead_letter_total`

Minimum logs:

- Connector name, query, and result count.
- Frontier enqueue/reject reason.
- Crawl batch ID and candidate count.
- Fetcher choice and fallback reason.
- Pipeline validation result.

## References

- Scrapy architecture: https://docs.scrapy.org/en/latest/topics/architecture.html
- Scrapy broad crawls: https://docs.scrapy.org/en/latest/topics/broad-crawls.html
- Robots Exclusion Protocol, RFC 9309: https://datatracker.ietf.org/doc/html/rfc9309
- Sitemaps protocol: https://www.sitemaps.org/protocol.html
- Google sitemap overview: https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
- Brave Search API: https://api-dashboard.search.brave.com/documentation
- GDELT Project: https://www.gdeltproject.org/
- GDELT DOC 2.0 API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- Common Crawl index: https://index.commoncrawl.org/
- Common Crawl CDXJ index: https://commoncrawl.org/cdxj-index
- Google Custom Search JSON API: https://developers.google.com/custom-search/v1/overview
- YouTube Data API search: https://developers.google.com/youtube/v3/docs/search/list
- Reddit API: https://www.reddit.com/dev/api/
- Apache Nutch tutorial: https://cwiki.apache.org/confluence/display/NUTCH/NutchTutorial
- Heritrix developer documentation: https://crawler.archive.org/articles/developer_manual/index.html
