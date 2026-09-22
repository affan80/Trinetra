from backend.app.workers.celery_app import celery_app

@celery_app.task(name="trinetra.dispatch_collection_job")
def dispatch_collection_job(job_id: str):
    # Layer 3 owns collection. This task only provides the stable handoff contract.
    return {"job_id": job_id, "status": "READY_FOR_LAYER3"}
