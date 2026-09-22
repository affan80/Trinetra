# TRINETRA Layer 3

## Current layer
Layer 3 — Raw Evidence Acquisition. Layer 1 produces profiles; Layer 2 produces safe jobs.

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
