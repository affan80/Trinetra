# Source Discovery Guide

## Purpose

Discovery finds candidate URLs or platform records before crawling. It should not download full article bodies or bypass source controls. Each connector emits normalized URL candidates for the future frontier.

Common output shape:

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

Connector implementation rule: map provider-specific fields into `metadata`; do not change existing `NewsItem`, `BlogItem`, or `ImageItem` schemas during discovery work.

## Source Selection Matrix

| Source | Best for | Not for |
| --- | --- | --- |
| Brave Search | Fresh public web/news/image/video URL discovery. | Full article extraction or platform-specific private data. |
| Google Custom Search | Legacy programmable search engines and existing customers. | New default provider selection. |
| GDELT | Global news/event monitoring and query-based news discovery. | Real-time social media collection or full-text extraction. |
| Common Crawl | Historical/backfill URL discovery. | Real-time monitoring. |
| RSS | High-signal recurring articles from known publishers. | Unknown-source discovery. |
| Sitemaps | Domain-scoped URL discovery from known sites. | Permission bypass or exhaustive crawling without policy. |
| YouTube API | Video/channel discovery. | HTML scraping as first choice. |
| Reddit API | Bounded subreddit/search listings. | Infinite polling loops. |
| Telegram API | Approved channels/groups with credentials. | Unapproved/private data collection. |
| Manual registry | Curated high-value sources and policy defaults. | Replacing automated freshness discovery. |

## Brave Search API

Purpose:

- Primary web-search discovery provider.
- Find fresh URLs for defence topics, official statements, news articles, images, and videos.

Credentials:

- API key.
- Store as future environment variable `BRAVE_SEARCH_API_KEY`.
- Requests use Brave's subscription-token authentication header.

Input query shape:

```json
{
  "q": "india border security",
  "freshness": "pd|pw|pm|py|YYYY-MM-DDtoYYYY-MM-DD",
  "country": "IN",
  "search_lang": "en",
  "count": 20,
  "offset": 0
}
```

Output mapping:

- `url`: provider result URL.
- `discovered_from`: `brave_search`.
- `query`: original `q`.
- `source_type`: `news`, `image`, `video`, or `unknown` based on endpoint/result type.
- `priority`: derived from source registry and query importance.
- `metadata.title`: result title.
- `metadata.snippet`: result description/snippet.
- `metadata.provider`: `brave_search`.

Rate-limit considerations:

- Respect the subscribed Brave plan.
- Paginate only while provider response indicates more results.
- Keep connector runs bounded by query count and max results per query.

When to use:

- Fresh public web/news discovery.
- Query expansion around incidents, border security, misinformation narratives, think-tank analysis, and official public updates.

Security notes:

- Do not use search results as truth. Treat them as crawl candidates that still need extraction, validation, and credibility scoring.
- Keep SafeSearch and locale settings explicit per mission need.

References:

- https://api-dashboard.search.brave.com/documentation
- https://api-dashboard.search.brave.com/documentation/services/web-search

## Google Custom Search JSON API

Purpose:

- Optional/legacy provider for existing Programmable Search Engine users.
- Useful for narrow, curated domain sets where an existing search engine is already configured.

Credentials:

- API key.
- Programmable Search Engine ID.
- Future environment variables: `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID`.

Input query shape:

```json
{
  "q": "india border security",
  "cx": "programmable-search-engine-id",
  "num": 10,
  "start": 1
}
```

Output mapping:

- `url`: `item.link`.
- `discovered_from`: `google_custom_search`.
- `query`: original `q`.
- `source_type`: inferred from source registry/domain.
- `metadata.title`: `item.title`.
- `metadata.snippet`: `item.snippet`.
- `metadata.provider`: `google_custom_search`.

Rate-limit considerations:

- Current Google docs mark the API as a transition-risk option for existing customers.
- Free and paid quota limits apply for existing users.

When to use:

- Existing deployments with a configured search engine.
- Domain-restricted search during migration.

Security notes:

- Do not make this the default provider for new discovery work.
- Track migration risk in implementation tickets.

Reference:

- https://developers.google.com/custom-search/v1/overview

## GDELT DOC 2.0

Purpose:

- Global news discovery.
- Monitor topics, narratives, regions, images, and event-related public coverage.

Credentials:

- No local credential assumption in the plan.
- Confirm GDELT usage policies before production load.

Input query shape:

```json
{
  "query": "(\"border security\" OR \"line of control\")",
  "mode": "artlist",
  "maxrecords": 100,
  "timespan": "1week",
  "format": "json"
}
```

Output mapping:

- `url`: article URL from GDELT result.
- `discovered_from`: `gdelt`.
- `query`: original GDELT query.
- `source_type`: `news`.
- `metadata.title`: article title when available.
- `metadata.domain`: article domain.
- `metadata.published_at`: article date when available.
- `metadata.provider`: `gdelt_doc_2`.

Rate-limit considerations:

- Bound `maxrecords`.
- Prefer short time windows for monitoring.
- Use longer windows only for backfill jobs.

When to use:

- News monitoring across many regions/languages.
- Discovering emerging topic clusters.
- Seeding the crawler with article URLs found by GDELT.

Security notes:

- GDELT discovers third-party URLs; Trinetra still needs source policy before crawling them.
- Store query and time-window provenance for audit.

References:

- https://www.gdeltproject.org/
- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

## Common Crawl

Purpose:

- Historical and backfill URL discovery from public web crawl indexes.
- Useful for finding older URLs on known domains or historical snapshots of topic pages.

Credentials:

- No local credential assumption in the plan.
- Respect Common Crawl server guidance and avoid overloading index servers.

Input query shape:

```json
{
  "crawl": "CC-MAIN-YYYY-NN",
  "url_pattern": "example.com/news/*",
  "matchType": "prefix",
  "filter": "status:200",
  "output": "json"
}
```

Output mapping:

- `url`: CDXJ record URL.
- `discovered_from`: `common_crawl`.
- `source_type`: inferred from URL/domain.
- `priority`: low by default unless a backfill mission raises it.
- `metadata.timestamp`: crawl capture timestamp.
- `metadata.status`: HTTP status.
- `metadata.mime`: MIME type.
- `metadata.digest`: content digest.
- `metadata.crawl`: crawl collection ID.

Rate-limit considerations:

- Use index queries sparingly.
- Use Common Crawl columnar/bulk options for large-scale filtering instead of repeatedly hitting the public index server.
- Backfill runs should use a separate low-priority queue.

When to use:

- Historical discovery.
- Domain audits.
- Backfilling old public URLs for analysis.

Security notes:

- Common Crawl presence does not override source policy.
- Do not treat archived content as current.

References:

- https://index.commoncrawl.org/
- https://commoncrawl.org/cdxj-index

## RSS And Atom Feeds

Purpose:

- High-signal recurring discovery from known sources.
- Useful for official sites, newsrooms, think tanks, advisories, and blogs.

Credentials:

- Usually none for public feeds.
- Private/authenticated feeds are out of scope unless explicitly approved.

Input query shape:

```json
{
  "feed_url": "https://example.com/rss.xml",
  "source_name": "Example Source",
  "source_type": "news",
  "country_tags": ["IN"],
  "topic_tags": ["defence"]
}
```

Output mapping:

- `url`: feed entry link.
- `discovered_from`: `rss`.
- `query`: feed URL or source registry ID.
- `source_type`: registry source type.
- `metadata.title`: entry title.
- `metadata.published_at`: entry published/updated timestamp.
- `metadata.feed_url`: feed URL.

Rate-limit considerations:

- Poll feeds on a schedule appropriate to the source.
- Use conditional HTTP headers in future implementation where available.
- Deduplicate by entry URL and canonical URL.

When to use:

- Trusted or frequently monitored sources.
- Low-noise monitoring.

Security notes:

- Feed entries still pass through source policy before crawling.

References:

- https://www.rssboard.org/rss-specification
- https://datatracker.ietf.org/doc/html/rfc4287

## XML Sitemaps

Purpose:

- Domain-scoped discovery for known sources.
- Discover official page URLs, last-modified hints, and sitemap indexes.

Credentials:

- Usually none for public sitemaps.

Input query shape:

```json
{
  "sitemap_url": "https://example.com/sitemap.xml",
  "source_name": "Example Source",
  "source_type": "news",
  "max_urls": 1000
}
```

Output mapping:

- `url`: `<loc>` value.
- `discovered_from`: `sitemap`.
- `query`: sitemap URL.
- `metadata.lastmod`: `<lastmod>` when provided.
- `metadata.sitemap_url`: source sitemap URL.

Rate-limit considerations:

- Bound sitemap index expansion.
- Respect compressed sitemap sizes and parser limits.
- Use `lastmod` as a freshness hint, not as proof content changed.

When to use:

- Known official domains.
- Discovering deep article URLs without broad link crawling.

Security notes:

- A sitemap is a discovery aid, not permission to crawl all pages.
- Robots and source policy still apply.

References:

- https://www.sitemaps.org/protocol.html
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview

## YouTube Data API

Purpose:

- Discover public videos, channels, and playlists relevant to OSINT topics.

Credentials:

- YouTube Data API key or OAuth where required.
- Future environment variable: `YOUTUBE_API_KEY`.

Input query shape:

```json
{
  "q": "india border security",
  "part": "snippet",
  "type": "video",
  "maxResults": 50,
  "publishedAfter": "ISO-8601"
}
```

Output mapping:

- `url`: `https://www.youtube.com/watch?v=<videoId>`.
- `discovered_from`: `platform`.
- `source_type`: `video`.
- `metadata.provider`: `youtube`.
- `metadata.video_id`: video ID.
- `metadata.channel_id`: channel ID.
- `metadata.title`: snippet title.
- `metadata.description`: snippet description.
- `metadata.published_at`: snippet publish time.

Rate-limit considerations:

- Track quota cost and daily quota.
- Bound query count and result count.
- Store page tokens only as short-lived run state.

When to use:

- Video discovery, public channel monitoring, public incident footage discovery.

Security notes:

- Use official API first.
- Do not scrape private videos or bypass platform controls.

Reference:

- https://developers.google.com/youtube/v3/docs/search/list

## Reddit API

Purpose:

- Discover public posts and subreddits from bounded listings/search.

Credentials:

- Reddit app credentials/OAuth as required by chosen client implementation.
- Future environment variables: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`.

Input query shape:

```json
{
  "subreddit": "worldnews",
  "listing": "new|hot|top|rising",
  "q": "india border security",
  "limit": 100,
  "after": ""
}
```

Output mapping:

- `url`: Reddit permalink or external URL if policy allows downstream crawling.
- `discovered_from`: `platform`.
- `source_type`: `social`.
- `metadata.provider`: `reddit`.
- `metadata.subreddit`: subreddit name.
- `metadata.post_id`: post ID.
- `metadata.author`: public author name where allowed.
- `metadata.created_utc`: post timestamp.

Rate-limit considerations:

- Use listings with `limit` and pagination tokens.
- Avoid infinite loops.
- Respect Reddit API terms and rate limits.

When to use:

- Public social discussion monitoring.
- Discovering external URLs shared in public subreddits.

Security notes:

- Treat Reddit collection as platform collection, not ordinary web crawling.
- Do not collect private messages, restricted content, or authenticated-only data.

Reference:

- https://www.reddit.com/dev/api/

## Telegram Connector

Purpose:

- Monitor approved public or authorized Telegram channels/groups for OSINT signals.

Credentials:

- Telegram API ID/hash and any required session configuration.
- Current project already references Telegram credentials in local setup docs.

Input query shape:

```json
{
  "channel": "approved_channel_name",
  "max_messages": 100,
  "since": "ISO-8601",
  "source_policy_id": "telegram-approved-channel"
}
```

Output mapping:

- `url`: public message URL where available.
- `discovered_from`: `platform`.
- `source_type`: `social`.
- `metadata.provider`: `telegram`.
- `metadata.channel`: channel/group identifier.
- `metadata.message_id`: message ID.
- `metadata.collected_with_authorization`: true/false according to source policy.

Rate-limit considerations:

- Bound messages per channel per run.
- Handle provider flood/rate-limit errors gracefully.
- Keep channel allowlists explicit.

When to use:

- Approved public channels or authorized sources.
- Monitoring known sources in a controlled analyst workflow.

Security notes:

- Do not collect private groups/chats without explicit authorization.
- Keep credentials out of source control.
- Audit channel policy and collection scope.

## Manual And Curated Sources

Purpose:

- Encode analyst-approved sources and policy defaults.

Credentials:

- None unless a source explicitly uses an API.

Input shape:

```json
{
  "source_name": "Example Ministry",
  "source_type": "gov",
  "base_url": "https://example.gov/",
  "rss_urls": [],
  "sitemap_urls": [],
  "priority": 85,
  "country_tags": ["IN"],
  "topic_tags": ["defence"],
  "policy": {
    "robots_obey": true,
    "max_depth": 2,
    "max_pages": 100,
    "download_delay": 1.0,
    "scrapling_fallback_allowed": false
  }
}
```

Output mapping:

- Manual seeds become `discovered_from: "manual"`.
- Registry feeds/sitemaps feed RSS and sitemap connectors.

Rate-limit considerations:

- Apply per-source policy even for trusted sources.

When to use:

- Official sources, high-value domains, analyst-curated seed lists, and repeat monitoring targets.

Security notes:

- Registry changes should be reviewed because they control collection scope.

## Future Test Checklist

- Mock every provider response and verify normalized candidate mapping.
- Test URL normalization before dedupe.
- Test provider errors, quota errors, malformed responses, and empty results.
- Test source policy rejections.
- Test Redis frontier enqueue/dequeue with Redis available.
- Test bounded discovery -> frontier -> crawler -> pipeline path.

## References

- Brave Search API: https://api-dashboard.search.brave.com/documentation
- Google Custom Search JSON API: https://developers.google.com/custom-search/v1/overview
- GDELT Project: https://www.gdeltproject.org/
- GDELT DOC 2.0 API: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- Common Crawl index: https://index.commoncrawl.org/
- Common Crawl CDXJ index: https://commoncrawl.org/cdxj-index
- Sitemaps protocol: https://www.sitemaps.org/protocol.html
- Google sitemap overview: https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview
- YouTube Data API search: https://developers.google.com/youtube/v3/docs/search/list
- Reddit API: https://www.reddit.com/dev/api/
