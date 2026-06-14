# Trinetra Scraper & Crawler Guide

This guide helps you run and test the data collection tools in Trinetra.

---

## 1. Quick Start

### Setup
1. **Enter Project Folder**: `cd Trinetra`
2. **Activate Environment**: `source .venv/bin/activate`
3. **Install Tools**: `pip install -r requirements.txt`

### Running the Test Suite
We have a simple script that runs all active spiders (News, Images, Blogs) and saves the results.
```bash
chmod +x run_tests.sh
./run_tests.sh
```
*   **Results**: Check the `artifacts/test_output/` folder for `.jsonl` files.
*   **Offline Checks**: The script first runs `tests/smoke/test_imports.py` and `tests/scraper/test_scrapers.py`.
*   **Redis**: The pipeline pushes valid items to Redis when `REDIS_URL` is reachable. If Redis is offline, crawls continue and only file output is written.
*   **Logging**: Spiders now use "Logarithmic Logging" (logs at 1, 2, 4, 8... pages) to keep your terminal clean.

---

## 2. Discovery vs Crawling

Current spiders crawl known URLs. You pass one or more seeds with `-a urls=...`, and the spider follows allowed links until its depth and `max_pages` limits are reached.

The planned discovery layer is separate. It will find candidate URLs from search APIs, RSS feeds, XML sitemaps, GDELT, Common Crawl, curated source registries, and platform APIs. Those candidates will be normalized, deduped, prioritized, and policy-checked in a Redis URL frontier before any spider fetches page content.

Target flow:

```text
Discovery -> Redis URL Frontier -> Scrapy/Scrapling Crawl -> OsintPipeline -> Redis raw_items
```

Important boundaries:

*   **Discovery** finds possible URLs but does not extract full article bodies.
*   **Frontier** dedupes, prioritizes, applies source policy, and schedules bounded crawl batches.
*   **Scrapy** remains the default crawler.
*   **Scrapling** improves parsing and optional fetch fallback; it does not replace discovery.
*   **Platform connectors** such as Telegram, Reddit, and YouTube should use their APIs and stay separate from ordinary web crawling.

Planning docs:

*   Temporary implementation plan: `docs/scraping/temp/IMPLEMENTATION.md`
*   Architecture: `docs/scraping/OSINT_COLLECTION_ARCHITECTURE.md`
*   Discovery guide: `docs/scraping/SOURCE_DISCOVERY_GUIDE.md`

---

## 3. Running Individual Spiders

If you want to run a specific spider manually, use these commands:

### Image Spider (New!)
Finds and extracts images with their titles and descriptions.
```bash
export PYTHONPATH="."
scrapy runspider services/crawlers/spiders/image_spider.py -a urls=https://example.com -o output.jsonl
```

### News Spider
Crawls news sites like BBC or Al Jazeera for articles.
```bash
export PYTHONPATH="."
scrapy runspider services/crawlers/spiders/news_spider.py -a urls=https://www.bbc.com/ -o output.jsonl
```

### Discovery Dry Run
Runs discovery connectors and prints normalized URL candidates without writing to Redis.
```bash
export PYTHONPATH="."
python -m services.scraper.discovery.run_discovery \
  --dry-run \
  --connectors rss,sitemap \
  --max-results 5
```

### Discovery To Frontier
Runs discovery and enqueues accepted URL candidates into the Redis URL frontier.
```bash
export PYTHONPATH="."
python -m services.scraper.discovery.run_discovery \
  --connectors rss,sitemap \
  --max-results 25
```

### Frontier Spider
Crawls a bounded batch from the Redis URL frontier and sends extracted items through the normal pipeline.
```bash
export PYTHONPATH="."
scrapy runspider services/crawlers/spiders/frontier_spider.py \
  -a batch_size=10 \
  -O artifacts/test_output/frontier.jsonl
```

---

## 4. Adding a New Spider

To add a new spider to the automated test script (`run_tests.sh`):
1. Open `run_tests.sh`.
2. Add your spider path and test URL to the `SPIDERS` list:
   ```bash
   "path/to/your_spider.py|urls=https://test-site.com"
   ```

---

## 5. Tips for Success

*   **Python Path**: Always run `export PYTHONPATH="."` before manual scrapy commands so the system can find its internal parts.
*   **Redis URL**: Local commands default to `redis://localhost:6379/0`. Override with `export REDIS_URL="redis://host:port/db"` if needed.
*   **Pipeline File Output**: Scrapy's `-o` option is the normal way to write output files. To also make the pipeline write `<spider>_data.jsonl`, set `OSINT_PIPELINE_LOCAL_FILE=1`.
*   **Scrapling Parser**: Scrapling parsing is enabled by default with `SCRAPLING_PARSER_ENABLED=true`. Scrapy still handles crawling unless fallback is explicitly enabled.
*   **Scrapling Fallback**: Set `SCRAPLING_FETCH_FALLBACK_ENABLED=true` or pass `-a use_scrapling_fallback=true` to let a spider retry blocked/low-quality pages with Scrapling static fetch.
*   **Browser Mode**: `SCRAPLING_FETCH_MODE=dynamic` or `stealth` requires `SCRAPLING_BROWSER_ENABLED=true` plus installed Playwright/Patchright browser binaries. Browser mode is disabled by default.
*   **Proxy**: Set `SCRAPLING_PROXY_URL` to pass a proxy URL into Scrapling fetchers.
*   **Discovery Limits**: Use `DISCOVERY_MAX_RESULTS`, `DISCOVERY_TIMEOUT_SECONDS`, `DISCOVERY_RATE_LIMIT_SECONDS`, and `FRONTIER_BATCH_SIZE` to keep discovery and frontier crawls bounded.
*   **API Keys**: `BRAVE_SEARCH_API_KEY` and `YOUTUBE_API_KEY` are optional. Their connectors return structured missing-credential errors when keys are not configured.
*   **Interruption**: You can stop any crawl by pressing `Ctrl+C`. The data collected up to that point will be saved safely.
*   **Cleaning Data**: All text cleaning and date parsing logic is central in `services/common/`.
