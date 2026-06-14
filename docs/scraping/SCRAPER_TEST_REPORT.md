# Scraper Test Report

Additional Scrapling integration validation was run after adding the hybrid parser/fetcher architecture.

New checks:

- `scrapling[fetchers]==0.4.9` installed successfully in the local `.venv`.
- `python -c "import scrapling; print(scrapling.__version__)"` returned `0.4.9`.
- `python -m compileall -q services/scraper services/crawlers tests/scraper/test_scrapers.py` passed.
- `python tests/smoke/test_imports.py` passed.
- `python tests/scraper/test_scrapers.py` passed 7 regression tests.
- `ScraplingFetchClient` static fetch to `https://books.toscrape.com/` returned HTTP 200.
- Bounded image, blog, and news crawls completed with Scrapling provenance metadata.

New live validation outputs:

```text
/tmp/trinetra_scrapling_image.jsonl  20 rows, 0 validation errors
/tmp/trinetra_scrapling_blog.jsonl    2 rows, 0 validation errors
/tmp/trinetra_scrapling_news.jsonl    5 rows, 0 validation errors
```

All validated rows included audit/provenance metadata such as `parser_engine`, `fetcher`, `extractor_version`, `collected_at`, and `validation_status`.

## Scope

Validated the scraper/crawler fixes for:

- Scrapy import and settings health.
- Image extraction coverage.
- `max_pages` request scheduling limits.
- Redis-off pipeline behavior.
- Optional pipeline local file output.
- JSONL output validity for image, blog, and news spiders.

## Commands Run

```bash
./.venv/bin/python -m py_compile \
  services/crawlers/spiders/image_spider.py \
  services/crawlers/spiders/news_spider.py \
  services/crawlers/spiders/blog_spider.py \
  services/scraper/surfaceweb/image_scraper.py \
  services/parser/pipelines.py \
  services/shared/redis_client.py \
  services/shared/redis_queue.py \
  services/shared/redis_metrics.py

./.venv/bin/python tests/smoke/test_imports.py
./.venv/bin/python tests/scraper/test_scrapers.py
./.venv/bin/scrapy settings --get ITEM_PIPELINES
```

Live spider checks were run with Redis intentionally unavailable:

```bash
REDIS_URL=redis://localhost:6399/0 ./.venv/bin/scrapy runspider \
  services/crawlers/spiders/image_spider.py \
  -a urls=https://books.toscrape.com/ \
  -a max_pages=3 \
  -O artifacts/test_output/manual_20260614_scraper_validation/image_redis_off.jsonl \
  --loglevel INFO

REDIS_URL=redis://localhost:6399/0 ./.venv/bin/scrapy runspider \
  services/crawlers/spiders/blog_spider.py \
  -a urls=https://www.csis.org/blogs/ \
  -a max_pages=3 \
  -O artifacts/test_output/manual_20260614_scraper_validation/blog_redis_off.jsonl \
  --loglevel INFO

REDIS_URL=redis://localhost:6399/0 ./.venv/bin/scrapy runspider \
  services/crawlers/spiders/news_spider.py \
  -a urls=https://www.aljazeera.com/ \
  -a max_pages=20 \
  -O artifacts/test_output/manual_20260614_scraper_validation/news_aljazeera_20_redis_off.jsonl \
  --loglevel INFO
```

Optional local pipeline output was tested with:

```bash
OSINT_PIPELINE_LOCAL_FILE=1 \
OSINT_PIPELINE_OUTPUT_DIR=artifacts/test_output/manual_20260614_scraper_validation/pipeline_local \
REDIS_URL=redis://localhost:6399/0 \
./.venv/bin/scrapy runspider services/crawlers/spiders/image_spider.py \
  -a urls=https://books.toscrape.com/ \
  -a max_pages=1 \
  -O artifacts/test_output/manual_20260614_scraper_validation/image_pipeline_local_feed.jsonl \
  --loglevel ERROR
```

## Results

| Check | Result | Notes |
| --- | --- | --- |
| Python compile | PASS | Changed scraper/pipeline/shared files compile. |
| Import smoke test | PASS | `tests/smoke/test_imports.py` passed. |
| Offline regression tests | PASS | `tests/scraper/test_scrapers.py` passed all 3 tests. |
| Scrapy pipeline setting | PASS | `OsintPipeline` is enabled. |
| Image spider live crawl | PASS | 20 image items, 0 JSON validation errors. |
| Blog spider live crawl | PASS | 1 blog item, 0 JSON validation errors. |
| News spider live crawl | PASS | 4 news items from Al Jazeera, 0 JSON validation errors. |
| Redis-off behavior | PASS | Pipeline emitted one startup warning and continued without per-item Redis errors. |
| `max_pages` scheduling | PASS | Image crawl with `max_pages=3` scheduled 3 page requests plus `robots.txt`. News crawl with `max_pages=20` scheduled 19 page requests plus `robots.txt`. |
| Pipeline local file output | PASS | Opt-in output wrote 20 lines to `pipeline_local/spider_data.jsonl`. |

Generated validation files:

```text
artifacts/test_output/manual_20260614_scraper_validation/blog_redis_off.jsonl                    1 row
artifacts/test_output/manual_20260614_scraper_validation/image_redis_off.jsonl                  20 rows
artifacts/test_output/manual_20260614_scraper_validation/image_pipeline_local_feed.jsonl        20 rows
artifacts/test_output/manual_20260614_scraper_validation/news_aljazeera_20_redis_off.jsonl       4 rows
artifacts/test_output/manual_20260614_scraper_validation/pipeline_local/spider_data.jsonl       20 rows
```

## Validation Details

JSONL validation checked:

- Every line parses as JSON.
- Image items have HTTP/HTTPS `image_url`.
- Image output has no duplicate `image_url` values.
- News/blog items have `url`.
- News/blog items have at least `title` or `text`.

All useful output files passed those checks.

## Limitations

- Docker was not running, so Redis-on integration through `docker compose up -d redis` could not be tested. The command failed because the Docker daemon was unavailable.
- `https://www.bbc.com/` was blocked by `robots.txt` in this environment, so the news spider live positive test used `https://www.aljazeera.com/`.
- Live site output can change over time because these tests depend on external websites.

## Added Regression Test

`tests/scraper/test_scrapers.py` was added to cover core behavior without network access:

- `ImageScraper` extracts meta images, normal `src`, lazy image attributes, `srcset`, and `<picture><source>`.
- `ImageSpider` enforces the scheduled request cap.
- `OsintPipeline` rejects invalid image URLs.
