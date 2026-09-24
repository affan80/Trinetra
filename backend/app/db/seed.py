"""Database seeder to populate initial demo intelligence data for Trinetra V1."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.security import hash_password
from backend.app.db.models import (
    User, Role, Watchlist, WatchlistStatus, WatchlistLocation, Location,
    Source, MonitoringProfile, CollectionPlan, CollectionJob, RawObject,
    CanonicalRecord, RecordQuality, QualityStatus, DuplicateCluster,
    DuplicateClusterMember, DuplicateType, ClusterStatus, SourceHealth, CollectorWorker
)

def seed_database_if_empty(db: Session):
    existing_source = db.scalar(select(Source))
    if not existing_source:
        sources = [
            Source(id=uuid.uuid4(), name="Al Jazeera", source_class="NEWS", adapter_name="rss", enabled=True, allowed_domains=["aljazeera.com"]),
            Source(id=uuid.uuid4(), name="CSIS", source_class="BLOG", adapter_name="rss", enabled=True, allowed_domains=["csis.org"]),
            Source(id=uuid.uuid4(), name="Books To Scrape Test", source_class="ECOMMERCE", adapter_name="playwright", enabled=True, allowed_domains=["books.toscrape.com"]),
            Source(id=uuid.uuid4(), name="Reuters OSINT", source_class="NEWS", adapter_name="rss", enabled=True, allowed_domains=["reuters.com"]),
        ]
        db.add_all(sources)
        db.flush()

        for s in sources:
            db.add(SourceHealth(source_id=s.id, state="HEALTHY", consecutive_failures=0))

        db.add(CollectorWorker(id=uuid.uuid4(), worker_name="worker-primary-1", status="READY", last_heartbeat_at=datetime.now(timezone.utc)))
        db.commit()

    # Sweep ALL active watchlists in the database and ensure they have georeferenced locations and evidence records
    source = db.scalar(select(Source))
    watchlists = list(db.scalars(select(Watchlist).where(Watchlist.status != WatchlistStatus.ARCHIVED)))
    for w in watchlists:
        locs = db.execute(select(WatchlistLocation).where(WatchlistLocation.watchlist_id == w.id)).all()
        if not locs:
            l1 = Location(id=uuid.uuid4(), name="Kyiv Hub", latitude=50.4501, longitude=30.5234, location_type="REGION", country="UA", region="Kyiv")
            l2 = Location(id=uuid.uuid4(), name="Warsaw Logistics Center", latitude=52.2297, longitude=21.0122, location_type="CITY", country="PL", region="Mazovia")
            db.add_all([l1, l2])
            db.flush()
            db.add_all([
                WatchlistLocation(watchlist_id=w.id, location_id=l1.id),
                WatchlistLocation(watchlist_id=w.id, location_id=l2.id),
            ])

        recs = db.scalar(select(CanonicalRecord).where(CanonicalRecord.watchlist_id == w.id))
        if not recs and source:
            existing_profile = db.scalar(select(MonitoringProfile).where(MonitoringProfile.watchlist_id == w.id))
            p = existing_profile
            if not p:
                p = MonitoringProfile(id=uuid.uuid4(), watchlist_id=w.id, version=1, status="ACTIVE", payload={})
                db.add(p)
                db.flush()

            plan = CollectionPlan(id=uuid.uuid4(), profile_id=p.id, source_id=source.id, created_by=w.created_by)
            db.add(plan)
            db.flush()

            job = CollectionJob(
                id=uuid.uuid4(), plan_id=plan.id, profile_id=p.id, source_id=source.id,
                fingerprint=uuid.uuid4().hex * 2, query="infrastructure security", language="en", status="RUNNING"
            )
            db.add(job)
            db.flush()

            raw = RawObject(
                evidence_id=f"raw-{uuid.uuid4().hex[:8]}", job_id=job.id, source_id=source.id, watchlist_id=w.id,
                source_url="https://www.aljazeera.com/news/infrastructure-monitoring",
                final_url="https://www.aljazeera.com/news/infrastructure-monitoring",
                adapter_type="rss", object_uri=f"test://{uuid.uuid4().hex[:8]}", sha256=uuid.uuid4().hex * 2,
                content_type="text/html", content_length=1542, http_status=200, collector_version="v1"
            )
            db.add(raw)
            db.flush()

            rec1 = CanonicalRecord(
                record_id=f"rec-{uuid.uuid4().hex[:8]}", evidence_id=raw.evidence_id, source_id=source.id, watchlist_id=w.id,
                record_type="text", title="Infrastructure monitoring report: Energy grid stability in eastern transport hubs",
                canonical_url="https://www.aljazeera.com/news/infrastructure-monitoring"
            )
            db.add(rec1)
            db.flush()
            db.add(RecordQuality(record_id=rec1.record_id, status=QualityStatus.VALID, quality_score=0.94, quality_version="v1"))
    db.commit()


def seed_user_watchlist(db: Session, user):
    seed_database_if_empty(db)
    source = db.scalar(select(Source))

    watchlist = db.scalar(select(Watchlist).where(Watchlist.created_by == user.id, Watchlist.status != WatchlistStatus.ARCHIVED))
    if not watchlist:
        watchlist = Watchlist(
            id=uuid.uuid4(),
            name="Eastern European Security",
            objective="Monitor regional developments, infrastructure integrity, and transport corridors.",
            priority="HIGH",
            status=WatchlistStatus.ACTIVE,
            created_by=user.id
        )
        db.add(watchlist)
        db.flush()

    # Ensure locations
    locs = db.execute(select(WatchlistLocation).where(WatchlistLocation.watchlist_id == watchlist.id)).all()
    if not locs:
        l1 = Location(id=uuid.uuid4(), name="Kyiv Hub", latitude=50.4501, longitude=30.5234, location_type="REGION", country="UA", region="Kyiv")
        l2 = Location(id=uuid.uuid4(), name="Warsaw Logistics Center", latitude=52.2297, longitude=21.0122, location_type="CITY", country="PL", region="Mazovia")
        db.add_all([l1, l2])
        db.flush()
        db.add_all([
            WatchlistLocation(watchlist_id=watchlist.id, location_id=l1.id),
            WatchlistLocation(watchlist_id=watchlist.id, location_id=l2.id),
        ])

    # Ensure records
    recs = db.scalar(select(CanonicalRecord).where(CanonicalRecord.watchlist_id == watchlist.id))
    if not recs and source:
        existing_profile = db.scalar(select(MonitoringProfile).where(MonitoringProfile.watchlist_id == watchlist.id))
        p = existing_profile
        if not p:
            p = MonitoringProfile(id=uuid.uuid4(), watchlist_id=watchlist.id, version=1, status="ACTIVE", payload={})
            db.add(p)
            db.flush()

        plan = CollectionPlan(id=uuid.uuid4(), profile_id=p.id, source_id=source.id, created_by=user.id)
        db.add(plan)
        db.flush()

        job = CollectionJob(
            id=uuid.uuid4(), plan_id=plan.id, profile_id=p.id, source_id=source.id,
            fingerprint=uuid.uuid4().hex * 2, query="infrastructure security", language="en", status="RUNNING"
        )
        db.add(job)
        db.flush()

        raw = RawObject(
            evidence_id=f"raw-{uuid.uuid4().hex[:8]}", job_id=job.id, source_id=source.id, watchlist_id=watchlist.id,
            source_url="https://www.aljazeera.com/news/infrastructure-monitoring",
            final_url="https://www.aljazeera.com/news/infrastructure-monitoring",
            adapter_type="rss", object_uri=f"test://{uuid.uuid4().hex[:8]}", sha256=uuid.uuid4().hex * 2,
            content_type="text/html", content_length=1542, http_status=200, collector_version="v1"
        )
        db.add(raw)
        db.flush()

        rec1 = CanonicalRecord(
            record_id=f"rec-{uuid.uuid4().hex[:8]}", evidence_id=raw.evidence_id, source_id=source.id, watchlist_id=watchlist.id,
            record_type="text", title="Infrastructure monitoring report: Energy grid stability in eastern transport hubs",
            canonical_url="https://www.aljazeera.com/news/infrastructure-monitoring"
        )
        db.add(rec1)
        db.flush()
        db.add(RecordQuality(record_id=rec1.record_id, status=QualityStatus.VALID, quality_score=0.94, quality_version="v1"))

    db.commit()
