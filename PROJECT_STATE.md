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
