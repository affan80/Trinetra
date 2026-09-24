"""Read-only analyst overview assembled from the existing evidence tables."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AuditLog,
    CanonicalRecord,
    CollectionJob,
    CollectionPlan,
    CollectorWorker,
    DuplicateCluster,
    DuplicateClusterMember,
    Location,
    MonitoringProfile,
    RawObject,
    RecordQuality,
    Source,
    SourceHealth,
    Watchlist,
    WatchlistLocation,
    WatchlistStatus,
)


def _count(db: Session, model, *conditions) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


def _visible_watchlists(db: Session, user) -> list[Watchlist]:
    query = select(Watchlist).where(Watchlist.status != WatchlistStatus.ARCHIVED).order_by(Watchlist.updated_at.desc()).limit(50)
    if user.role.value != "ADMIN":
        query = query.where(Watchlist.created_by == user.id)
    return list(db.scalars(query))


def _record_filter(user):
    if user.role.value == "ADMIN":
        return ()
    return (CanonicalRecord.watchlist_id.in_(_owned_watchlist_ids(user)),)


def _raw_filter(user):
    if user.role.value == "ADMIN":
        return ()
    return (RawObject.watchlist_id.in_(_owned_watchlist_ids(user)),)


def _job_filter(user):
    if user.role.value == "ADMIN":
        return ()
    return (CollectionJob.plan_id.in_(
        select(CollectionPlan.id)
        .join(MonitoringProfile, MonitoringProfile.id == CollectionPlan.profile_id)
        .where(MonitoringProfile.watchlist_id.in_(_owned_watchlist_ids(user)))
    ),)


def _owned_watchlist_ids(user):
    return select(Watchlist.id).where(
        Watchlist.created_by == user.id,
        Watchlist.status != WatchlistStatus.ARCHIVED,
    )


def build_overview(db: Session, user) -> dict:
    watchlists = _visible_watchlists(db, user)
    locations = db.execute(
        select(WatchlistLocation.watchlist_id, Location)
        .join(Location, Location.id == WatchlistLocation.location_id)
        .where(WatchlistLocation.watchlist_id.in_([w.id for w in watchlists]))
    ).all() if watchlists else []
    locations_by_watchlist: dict[str, list] = {str(w.id): [] for w in watchlists}
    for watchlist_id, location in locations:
        locations_by_watchlist[str(watchlist_id)].append({
            "id": str(location.id), "name": location.name,
            "latitude": location.latitude, "longitude": location.longitude,
        })
    record_counts = {watchlist_id: (count, source_count) for watchlist_id, count, source_count in db.execute(
        select(
            CanonicalRecord.watchlist_id,
            func.count(CanonicalRecord.id),
            func.count(distinct(CanonicalRecord.source_id)),
        )
        .where(CanonicalRecord.watchlist_id.in_([w.id for w in watchlists]))
        .group_by(CanonicalRecord.watchlist_id)
    ).all()} if watchlists else {}

    record_filter = _record_filter(user)
    raw_filter = _raw_filter(user)
    job_filter = _job_filter(user)
    canonical_count = _count(db, CanonicalRecord, *record_filter)
    duplicate_count = db.scalar(
        select(func.count(distinct(DuplicateClusterMember.record_id)))
        .join(CanonicalRecord, CanonicalRecord.record_id == DuplicateClusterMember.record_id)
        .join(DuplicateCluster, DuplicateCluster.id == DuplicateClusterMember.cluster_id)
        .where(DuplicateClusterMember.record_id != DuplicateCluster.representative_record_id, *record_filter)
    ) or 0

    rows = db.execute(
        select(CanonicalRecord, Source.name, RecordQuality.quality_score, RecordQuality.status)
        .outerjoin(Source, Source.id == CanonicalRecord.source_id)
        .outerjoin(RecordQuality, RecordQuality.record_id == CanonicalRecord.record_id)
        .where(*record_filter)
        .order_by(CanonicalRecord.created_at.desc())
        .limit(40)
    ).all()
    records = [{
        "id": record.record_id,
        "evidence_id": record.evidence_id,
        "title": record.title or record.canonical_url or "Untitled evidence",
        "type": record.record_type,
        "source": source_name or "Unknown source",
        "watchlist_id": str(record.watchlist_id) if record.watchlist_id else None,
        "timestamp": (record.published_at or record.retrieved_at or record.created_at).isoformat(),
        "quality_score": quality_score,
        "quality_status": quality_status.value if quality_status else None,
        "url": record.canonical_url,
    } for record, source_name, quality_score, quality_status in rows]

    sources = list(db.scalars(select(Source).order_by(Source.name).limit(100)))
    source_count = _count(db, Source)
    enabled_source_count = _count(db, Source, Source.enabled.is_(True))
    source_health = {str(row.source_id): row.state for row in db.scalars(select(SourceHealth))}
    jobs = list(db.scalars(select(CollectionJob).where(*job_filter).order_by(CollectionJob.created_at.desc()).limit(20)))
    audit_filter = () if user.role.value == "ADMIN" else (AuditLog.watchlist_id.in_(_owned_watchlist_ids(user)),)
    audits = list(db.scalars(select(AuditLog).where(*audit_filter).order_by(AuditLog.timestamp.desc()).limit(20)))

    timeline = [
        {"id": f"record:{row['id']}", "timestamp": row["timestamp"], "title": "Evidence normalized", "detail": row["title"], "kind": "evidence"}
        for row in records[:12]
    ] + [
        {"id": f"job:{job.id}", "timestamp": job.created_at.isoformat(), "title": f"Collection job {job.status.lower()}", "detail": job.query[:100], "kind": "job"}
        for job in jobs[:12]
    ] + [
        {"id": f"audit:{event.id}", "timestamp": event.timestamp.isoformat(), "title": event.event_type.replace("_", " ").title(), "detail": "Watchlist activity", "kind": "audit"}
        for event in audits[:12]
    ]
    timeline.sort(key=lambda event: event["timestamp"], reverse=True)

    workers = list(db.scalars(select(CollectorWorker)))
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    live_workers = sum(1 for worker in workers if worker.status == "READY" and worker.last_heartbeat_at and (worker.last_heartbeat_at.replace(tzinfo=timezone.utc) if worker.last_heartbeat_at.tzinfo is None else worker.last_heartbeat_at.astimezone(timezone.utc)) >= cutoff)
    active_jobs = _count(db, CollectionJob, CollectionJob.status.in_(["QUEUED", "RETRY", "DISPATCHED", "RUNNING"]), *job_filter)
    failed_jobs = _count(db, CollectionJob, CollectionJob.status == "FAILED", *job_filter)
    unhealthy_sources = _count(db, SourceHealth, SourceHealth.state == "UNHEALTHY")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "sources": source_count,
            "raw_evidence": _count(db, RawObject, *raw_filter),
            "canonical_records": canonical_count,
            "unique_evidence": max(0, canonical_count - duplicate_count),
            "duplicates": duplicate_count,
            "active_jobs": active_jobs,
        },
        "watchlists": [{
            "id": str(w.id), "title": w.name, "objective": w.objective,
            "priority": w.priority.value, "status": w.status.value,
            "updated_at": w.updated_at.isoformat(),
            "locations": locations_by_watchlist[str(w.id)],
            "record_count": record_counts.get(w.id, (0, 0))[0],
            "source_count": record_counts.get(w.id, (0, 0))[1],
        } for w in watchlists],
        "records": records,
        "sources": [{
            "id": str(source.id), "name": source.name, "category": source.source_class,
            "enabled": source.enabled, "health": source_health.get(str(source.id), "UNKNOWN"),
        } for source in sources],
        "timeline": timeline[:20],
        "pipeline": {
            "sources_enabled": enabled_source_count,
            "sources_total": source_count,
            "sources_unhealthy": unhealthy_sources,
            "workers_live": live_workers,
            "workers_total": len(workers),
            "jobs_failed": failed_jobs,
            "jobs_active": active_jobs,
            "raw_stored": _count(db, RawObject, *raw_filter),
            "canonical_ready": canonical_count,
        },
    }


def build_lineage(db: Session, record_id: str, user) -> dict | None:
    record = db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == record_id, *_record_filter(user)))
    if record is None:
        return None

    source = db.get(Source, record.source_id) if record.source_id else None
    raw = db.scalar(select(RawObject).where(RawObject.evidence_id == record.evidence_id, *_raw_filter(user)))
    cluster_ids = select(DuplicateClusterMember.cluster_id).where(DuplicateClusterMember.record_id == record_id)
    related = db.execute(
        select(CanonicalRecord.record_id, CanonicalRecord.title, Source.name)
        .distinct()
        .join(DuplicateClusterMember, DuplicateClusterMember.record_id == CanonicalRecord.record_id)
        .outerjoin(Source, Source.id == CanonicalRecord.source_id)
        .where(DuplicateClusterMember.cluster_id.in_(cluster_ids), CanonicalRecord.record_id != record_id, *_record_filter(user))
        .limit(20)
    ).all()
    watchlist = db.get(Watchlist, record.watchlist_id) if record.watchlist_id else None
    return {
        "record": {"id": record.record_id, "title": record.title or "Untitled evidence"},
        "source": {"id": str(source.id), "name": source.name, "category": source.source_class} if source else None,
        "raw": {"id": raw.evidence_id, "retrieved_at": raw.retrieved_at.isoformat()} if raw else None,
        "related": [{"id": row_id, "title": title or "Untitled evidence", "source": name or "Unknown source"} for row_id, title, name in related],
        "watchlist": {"id": str(watchlist.id), "name": watchlist.name} if watchlist else None,
    }
