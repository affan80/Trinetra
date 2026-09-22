from datetime import datetime, timezone
from sqlalchemy import select
from backend.app.db.models import CollectionJob, CollectionPlan
from backend.app.services.job_fingerprint import fingerprint

def generate(db, plan: CollectionPlan, profile: dict, limit: int = 100):
    jobs = []
    for item in profile.get("queries", [])[:limit]:
        fp = fingerprint(profile["profile_id"], plan.source_id, item["query"], item["language"])
        if db.scalar(select(CollectionJob).where(CollectionJob.fingerprint == fp)): continue
        job = CollectionJob(plan_id=plan.id, profile_id=plan.profile_id, source_id=plan.source_id, fingerprint=fp, query=item["query"], language=item["language"], payload={"adapter_name": plan.policy["adapter_name"], "source_id": str(plan.source_id), "query_provenance": item["generated_from"], "security": {"allowed_domains": plan.policy.get("allowed_domains", [])}})
        db.add(job); jobs.append(job)
    db.commit(); return jobs
