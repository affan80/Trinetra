import uuid
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.security import bearer, create_access_token, decode_access_token, hash_password, verify_password
from backend.app.db.database import Base, engine, get_db
from backend.app.db.models import *
from backend.app.schemas import LoginIn, RegisterIn, WatchlistIn, WatchlistPatch
from backend.app.services.monitoring_profile_builder import build
from backend.app.services.query_expander import expand
from backend.app.services.requirement_parser import parse_watchlist

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="TRINETRA Layer 1", version="1.0.0", lifespan=lifespan)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials: raise HTTPException(401, "Authentication required")
    try: user_id = uuid.UUID(decode_access_token(credentials.credentials)["sub"])
    except (ValueError, KeyError): raise HTTPException(401, "Authentication required")
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, "Authentication required")
    return user


@app.get(settings.api_v1_prefix + "/overview")
def overview(db: Session = Depends(get_db), user=Depends(current_user)):
    from backend.app.services.overview import build_overview
    return build_overview(db, user)


@app.get(settings.api_v1_prefix + "/source-audit")
def source_audit(user=Depends(current_user)):
    report = Path(os.getenv("SOURCE_AUDIT_REPORT", "artifacts/source_audit_live.json"))
    try:
        return json.loads(report.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "NOT_STARTED", "started_at": None, "updated_at": None,
                "summary": {"total": 0, "completed": 0, "collected": 0, "failed": 0, "blocked": 0,
                            "forbidden": 0, "skipped": 0, "rss_feeds": 0, "rss_entries": 0}, "sources": []}


@app.get(settings.api_v1_prefix + "/overview/lineage/{record_id}")
def overview_lineage(record_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    from backend.app.services.overview import build_lineage
    lineage = build_lineage(db, record_id, user)
    if lineage is None:
        raise HTTPException(404, "Evidence record not found")
    return lineage

def require_roles(*roles):
    def dependency(user=Depends(current_user)):
        if user.role.value not in roles: raise HTTPException(403, "Insufficient permissions")
        return user
    return dependency

def audit(db, event, user, watchlist, old=None, new=None):
    db.add(AuditLog(event_type=event, user_id=user.id, watchlist_id=watchlist.id if watchlist else None, old_value=old, new_value=new)); db.commit()

def find_watchlist(wid, db, user=None):
    w = db.get(Watchlist, wid)
    if not w or w.status == WatchlistStatus.ARCHIVED: raise HTTPException(404, "Watchlist not found")
    if user and user.role != Role.ADMIN and w.created_by != user.id: raise HTTPException(404, "Watchlist not found")
    return w

def ensure_record_access(record, db, user):
    if not record: raise HTTPException(404, "Record not found")
    if record.watchlist_id: find_watchlist(record.watchlist_id, db, user)
    elif user.role != Role.ADMIN: raise HTTPException(404, "Record not found")
    return record

def ensure_plan_access(plan, db, user):
    if not plan: raise HTTPException(404, "Collection plan not found")
    profile = db.get(MonitoringProfile, plan.profile_id)
    if not profile: raise HTTPException(404, "Collection plan not found")
    find_watchlist(profile.watchlist_id, db, user)
    return plan

def visible_record(record_id, db, user):
    try: ensure_record_access(db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == record_id)), db, user); return True
    except HTTPException: return False

def serialize_watchlist(w, db):
    entities = [db.get(Entity, x.entity_id) for x in w.entities]
    locations = [db.get(Location, x.location_id) for x in w.locations]
    return {"name": w.name, "description": w.description, "objective": w.objective, "priority": w.priority,
      "subjects": [x.value for x in w.subjects],
      "entities": [{"name": e.name, "type": e.type.value, "aliases": [a.value for a in e.aliases]} for e in entities if e],
      "keywords": [x.value for x in w.keywords if x.kind == KeywordKind.INCLUDE],
      "exclude_keywords": [x.value for x in w.keywords if x.kind == KeywordKind.EXCLUDE],
      "locations": [{"name": l.name, "country": l.country, "region": l.region, "city": l.city, "latitude": l.latitude, "longitude": l.longitude, "location_type": l.location_type, "precision": l.precision} for l in locations if l],
      "languages": [x.code for x in w.languages], "source_classes": [x.source_class for x in w.sources],
      "collection_policy": {"refresh_interval_minutes": w.refresh_interval_minutes},
      "alert_rules": [{"type": x.type, "enabled": x.enabled, "threshold": x.threshold, "config": x.config} for x in w.alert_rules]}

def write_children(w, data, db):
    w.subjects = [WatchlistSubject(value=x) for x in dict.fromkeys(data.subjects)]
    w.keywords = [WatchlistKeyword(value=x, kind=KeywordKind.INCLUDE) for x in dict.fromkeys(data.keywords)] + [WatchlistKeyword(value=x, kind=KeywordKind.EXCLUDE) for x in dict.fromkeys(data.exclude_keywords)]
    w.languages = [WatchlistLanguage(code=x) for x in data.languages]; w.sources = [WatchlistSource(source_class=x) for x in data.source_classes]
    w.alert_rules = [AlertRule(type=x.type, enabled=x.enabled, threshold=x.threshold, config=x.config) for x in data.alert_rules]
    w.entities = []
    for item in data.entities:
        e = Entity(name=item.name, type=item.type); e.aliases = [EntityAlias(value=a) for a in dict.fromkeys(item.aliases)]; db.add(e); db.flush(); w.entities.append(WatchlistEntity(entity_id=e.id))
    w.locations = []
    for item in data.locations:
        l = Location(**item.model_dump()); db.add(l); db.flush(); w.locations.append(WatchlistLocation(location_id=l.id))
    w.refresh_interval_minutes = data.collection_policy.get("refresh_interval_minutes", 15)

@app.get("/health")
def health(): return {"status": "healthy"}

@app.post(settings.api_v1_prefix + "/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)): raise HTTPException(409, "User already exists")
    user = User(email=data.email, password_hash=hash_password(data.password), role=Role.ANALYST); db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_access_token(str(user.id), user.role.value), "token_type": "bearer"}

@app.post(settings.api_v1_prefix + "/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.password_hash): raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_access_token(str(user.id), user.role.value), "token_type": "bearer"}

@app.post(settings.api_v1_prefix + "/watchlists")
def create_watchlist(data: WatchlistIn, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    w = Watchlist(name=data.name, description=data.description, objective=data.objective, priority=data.priority, created_by=user.id); db.add(w); db.flush(); write_children(w, data, db); db.commit(); db.refresh(w); audit(db, "WATCHLIST_CREATED", user, w); return {"id": str(w.id), **serialize_watchlist(w, db), "status": w.status.value}

@app.get(settings.api_v1_prefix + "/watchlists")
def list_watchlists(db: Session = Depends(get_db), user=Depends(current_user)):
    query = select(Watchlist).where(Watchlist.status != WatchlistStatus.ARCHIVED)
    if user.role != Role.ADMIN: query = query.where(Watchlist.created_by == user.id)
    return [{"id": str(w.id), "name": w.name, "status": w.status.value, "priority": w.priority.value, "updated_at": w.updated_at} for w in db.scalars(query.limit(100)).all()]

@app.get(settings.api_v1_prefix + "/watchlists/{wid}")
def get_watchlist(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    w = find_watchlist(wid, db, user); return {"id": str(w.id), **serialize_watchlist(w, db), "status": w.status.value, "created_at": w.created_at, "updated_at": w.updated_at}

@app.patch(settings.api_v1_prefix + "/watchlists/{wid}")
def update_watchlist(wid: uuid.UUID, data: WatchlistPatch, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    w = find_watchlist(wid, db, user)
    if w.status in {WatchlistStatus.ACTIVE, WatchlistStatus.PAUSED}: w.status = WatchlistStatus.DRAFT
    w.name, w.description, w.objective, w.priority = data.name, data.description, data.objective, data.priority; write_children(w, data, db); db.commit(); db.refresh(w); audit(db, "WATCHLIST_UPDATED", user, w); return {"id": str(w.id), **serialize_watchlist(w, db), "status": w.status.value}

def transition(w, target):
    allowed = {WatchlistStatus.DRAFT: {WatchlistStatus.VALIDATED, WatchlistStatus.ARCHIVED}, WatchlistStatus.VALIDATED: {WatchlistStatus.ACTIVE, WatchlistStatus.ARCHIVED}, WatchlistStatus.ACTIVE: {WatchlistStatus.PAUSED, WatchlistStatus.ARCHIVED}, WatchlistStatus.PAUSED: {WatchlistStatus.ACTIVE, WatchlistStatus.ARCHIVED}}
    if target not in allowed.get(w.status, set()): raise HTTPException(409, f"Invalid transition from {w.status.value} to {target.value}")
    w.status = target

def lifecycle(wid, target, event, db, user):
    w = find_watchlist(wid, db, user); transition(w, target); db.commit(); audit(db, event, user, w); return {"id": str(w.id), "status": w.status.value}

@app.post(settings.api_v1_prefix + "/watchlists/{wid}/validate")
def validate(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))): return lifecycle(wid, WatchlistStatus.VALIDATED, "WATCHLIST_VALIDATED", db, user)
@app.post(settings.api_v1_prefix + "/watchlists/{wid}/activate")
def activate(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))): return lifecycle(wid, WatchlistStatus.ACTIVE, "WATCHLIST_ACTIVATED", db, user)
@app.post(settings.api_v1_prefix + "/watchlists/{wid}/pause")
def pause(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))): return lifecycle(wid, WatchlistStatus.PAUSED, "WATCHLIST_PAUSED", db, user)
@app.post(settings.api_v1_prefix + "/watchlists/{wid}/archive")
def archive(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))): return lifecycle(wid, WatchlistStatus.ARCHIVED, "WATCHLIST_ARCHIVED", db, user)

@app.get(settings.api_v1_prefix + "/watchlists/{wid}/preview-queries")
def preview_queries(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    w = find_watchlist(wid, db, user); return {"queries": expand(parse_watchlist(serialize_watchlist(w, db)))}

@app.post(settings.api_v1_prefix + "/watchlists/{wid}/compile")
def compile_profile(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    w = find_watchlist(wid, db, user)
    if w.status not in {WatchlistStatus.VALIDATED, WatchlistStatus.ACTIVE}: raise HTTPException(409, "Watchlist must be validated before compilation")
    requirement = parse_watchlist(serialize_watchlist(w, db)); queries = expand(requirement); previous = db.scalar(select(MonitoringProfile).where(MonitoringProfile.watchlist_id == w.id).order_by(MonitoringProfile.version.desc())); version = previous.version + 1 if previous else 1
    payload = build(w, requirement, queries, version); profile = MonitoringProfile(watchlist_id=w.id, version=version, status="ACTIVE", payload=payload); db.add(profile); db.flush(); payload["profile_id"] = str(profile.id); db.execute(update(MonitoringProfile).where(MonitoringProfile.id == profile.id).values(payload=payload)); db.add_all([GeneratedQuery(profile_id=profile.id, query=q["query"], language=q["language"], method=q["method"], generated_from=q["generated_from"]) for q in queries]); db.commit(); audit(db, "WATCHLIST_COMPILED", user, w, new={"version": version}); return payload

@app.get(settings.api_v1_prefix + "/watchlists/{wid}/monitoring-profile")
def monitoring_profile(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    w = find_watchlist(wid, db, user); p = db.scalar(select(MonitoringProfile).where(MonitoringProfile.watchlist_id == w.id).order_by(MonitoringProfile.version.desc()))
    if not p: raise HTTPException(404, "No compiled profile")
    return p.payload

@app.get(settings.api_v1_prefix + "/watchlists/{wid}/audit")
def audit_history(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    find_watchlist(wid, db, user); return [{"event_type": x.event_type, "timestamp": x.timestamp, "old_value": x.old_value, "new_value": x.new_value} for x in db.scalars(select(AuditLog).where(AuditLog.watchlist_id == wid).order_by(AuditLog.timestamp.desc()).limit(100)).all()]
from backend.app.layer2_schemas import PlanCreate, SourceCreate, WorkerHeartbeat
from backend.app.security import validate_source_config
from backend.app.services.dispatch_service import dispatch
from backend.app.workers.dispatch_tasks import dispatch_collection_job
from backend.app.services.job_generator import generate
from backend.app.services.scheduler_service import schedule
from backend.app.services.source_health_service import record as record_source_health
from backend.app.services.adapter_registry import ADAPTERS
from backend.app.collectors.adapters.rss import collect as collect_rss
from backend.app.services.checkpoint_service import get as get_checkpoint, save as save_checkpoint
from backend.app.services.evidence_service import preserve
from backend.app.services.object_store import ObjectStore
from backend.app.dedup.services.dedup_pipeline import process as process_dedup

@app.post(settings.api_v1_prefix + "/records/{record_id}/deduplicate")
def deduplicate_record(record_id: str, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    try: return process_dedup(db, record_id, user.id)
    except ValueError as exc: raise HTTPException(404, str(exc))

@app.get(settings.api_v1_prefix + "/records/{record_id}/quality")
def record_quality(record_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    ensure_record_access(db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == record_id)), db, user); row = db.scalar(select(RecordQuality).where(RecordQuality.record_id == record_id))
    if not row: raise HTTPException(404, "Quality annotation not found")
    return {"record_id": record_id, "status": row.status.value, "score": row.quality_score, "version": row.quality_version, "components": row.components, "flags": row.flags}

@app.get(settings.api_v1_prefix + "/records/{record_id}/duplicates")
def record_duplicates(record_id: str, limit: int = 100, offset: int = 0, db: Session = Depends(get_db), user=Depends(current_user)):
    ensure_record_access(db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == record_id)), db, user); limit = max(1, min(limit, 100)); members = db.scalars(select(DuplicateClusterMember).where(DuplicateClusterMember.record_id == record_id).offset(offset).limit(limit)).all()
    return [{"cluster_id": str(member.cluster_id), "record_id": member.record_id, "relationship": member.relationship_type, "score": member.similarity_score, "method": member.detection_method} for member in members]

@app.get(settings.api_v1_prefix + "/records/{record_id}/similarities")
def record_similarities(record_id: str, limit: int = 100, offset: int = 0, db: Session = Depends(get_db), user=Depends(current_user)):
    ensure_record_access(db.scalar(select(CanonicalRecord).where(CanonicalRecord.record_id == record_id)), db, user); limit = max(1, min(limit, 100)); rows = db.scalars(select(RecordSimilarity).where(or_(RecordSimilarity.record_a_id == record_id, RecordSimilarity.record_b_id == record_id)).offset(offset).limit(limit)).all()
    return [{"record_a_id": row.record_a_id, "record_b_id": row.record_b_id, "type": row.similarity_type, "score": row.similarity_score, "signals": row.signals, "decision": row.decision, "version": row.decision_version} for row in rows if visible_record(row.record_a_id, db, user) and visible_record(row.record_b_id, db, user)]

@app.get(settings.api_v1_prefix + "/duplicate-clusters/{cluster_id}/members")
def cluster_members(cluster_id: uuid.UUID, limit: int = 100, offset: int = 0, db: Session = Depends(get_db), user=Depends(current_user)):
    limit = max(1, min(limit, 100)); cluster = db.get(DuplicateCluster, cluster_id)
    if not cluster: raise HTTPException(404, "Duplicate cluster not found")
    rows = db.scalars(select(DuplicateClusterMember).where(DuplicateClusterMember.cluster_id == cluster_id).offset(offset).limit(limit)).all()
    visible = [row for row in rows if visible_record(row.record_id, db, user)]
    if not visible and user.role != Role.ADMIN: raise HTTPException(404, "Duplicate cluster not found")
    representative = cluster.representative_record_id if visible_record(cluster.representative_record_id, db, user) else visible[0].record_id
    return {"cluster_id": str(cluster.id), "representative_record_id": representative, "member_count": len(visible) if user.role != Role.ADMIN else cluster.member_count, "members": [{"record_id": row.record_id, "relationship": row.relationship_type, "score": row.similarity_score, "explanation": row.explanation} for row in visible]}


@app.post(settings.api_v1_prefix + "/sources")
def create_source(data: SourceCreate, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN"))):
    try: validate_source_config(data.allowed_domains, data.config)
    except ValueError as exc: raise HTTPException(422, str(exc))
    if db.scalar(select(Source).where(Source.name == data.name)): raise HTTPException(409, "Source already exists")
    source = Source(**data.model_dump()); db.add(source); db.commit(); db.refresh(source)
    audit(db, "SOURCE_CREATED", user, None, new={"source_id": str(source.id), "name": source.name})
    return {"id": str(source.id), "name": source.name, "source_class": source.source_class, "adapter_name": source.adapter_name, "enabled": source.enabled}

@app.get(settings.api_v1_prefix + "/sources")
def list_sources(db: Session = Depends(get_db), user=Depends(current_user)):
    return [{"id": str(s.id), "name": s.name, "source_class": s.source_class, "adapter_name": s.adapter_name, "enabled": s.enabled, "rate_limit_per_minute": s.rate_limit_per_minute} for s in db.scalars(select(Source).limit(100)).all()]

@app.get(settings.api_v1_prefix + "/collectors")
def collectors(user=Depends(current_user)): return {"adapters": list(ADAPTERS)}

@app.post(settings.api_v1_prefix + "/collectors/heartbeat")
def heartbeat(data: WorkerHeartbeat, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    from datetime import datetime, timezone
    worker = db.scalar(select(CollectorWorker).where(CollectorWorker.worker_name == data.worker_name))
    if not worker: worker = CollectorWorker(worker_name=data.worker_name); db.add(worker)
    worker.adapter_names = data.adapter_names; worker.status = "READY"; worker.last_heartbeat_at = datetime.now(timezone.utc); db.commit()
    return {"worker_name": worker.worker_name, "status": worker.status}

@app.post(settings.api_v1_prefix + "/collection-plans")
def create_collection_plans(data: PlanCreate, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    try:
        profile_id = uuid.UUID(data.profile_id)
        source_ids = [uuid.UUID(s_id) for s_id in data.source_ids]
    except ValueError:
        raise HTTPException(422, "Invalid UUID format")
    
    profile = db.get(MonitoringProfile, profile_id)
    if not profile or profile.status != "ACTIVE": raise HTTPException(404, "Active monitoring profile not found")
    find_watchlist(profile.watchlist_id, db, user)
    
    sources = [db.get(Source, s_id) for s_id in source_ids]
    if any(s is None or not s.enabled for s in sources): raise HTTPException(422, "All sources must exist and be enabled")
    allowed = set(profile.payload.get("source_classes", []))
    if any(s.source_class not in allowed for s in sources): raise HTTPException(422, "Source class is not present in the monitoring profile")
    result = []
    for source in sources:
        plan = CollectionPlan(profile_id=profile.id, source_id=source.id, created_by=user.id, policy={"adapter_name": source.adapter_name, "allowed_domains": source.allowed_domains})
        db.add(plan); db.flush(); schedule_row = schedule(db, plan.id, data.interval_seconds)
        jobs = generate(db, plan, profile.payload)
        result.append({"plan_id": str(plan.id), "source_id": str(source.id), "schedule_id": str(schedule_row.id), "jobs_created": len(jobs)})
    audit(db, "COLLECTION_PLAN_CREATED", user, None, new={"profile_id": str(profile.id), "plans": result})
    return {"profile_id": str(profile.id), "plans": result}

@app.get(settings.api_v1_prefix + "/collection-plans")
def list_collection_plans(db: Session = Depends(get_db), user=Depends(current_user)):
    plans = db.scalars(select(CollectionPlan).limit(100)).all()
    return [{"id": str(p.id), "profile_id": str(p.profile_id), "source_id": str(p.source_id), "status": p.status, "policy": p.policy} for p in plans if user.role == Role.ADMIN or not _plan_hidden(p, db, user)]

@app.get(settings.api_v1_prefix + "/collection-jobs")
def list_collection_jobs(db: Session = Depends(get_db), user=Depends(current_user)):
    jobs = db.scalars(select(CollectionJob).order_by(CollectionJob.created_at.desc()).limit(100)).all()
    return [{"id": str(j.id), "plan_id": str(j.plan_id), "source_id": str(j.source_id), "query": j.query, "language": j.language, "fingerprint": j.fingerprint, "status": j.status, "attempts": j.attempts} for j in jobs if user.role == Role.ADMIN or not _plan_hidden(db.get(CollectionPlan, j.plan_id), db, user)]

def _plan_hidden(plan, db, user):
    try: ensure_plan_access(plan, db, user); return False
    except HTTPException: return True

@app.post(settings.api_v1_prefix + "/collection-jobs/{job_id}/dispatch")
def dispatch_job(job_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    job = db.get(CollectionJob, job_id)
    if not job: raise HTTPException(404, "Collection job not found")
    ensure_plan_access(db.get(CollectionPlan, job.plan_id), db, user)
    if job.status not in {"QUEUED", "RETRY"}: raise HTTPException(409, "Job is not dispatchable")
    payload = dispatch(job); job.status = "DISPATCHED"; job.dispatched_at = now(); job.attempts += 1; db.commit()
    return {"job_id": str(job.id), "status": "DISPATCHED", "payload": payload}

@app.post(settings.api_v1_prefix + "/collection-jobs/{job_id}/celery-dispatch")
def celery_dispatch(job_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    job = db.get(CollectionJob, job_id)
    if not job: raise HTTPException(404, "Collection job not found")
    ensure_plan_access(db.get(CollectionPlan, job.plan_id), db, user)
    task = dispatch_collection_job.delay(str(job.id))
    return {"job_id": str(job.id), "task_id": task.id, "status": "QUEUED_FOR_WORKER"}

@app.post(settings.api_v1_prefix + "/sources/{source_id}/health")
def source_health(source_id: uuid.UUID, ok: bool = True, error: str | None = None, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    if not db.get(Source, source_id): raise HTTPException(404, "Source not found")
    record_source_health(db, source_id, ok, error)
    return {"source_id": str(source_id), "state": "HEALTHY" if ok else "UNHEALTHY"}

@app.post(settings.api_v1_prefix + "/collection-jobs/{job_id}/collect/rss")
def collect_rss_job(job_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    job = db.get(CollectionJob, job_id); source = db.get(Source, job.source_id) if job else None
    if not job or not source: raise HTTPException(404, "Collection job or source not found")
    ensure_plan_access(db.get(CollectionPlan, job.plan_id), db, user)
    feed_url = job.payload.get("feed_url") or source.config.get("rss_url")
    if not feed_url: raise HTTPException(422, "No trusted RSS URL is configured for this source")
    try:
        result = collect_rss(feed_url, source.allowed_domains, get_checkpoint(db, source.id))
        saved = preserve(db, job, source, result, object_store=ObjectStore()); save_checkpoint(db, source.id, result["checkpoint_after"])
        job.status = "SUCCEEDED"; db.commit()
        return {"job_id": str(job.id), "status": "SUCCEEDED", "items_collected": len(result["entries"]), **saved}
    except ValueError as exc:
        job.status = "FAILED"; db.commit(); raise HTTPException(502, str(exc))
