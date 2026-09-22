from datetime import datetime, timezone
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import select
from backend.app.db.database import SessionLocal
from backend.app.db.models import CollectionPlan, CollectionSchedule, MonitoringProfile
from backend.app.services.job_generator import generate
from backend.app.services.scheduler_service import next_run

def tick():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        for schedule in db.scalars(select(CollectionSchedule).where(CollectionSchedule.enabled.is_(True), CollectionSchedule.next_run_at <= now)).all():
            plan = db.get(CollectionPlan, schedule.plan_id); profile = db.get(MonitoringProfile, plan.profile_id) if plan else None
            if plan and profile and profile.status == "ACTIVE": generate(db, plan, profile.payload, limit=plan.policy.get("max_jobs_per_run", 100))
            schedule.next_run_at = next_run(schedule.interval_seconds)
        db.commit()
    finally: db.close()

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(tick, "interval", seconds=30, max_instances=1, coalesce=True)
    scheduler.start()
