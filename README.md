# TRINETRA

Evidence-centric OSINT platform with a staged, auditable pipeline:

~~~text
Layer 1  Watchlists and monitoring profiles
   ↓
Layer 2  Collection planning, scheduling, jobs, policies, dispatch
   ↓
Layer 3  Raw evidence collection, hashing, storage, provenance
   ↓
Layer 4  Canonical-record input seam
   ↓
Layer 5  Data quality, exact deduplication, clustering, representative selection
~~~

The active repository preserves source observations and adds deterministic operational metadata. Intelligence analysis is intentionally outside the current Layer 1–5 path: no NER, event extraction, credibility scoring, knowledge graph, RAG, or LLM analysis.

## Current status

Implemented:

- JWT authentication with ADMIN, ANALYST, and VIEWER access control.
- Watchlist CRUD, lifecycle validation, deterministic requirement parsing, query expansion, and versioned monitoring profiles.
- Source registry, collection plans, schedules, jobs, Redis handoff, Celery dispatch, retry/rate/checkpoint/health foundations.
- Hardened HTTP/SSRF validation, RSS discovery fixtures, explicit RSS collection, SHA-256 preservation, MinIO-compatible storage, and provenance records.
- Layer 5 first slice: canonical record → quality → raw/text fingerprints → exact duplicate lookup → cluster → representative → annotation.
- Ownership checks for watchlists, plans, jobs, and record endpoints.

Current limits:

- Layer 4 is represented by the minimal canonical_records input seam in this checkout.
- Layer 3 currently exposes the explicit RSS execution path; WEB/API/document/media adapters are incomplete.
- Layer 5 currently implements exact raw/text deduplication. SimHash, MinHash/LSH, lineage, media fingerprints, and queue routing remain future work.
- Alembic has an initial local scaffold; production migrations still need to replace metadata-based creation.

## Repository layout

~~~text
backend/
  app/
    main.py                 FastAPI application and current API routes
    core/                   configuration and security
    db/                     SQLAlchemy database, enums, and models
    services/               Layer 1/2/3 service logic
    collectors/             Layer 3 adapters
    security/               SSRF-aware network and HTTP helpers
    dedup/                  Layer 5 quality, fingerprints, clusters, pipeline
    workers/                Celery and scheduler entry points
  alembic/                  database migration scaffold
  requirements.txt          minimal active backend/container dependencies
  Dockerfile

frontend/
  pages/                    Next.js pages for watchlists and collection control
  package.json

config/                     source registry and scraper configuration
docs/                       source registry and architecture documentation
scripts/                    source import and RSS discovery commands
tests/                      Layer 3/5/security and fixture-based tests
PROJECT_STATE.md            compact implementation state
docker-compose.yml          local PostgreSQL/Redis/MinIO/API/worker stack
~~~

Legacy crawler, processing, graph, Kafka, and model code remains in services/, models/, and related directories for separate work. It is not installed by the active backend Docker image and is not part of the current Layer 1–5 request path.

## Docker quick start

Prerequisites:

- Docker Desktop or another Docker Engine with Compose support.

Start from the repository root:

~~~bash
cp .env.example .env
docker compose up --build
~~~

Services:

| Service | Address | Purpose |
|---|---|---|
| backend | http://localhost:8000 | FastAPI API |
| frontend | http://localhost:3000 | Next.js UI |
| postgres | localhost:5432 | System of record |
| redis | localhost:6379 | Queue/cache handoff |
| minio | http://localhost:9000 | Raw evidence object storage |
| MinIO console | http://localhost:9001 | Development storage console |
| celery | internal | Collection job worker |
| scheduler | internal | Collection schedule process |

Development Compose credentials are intentionally local-only. Change them in .env before sharing or deploying.

~~~bash
curl http://localhost:8000/health
~~~

Expected response:

~~~json
{"status":"healthy"}
~~~

Stop the stack:

~~~bash
docker compose down
~~~

Named PostgreSQL and MinIO volumes are retained. Reset local data only when intentional:

~~~bash
docker compose down -v
~~~

## Configuration

Copy .env.example to .env:

~~~env
DATABASE_URL=postgresql+psycopg://trinetra:trinetra@postgres:5432/trinetra
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=trinetra
MINIO_SECRET_KEY=replace-with-a-secret
MINIO_BUCKET_RAW=raw-evidence
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_ENV=development
API_V1_PREFIX=/api/v1
~~~

Never commit real secrets. The backend defaults to SQLite for lightweight local tests when DATABASE_URL is unset; Docker uses PostgreSQL.

## API

Base path: /api/v1

Authentication:

~~~text
POST /auth/register
POST /auth/login
~~~

Watchlists and monitoring profiles:

~~~text
POST   /watchlists
GET    /watchlists
GET    /watchlists/{id}
PATCH  /watchlists/{id}
POST   /watchlists/{id}/validate
POST   /watchlists/{id}/compile
POST   /watchlists/{id}/activate
POST   /watchlists/{id}/pause
POST   /watchlists/{id}/archive
GET    /watchlists/{id}/preview-queries
GET    /watchlists/{id}/monitoring-profile
GET    /watchlists/{id}/audit
~~~

Layer 2 collection control:

~~~text
POST /sources
GET  /sources
GET  /collectors
POST /collectors/heartbeat

POST /collection-plans
GET  /collection-plans
GET  /collection-jobs
POST /collection-jobs/{id}/dispatch
POST /collection-jobs/{id}/celery-dispatch
POST /sources/{id}/health
~~~

Layer 3 explicit RSS path:

~~~text
POST /collection-jobs/{id}/collect/rss
~~~

Layer 5 processing and reads:

~~~text
POST /records/{id}/deduplicate
GET  /records/{id}/quality
GET  /records/{id}/duplicates
GET  /records/{id}/similarities
GET  /duplicate-clusters/{id}/members
~~~

Protected endpoints require a bearer token from registration or login. Non-admin users can access only records and collection resources connected to their own watchlists. VIEWER is read-only.

## Typical workflow

1. Register or log in.
2. Create a watchlist as ANALYST.
3. Validate it, compile a monitoring profile, and activate it.
4. Register enabled sources as ADMIN.
5. Create collection plans for the active profile.
6. Dispatch a generated job.
7. For a trusted configured RSS source, run the explicit RSS collection endpoint.
8. Submit a Layer 4 canonical record to the Layer 5 deduplication endpoint.
9. Read its quality annotation, cluster membership, and representative assignment.

Collection and deduplication are non-destructive: raw evidence, canonical records, provenance, and duplicate observations remain preserved.

## Source registry tools

The approved source document is docs/source_registry.md. Import it into the version-controlled manifest:

~~~bash
python scripts/import_source_registry.py docs/source_registry.md
~~~

The importer writes config/source_registry.yaml and reports parsed, merged, missing, and invalid entries. Tracking parameters are removed and URLs are canonicalized; missing URLs are disabled rather than guessed.

RSS discovery supports bounded runs:

~~~bash
python scripts/discover_rss.py --source SRC-PIB
python scripts/discover_rss.py --sector NEWS --limit 20
python scripts/discover_rss.py --all-enabled --limit 20
~~~

Tests use local RSS and autodiscovery fixtures. Check robots and usage policies before broad discovery against third-party sites.

## Local development

Backend:

~~~bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8000
~~~

For PostgreSQL-backed development, export DATABASE_URL and the other values from .env. Leave DATABASE_URL unset for the default SQLite test seam.

Frontend:

~~~bash
cd frontend
npm ci
npm run dev
~~~

The frontend currently provides basic watchlist and collection-control pages, prioritizing functionality over finished visual design.

## Verification

Run the active Layer 1–5 regression and security tests:

~~~bash
PYTHONPATH=. python -m pytest -q \
  backend/tests/test_layer1.py \
  tests/test_layer3.py \
  tests/test_layer5.py \
  tests/test_security_audit.py
~~~

Other checks:

~~~bash
PYTHONPATH=. python -m compileall -q backend/app tests scripts
cd frontend && npm run lint
cd frontend && npm run build
cd .. && docker compose config
~~~

The tests cover watchlist CRUD, RSS fixtures, hashing/storage paths, exact deduplication, idempotent reruns, ownership checks, and security-oriented URL behavior. Docker image startup additionally requires a running Docker daemon.

## Security boundaries

- Passwords are hashed and JWTs expire using ACCESS_TOKEN_EXPIRE_MINUTES.
- Active API paths use ORM/parameterized database operations.
- Ownership and role checks protect watchlists, plans, jobs, and Layer 5 record reads.
- Outbound HTTP helpers validate schemes, DNS/IP destinations, redirects, ports, timeouts, and response sizes.
- HTTP bodies are bounded before buffering; API lists and cluster scans are bounded and paginated.
- Raw evidence is SHA-256 hashed and stored through the object-store abstraction with provenance.
- The current React UI uses normal rendering; no dangerouslySetInnerHTML, innerHTML, or eval sink is present.

This is a development platform, not a production security certification. Run dependency scanning, backups, secret rotation, container hardening, and external penetration testing before deployment.

## Design constraints

Layer 1–5 deliberately does not include:

~~~text
Kafka, Kubernetes, Neo4j, OpenSearch, Qdrant, ML/LLM analysis,
NER, OCR, ASR, translation, claim/event extraction, credibility scoring,
knowledge graphs, evidence graphs, RAG, or intelligence alert detection.
~~~

The active backend image installs only backend/requirements.txt. The root requirements.txt remains for legacy scraper/model experiments and is not used by the Docker backend image.

## Project state

PROJECT_STATE.md is the compact source of truth for implementation milestones, schema status, thresholds, tests, and known issues. Update it whenever a meaningful layer milestone changes.
