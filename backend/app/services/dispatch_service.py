import json
import os
from datetime import datetime, timezone
from redis import Redis
from backend.app.db.models import CollectionJob

def client(): return Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

def dispatch(job: CollectionJob, redis_client=None):
    payload = {"job_id": str(job.id), "adapter_name": job.payload["adapter_name"], "source_id": str(job.source_id), "query": job.query, "language": job.language, "query_provenance": job.payload["query_provenance"], "security": job.payload["security"]}
    (redis_client or client()).rpush("trinetra:collection:jobs", json.dumps(payload, separators=(",", ":")))
    return payload
