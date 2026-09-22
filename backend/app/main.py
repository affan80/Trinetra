import uuid
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.security import bearer, create_access_token, decode_access_token, hash_password, verify_password
from backend.app.db.database import Base, engine, get_db
from backend.app.db.models import *
from backend.app.schemas import LoginIn, RegisterIn, WatchlistIn, WatchlistPatch
from backend.app.services.monitoring_profile_builder import build
from backend.app.services.query_expander import expand
from backend.app.services.requirement_parser import parse_watchlist

app = FastAPI(title="TRINETRA Layer 1", version="1.0.0")

@app.on_event("startup")
def startup(): Base.metadata.create_all(engine)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials: raise HTTPException(401, "Authentication required")
    try: user_id = uuid.UUID(decode_access_token(credentials.credentials)["sub"])
    except (ValueError, KeyError): raise HTTPException(401, "Authentication required")
    user = db.get(User, user_id)
    if not user: raise HTTPException(401, "Authentication required")
    return user

def require_roles(*roles):
    def dependency(user=Depends(current_user)):
        if user.role.value not in roles: raise HTTPException(403, "Insufficient permissions")
        return user
    return dependency

def audit(db, event, user, watchlist, old=None, new=None):
    db.add(AuditLog(event_type=event, user_id=user.id, watchlist_id=watchlist.id, old_value=old, new_value=new)); db.commit()

def find_watchlist(wid, db):
    w = db.get(Watchlist, wid)
    if not w or w.status == WatchlistStatus.ARCHIVED: raise HTTPException(404, "Watchlist not found")
    return w

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
    w.refresh_interval_minutes = data.collection_policy["refresh_interval_minutes"]

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
    return [{"id": str(w.id), "name": w.name, "status": w.status.value, "priority": w.priority.value, "updated_at": w.updated_at} for w in db.scalars(select(Watchlist).where(Watchlist.status != WatchlistStatus.ARCHIVED)).all()]

@app.get(settings.api_v1_prefix + "/watchlists/{wid}")
def get_watchlist(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    w = find_watchlist(wid, db); return {"id": str(w.id), **serialize_watchlist(w, db), "status": w.status.value, "created_at": w.created_at, "updated_at": w.updated_at}

@app.patch(settings.api_v1_prefix + "/watchlists/{wid}")
def update_watchlist(wid: uuid.UUID, data: WatchlistPatch, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    w = find_watchlist(wid, db)
    if w.status in {WatchlistStatus.ACTIVE, WatchlistStatus.PAUSED}: w.status = WatchlistStatus.DRAFT
    w.name, w.description, w.objective, w.priority = data.name, data.description, data.objective, data.priority; write_children(w, data, db); db.commit(); db.refresh(w); audit(db, "WATCHLIST_UPDATED", user, w); return {"id": str(w.id), **serialize_watchlist(w, db), "status": w.status.value}

def transition(w, target):
    allowed = {WatchlistStatus.DRAFT: {WatchlistStatus.VALIDATED, WatchlistStatus.ARCHIVED}, WatchlistStatus.VALIDATED: {WatchlistStatus.ACTIVE, WatchlistStatus.ARCHIVED}, WatchlistStatus.ACTIVE: {WatchlistStatus.PAUSED, WatchlistStatus.ARCHIVED}, WatchlistStatus.PAUSED: {WatchlistStatus.ACTIVE, WatchlistStatus.ARCHIVED}}
    if target not in allowed.get(w.status, set()): raise HTTPException(409, f"Invalid transition from {w.status.value} to {target.value}")
    w.status = target

def lifecycle(wid, target, event, db, user):
    w = find_watchlist(wid, db); transition(w, target); db.commit(); audit(db, event, user, w); return {"id": str(w.id), "status": w.status.value}

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
    w = find_watchlist(wid, db); return {"queries": expand(parse_watchlist(serialize_watchlist(w, db)))}

@app.post(settings.api_v1_prefix + "/watchlists/{wid}/compile")
def compile_profile(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_roles("ADMIN", "ANALYST"))):
    w = find_watchlist(wid, db)
    if w.status not in {WatchlistStatus.VALIDATED, WatchlistStatus.ACTIVE}: raise HTTPException(409, "Watchlist must be validated before compilation")
    requirement = parse_watchlist(serialize_watchlist(w, db)); queries = expand(requirement); previous = db.scalar(select(MonitoringProfile).where(MonitoringProfile.watchlist_id == w.id).order_by(MonitoringProfile.version.desc())); version = previous.version + 1 if previous else 1
    payload = build(w, requirement, queries, version); profile = MonitoringProfile(watchlist_id=w.id, version=version, status="ACTIVE", payload=payload); db.add(profile); db.flush(); db.add_all([GeneratedQuery(profile_id=profile.id, query=q["query"], language=q["language"], method=q["method"], generated_from=q["generated_from"]) for q in queries]); db.commit(); audit(db, "WATCHLIST_COMPILED", user, w, new={"version": version}); return payload

@app.get(settings.api_v1_prefix + "/watchlists/{wid}/monitoring-profile")
def monitoring_profile(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    w = find_watchlist(wid, db); p = db.scalar(select(MonitoringProfile).where(MonitoringProfile.watchlist_id == w.id).order_by(MonitoringProfile.version.desc()))
    if not p: raise HTTPException(404, "No compiled profile")
    return p.payload

@app.get(settings.api_v1_prefix + "/watchlists/{wid}/audit")
def audit_history(wid: uuid.UUID, db: Session = Depends(get_db), user=Depends(current_user)):
    find_watchlist(wid, db); return [{"event_type": x.event_type, "timestamp": x.timestamp, "old_value": x.old_value, "new_value": x.new_value} for x in db.scalars(select(AuditLog).where(AuditLog.watchlist_id == wid).order_by(AuditLog.timestamp.desc())).all()]
