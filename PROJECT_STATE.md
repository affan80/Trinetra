# TRINETRA Layer 1

## Current layer
Layer 1 — Analyst / Mission Input & Watchlist Control.

## Completed components
- Normalized SQLAlchemy UUID schema for users, watchlists, entities, locations, keywords, sources, alert rules, profiles, generated queries, and audit logs.
- JWT/password authentication and ADMIN/ANALYST/VIEWER RBAC.
- Watchlist CRUD, lifecycle validation, deterministic parser/query expansion, profile versioning, previews, and audit history.

## Database schema summary
Models live in `backend/app/db/models.py`; Alembic scaffold is under `backend/alembic`.

## API endpoints implemented
Auth register/login; watchlist CRUD; validate/compile/activate/pause/archive; query/profile/audit previews.

## Remaining tasks
- Expand the basic Next.js screens into full CRUD form/detail views.

## Known issues
- Alembic initial migration uses metadata creation for the first local scaffold.
- Frontend build needs the Next SWC cache available in the local environment.
