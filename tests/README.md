# Tests

This folder keeps test code out of the project root and groups checks by purpose.

## Layout

```text
tests/
  smoke/          import and startup checks
  scraper/        scraper, discovery, frontier, and pipeline regression tests
  integration/    optional service-backed checks such as Redis
```

## Common Commands

```bash
./.venv/bin/python tests/smoke/test_imports.py
./.venv/bin/python tests/scraper/test_scrapers.py
./.venv/bin/python tests/integration/test_redis.py
```

`tests/integration/test_redis.py` skips Redis-specific checks when Redis is unavailable.
