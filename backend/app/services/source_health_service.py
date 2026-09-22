from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.db.models import SourceHealth

def record(db, source_id, ok: bool, error: str | None = None):
    row = db.scalar(select(SourceHealth).where(SourceHealth.source_id == source_id))
    if not row: row = SourceHealth(source_id=source_id); db.add(row)
    row.state = "HEALTHY" if ok else "UNHEALTHY"
    row.consecutive_failures = 0 if ok else row.consecutive_failures + 1
    row.last_error = error; row.last_checked_at = datetime.now(timezone.utc); db.commit()
