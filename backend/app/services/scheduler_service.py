from datetime import datetime, timedelta, timezone
from backend.app.db.models import CollectionSchedule

def next_run(interval_seconds: int): return datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)

def schedule(db, plan_id, interval_seconds):
    row = CollectionSchedule(plan_id=plan_id, interval_seconds=interval_seconds, next_run_at=next_run(interval_seconds)); db.add(row); db.commit(); return row
