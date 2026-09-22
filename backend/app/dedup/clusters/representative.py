from sqlalchemy import select
from backend.app.db.models import CanonicalRecord, DuplicateClusterMember, RecordQuality

def choose(db, cluster_id):
    # ponytail: cap representative scans; very large clusters need exemplar indexes.
    members = db.scalars(select(DuplicateClusterMember).where(DuplicateClusterMember.cluster_id == cluster_id).limit(1000)).all()
    rows = []
    for member in members:
        record = db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == member.record_id)); quality = db.scalar(select(RecordQuality).where(RecordQuality.record_id == member.record_id))
        rows.append((record, quality.quality_score if quality else 0.0))
    from datetime import datetime, timezone
    return min(rows, key=lambda item: (-(item[1]), item[0].published_at is None, item[0].published_at or item[0].retrieved_at or datetime.max.replace(tzinfo=timezone.utc)))[0] if rows else None
