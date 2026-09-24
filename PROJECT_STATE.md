# TRINETRA Layer 5

## Current layer
Layer 5 — Data quality, exact deduplication, and representative clustering. Layer 4 canonical records are the input contract.

## Completed components
- Normalized SQLAlchemy UUID schema for users, watchlists, entities, locations, keywords, sources, alert rules, profiles, generated queries, and audit logs.
- JWT/password authentication and ADMIN/ANALYST/VIEWER RBAC.
- Watchlist CRUD, lifecycle validation, deterministic parser/query expansion, profile versioning, previews, and audit history.
- Source and adapter registry foundation, collection plans/schedules/jobs, fingerprints, Redis handoff, Celery dispatch contract, rate/retry/checkpoint/health services, and collector worker heartbeat API.
- Markdown source importer and canonical YAML seed; hardened HTTP/SSRF client; RSS discovery/fixture collector; raw evidence/provenance models; SHA-256 content-addressed storage with MinIO or local fallback.

## Database schema summary
Models live in `backend/app/db/models.py`; Alembic scaffold is under `backend/alembic`. Layer 3 adds `raw_objects`, `collection_provenance`, and `robots_cache`.

## API endpoints implemented
Auth/register/login; Layer 1 profile APIs; Layer 2 source/plan/job APIs; Layer 3 RSS job execution endpoint: `POST /api/v1/collection-jobs/{id}/collect/rss`.

## Remaining tasks
- Add WEB/API/document/media adapters behind the same hardened fetch contract.
- Add quarantine/ClamAV, robots cache, MIME validation, Prometheus/JSON logging, and production Alembic migrations.
- Replace metadata-based initial migration with a generated PostgreSQL migration before production.

## Known issues
- Alembic initial migration uses metadata creation for the first local scaffold.
- Frontend build needs the Next SWC cache available in the local environment.
- Only the explicit RSS execution endpoint performs network collection; no analysis is performed.
- RSS execution is explicit and source-configured; tests use fixtures and do not contact live sites.

## Current milestone
First Layer 5 vertical slice complete: canonical record → quality → raw/text fingerprints → exact lookup → cluster → representative → annotation.

## Completed Layer 5 modules
- `backend/app/dedup/quality`: deterministic quality validation/scoring (`quality-v1`).
- `backend/app/dedup/fingerprints`: Unicode/whitespace normalization and SHA-256 text fingerprints (`fingerprint-v1`).
- `backend/app/dedup/clusters`: non-destructive cluster membership and representative selection.
- `backend/app/dedup/services/dedup_pipeline.py`: idempotent exact raw/text dedup and same-URL document-version records.

## Layer 5 database tables
`canonical_records`, `record_quality`, `record_fingerprints`, `duplicate_clusters`, `duplicate_cluster_members`, `record_similarities`, `duplicate_overrides`.

## API
`POST /api/v1/records/{id}/deduplicate`; quality, duplicate, similarity, and paginated cluster-member reads.

## Outstanding work
SimHash blocking, MinHash/LSH, conservative similarity decisions, lineage/attribution, document families, media fingerprints, Celery queue routing, metrics, and production migrations.

## Known Layer 5 issues
- Layer 4 had no persisted model in this checkout; `canonical_records` is the minimal explicit input seam and must be replaced by the real Layer 4 table when available.
- Alembic still uses metadata-based initial creation.

## Verification / security audit
- Local Layer 1–5 suite: 6 passed.
- React frontend lint: passed; no `dangerouslySetInnerHTML`, `innerHTML`, `eval`, or equivalent sink found.
- Fixed non-owner watchlist/plan/job/record access paths with ownership checks; added IDOR regression coverage.
- Hardened HTTP reads to stream and enforce response-size limits before buffering; bounded API lists, scheduler work, and representative scans.
- Docker Compose syntax is valid, but Docker daemon access is unavailable in this environment, so image build/start could not run.
- Added `backend/requirements.txt` so Docker installs only the active Layer 1–5 stack; legacy crawler/ML packages remain isolated in the root requirements for legacy services.
- Consolidated crawler imports on the existing canonical `services.ingestion.crawlers` and `services.ingestion.scraper` packages; removed obsolete top-level compatibility aliases and generated embedded environments.
- Optional Scrapy-based tests now skip cleanly when the legacy crawler dependencies are not installed in the minimal backend environment.
- Removed the unnecessary `python-dotenv` runtime dependency from the active Redis helper; environment variables are read directly.
- Full repository pytest collection: 9 passed, 2 skipped, 4 deprecation warnings. Removed the obsolete root Kafka smoke test instead of restoring the out-of-scope Kafka dependency to the active stack.
- Compileall, frontend lint, Docker Compose config, and canonical imports pass. Docker image build remains unverified because the Docker daemon is unavailable.
- Frontend production build passes with the stable Webpack builder; Next tracing is pinned to the frontend workspace root.
- Native runtime verified with SQLite: `backend/run.py` starts Uvicorn, `/health` returns 200, and registration returns a JWT. Frontend production server returned 200 for `/` and `/watchlists`.
- Local RSS fixture collection verified: one entry parsed, ETag/Last-Modified checkpoint produced, SHA-256 generated, and raw evidence written to the local object-store fallback.
- `run_tests.sh` now runs offline checks and reports optional Scrapy live runs as skipped instead of failing when Scrapy is absent.
- Live registry smoke run completed for all 3 configured base URLs and 2 discovered RSS feeds using bounded SSRF-validated HTTP; raw bytes were hashed and written to `/tmp/trinetra-live-evidence`.
- RSS discovery now deduplicates feeds by final URL when the same feed is found through HTML and conventional paths.
- Added `scripts/audit_source_registry.py` for bounded robots-aware collection and JSON reporting across every enabled manifest URL; current live report: 3/3 collected, 2 RSS feeds, 35 entries, 0 failures.
- Expanded `docs/source_registry.md` from 3 to 218 parsed links from the supplied government, defence/aerospace, aviation, maritime/naval, and cargo/logistics lists; canonical manifest contains 217 unique sources with no duplicate IDs or base URLs.
- Full 217-source base audit completed with 167 collected, 34 transport/configuration failures, 12 HTTP-forbidden responses, and 4 robots/policy blocks. Report: `artifacts/source_audit_217_final.json`.
- Importer now merges www/non-www source variants and emits both explicit approved host variants for redirect validation; transient audit network errors retry three times with bounded backoff.
- Registry audit artifacts are ignored by Git; canonical source manifest remains the version-controlled seed.
- Restored the canonical Scrapy `NewsItem`, `BlogItem`, and `ImageItem` contract in `services/storage/common/items.py`; removed legacy NER/Kafka pipelines from default spider startup so collection does not require Layer 6 or Kafka.
- Fixed optional Parsel fallback extraction and the source registry path; all local tests pass with or without Scrapling installed.
- Scrapy discovery now loads `blogs`, `frontier`, `images`, `news`, and `telegram`; the default crawler settings disable Telnet, NER, and Kafka startup coupling.
- Full `.venv` regression suite: 29 passed, 4 deprecation warnings.
