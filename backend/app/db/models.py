import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.database import Base


def now(): return datetime.now(timezone.utc)
def uid(): return uuid.uuid4()


class Role(str, enum.Enum): ADMIN = "ADMIN"; ANALYST = "ANALYST"; VIEWER = "VIEWER"
class Priority(str, enum.Enum): LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; CRITICAL = "CRITICAL"
class WatchlistStatus(str, enum.Enum): DRAFT = "DRAFT"; VALIDATED = "VALIDATED"; ACTIVE = "ACTIVE"; PAUSED = "PAUSED"; ERROR = "ERROR"; ARCHIVED = "ARCHIVED"
class EntityType(str, enum.Enum): PERSON="PERSON"; ORGANISATION="ORGANISATION"; LOCATION="LOCATION"; ASSET="ASSET"; FACILITY="FACILITY"; SYSTEM="SYSTEM"; EVENT="EVENT"; OTHER="OTHER"
class KeywordKind(str, enum.Enum): INCLUDE="INCLUDE"; EXCLUDE="EXCLUDE"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.ANALYST)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Watchlist(Base):
    __tablename__ = "watchlists"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.MEDIUM)
    status: Mapped[WatchlistStatus] = mapped_column(Enum(WatchlistStatus), default=WatchlistStatus.DRAFT)
    refresh_interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    subjects = relationship("WatchlistSubject", cascade="all, delete-orphan")
    keywords = relationship("WatchlistKeyword", cascade="all, delete-orphan")
    locations = relationship("WatchlistLocation", cascade="all, delete-orphan")
    languages = relationship("WatchlistLanguage", cascade="all, delete-orphan")
    sources = relationship("WatchlistSource", cascade="all, delete-orphan")
    entities = relationship("WatchlistEntity", cascade="all, delete-orphan")
    alert_rules = relationship("AlertRule", cascade="all, delete-orphan")


class WatchlistSubject(Base):
    __tablename__ = "watchlist_subjects"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); value: Mapped[str] = mapped_column(String(255))
class WatchlistKeyword(Base):
    __tablename__ = "watchlist_keywords"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); value: Mapped[str] = mapped_column(String(255)); kind: Mapped[KeywordKind] = mapped_column(Enum(KeywordKind))
class WatchlistLanguage(Base):
    __tablename__ = "watchlist_languages"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); code: Mapped[str] = mapped_column(String(10))
class WatchlistSource(Base):
    __tablename__ = "watchlist_sources"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); source_class: Mapped[str] = mapped_column(String(40))
class Entity(Base):
    __tablename__ = "entities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); name: Mapped[str] = mapped_column(String(255)); type: Mapped[EntityType] = mapped_column(Enum(EntityType)); aliases = relationship("EntityAlias", cascade="all, delete-orphan")
class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id")); value: Mapped[str] = mapped_column(String(255))
class WatchlistEntity(Base):
    __tablename__ = "watchlist_entities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); entity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entities.id"))
class Location(Base):
    __tablename__ = "locations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); name: Mapped[str] = mapped_column(String(255)); country: Mapped[str] = mapped_column(String(100), default=""); region: Mapped[str] = mapped_column(String(100), default=""); city: Mapped[str] = mapped_column(String(100), default=""); latitude: Mapped[float | None] = mapped_column(Float); longitude: Mapped[float | None] = mapped_column(Float); location_type: Mapped[str] = mapped_column(String(40)); precision: Mapped[str] = mapped_column(String(40), default="REGIONAL")
class WatchlistLocation(Base):
    __tablename__ = "watchlist_locations"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("locations.id"))
class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); type: Mapped[str] = mapped_column(String(60)); enabled: Mapped[bool] = mapped_column(Boolean, default=True); threshold: Mapped[float | None] = mapped_column(Float); config: Mapped[dict] = mapped_column(JSON, default=dict)
class MonitoringProfile(Base):
    __tablename__ = "monitoring_profiles"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); watchlist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlists.id")); version: Mapped[int] = mapped_column(Integer); status: Mapped[str] = mapped_column(String(20)); payload: Mapped[dict] = mapped_column(JSON); generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); __table_args__ = (UniqueConstraint("watchlist_id", "version"),)
class GeneratedQuery(Base):
    __tablename__ = "generated_queries"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitoring_profiles.id")); query: Mapped[str] = mapped_column(Text); language: Mapped[str] = mapped_column(String(10)); method: Mapped[str] = mapped_column(String(80)); generated_from: Mapped[list] = mapped_column(JSON)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid); event_type: Mapped[str] = mapped_column(String(80)); user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id")); watchlist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("watchlists.id")); timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now); old_value: Mapped[dict | None] = mapped_column(JSON); new_value: Mapped[dict | None] = mapped_column(JSON); metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    source_class: Mapped[str] = mapped_column(String(40))
    adapter_name: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_domains: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class CollectionPlan(Base):
    __tablename__ = "collection_plans"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitoring_profiles.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[str] = mapped_column(String(30), default="READY")
    policy: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CollectionSchedule(Base):
    __tablename__ = "collection_schedules"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_plans.id"), unique=True)
    interval_seconds: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class CollectionJob(Base):
    __tablename__ = "collection_jobs"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    plan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_plans.id"))
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("monitoring_profiles.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    query: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CollectionAttempt(Base):
    __tablename__ = "collection_attempts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_jobs.id"))
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceCheckpoint(Base):
    __tablename__ = "source_checkpoints"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), unique=True)
    cursor: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class SourceHealth(Base):
    __tablename__ = "source_health"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), unique=True)
    state: Mapped[str] = mapped_column(String(30), default="HEALTHY")
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionPolicy(Base):
    __tablename__ = "collection_policies"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    backoff_seconds: Mapped[int] = mapped_column(Integer, default=60)
    max_jobs_per_run: Mapped[int] = mapped_column(Integer, default=100)
    config: Mapped[dict] = mapped_column(JSON, default=dict)


class CollectorWorker(Base):
    __tablename__ = "collector_workers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    worker_name: Mapped[str] = mapped_column(String(150), unique=True)
    adapter_names: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="UNKNOWN")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CanonicalRecord(Base):
    __tablename__ = "canonical_records"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    record_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    evidence_id: Mapped[str] = mapped_column(String(80))
    source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sources.id"))
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("watchlists.id"))
    record_type: Mapped[str] = mapped_column(String(40))
    canonical_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    plain_text: Mapped[str] = mapped_column(Text, default="")
    primary_language: Mapped[str | None] = mapped_column(String(12))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    processing_quality: Mapped[dict] = mapped_column(JSON, default=dict)
    content_blocks: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QualityStatus(str, enum.Enum): VALID="VALID"; LOW_CONTENT="LOW_CONTENT"; EMPTY="EMPTY"; BOILERPLATE="BOILERPLATE"; ERROR_PAGE="ERROR_PAGE"; CAPTCHA="CAPTCHA"; LOGIN_REQUIRED="LOGIN_REQUIRED"; CORRUPT="CORRUPT"; PARTIAL="PARTIAL"; UNSUPPORTED="UNSUPPORTED"
class DuplicateType(str, enum.Enum): EXACT_RAW="EXACT_RAW"; EXACT_TEXT="EXACT_TEXT"; CANONICAL_URL="CANONICAL_URL"; DOCUMENT_VERSION="DOCUMENT_VERSION"; POSSIBLE_DUPLICATE="POSSIBLE_DUPLICATE"; RELATED_NOT_DUPLICATE="RELATED_NOT_DUPLICATE"
class ClusterStatus(str, enum.Enum): ACTIVE="ACTIVE"; MERGED="MERGED"; SPLIT="SPLIT"


class RecordQuality(Base):
    __tablename__ = "record_quality"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    record_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"), unique=True)
    status: Mapped[QualityStatus] = mapped_column(Enum(QualityStatus))
    quality_score: Mapped[float] = mapped_column(Float)
    quality_version: Mapped[str] = mapped_column(String(40))
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RecordFingerprint(Base):
    __tablename__ = "record_fingerprints"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    record_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"), unique=True, index=True)
    raw_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    normalized_text_hash: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str | None] = mapped_column(String(12))
    fingerprint_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DuplicateCluster(Base):
    __tablename__ = "duplicate_clusters"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    cluster_type: Mapped[str] = mapped_column(String(40))
    representative_record_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"))
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ClusterStatus] = mapped_column(Enum(ClusterStatus), default=ClusterStatus.ACTIVE)
    version: Mapped[int] = mapped_column(Integer, default=1)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class DuplicateClusterMember(Base):
    __tablename__ = "duplicate_cluster_members"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    cluster_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("duplicate_clusters.id"))
    record_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"))
    relationship_type: Mapped[str] = mapped_column(String(40))
    similarity_score: Mapped[float] = mapped_column(Float, default=1.0)
    detection_method: Mapped[str] = mapped_column(String(60))
    decision_version: Mapped[str] = mapped_column(String(40))
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("cluster_id", "record_id"),)


class RecordSimilarity(Base):
    __tablename__ = "record_similarities"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    record_a_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"))
    record_b_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"))
    similarity_type: Mapped[str] = mapped_column(String(40))
    similarity_score: Mapped[float] = mapped_column(Float)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    decision: Mapped[str] = mapped_column(String(40))
    decision_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("record_a_id", "record_b_id", "decision_version"),)


class DuplicateOverride(Base):
    __tablename__ = "duplicate_overrides"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    record_a_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"))
    record_b_id: Mapped[str] = mapped_column(ForeignKey("canonical_records.record_id"))
    override_type: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RawObject(Base):
    __tablename__ = "raw_objects"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    evidence_id: Mapped[str] = mapped_column(String(40), unique=True)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_jobs.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    watchlist_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("watchlists.id"))
    profile_version: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str] = mapped_column(Text)
    final_url: Mapped[str] = mapped_column(Text)
    adapter_type: Mapped[str] = mapped_column(String(40))
    object_uri: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(150))
    content_length: Mapped[int] = mapped_column(Integer)
    http_status: Mapped[int] = mapped_column(Integer)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(255))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    malware_status: Mapped[str] = mapped_column(String(30), default="NOT_SCANNED")
    collector_version: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CollectionProvenance(Base):
    __tablename__ = "collection_provenance"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    raw_object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_objects.id"))
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collection_jobs.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    collector_id: Mapped[str] = mapped_column(String(100))
    collector_version: Mapped[str] = mapped_column(String(40))
    adapter_type: Mapped[str] = mapped_column(String(40))
    requested_url: Mapped[str] = mapped_column(Text)
    final_url: Mapped[str] = mapped_column(Text)
    redirect_chain: Mapped[list] = mapped_column(JSON, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    http_headers_sanitized: Mapped[dict] = mapped_column(JSON, default=dict)
    collection_method: Mapped[str] = mapped_column(String(40))
    checkpoint_before: Mapped[dict] = mapped_column(JSON, default=dict)
    checkpoint_after: Mapped[dict] = mapped_column(JSON, default=dict)


class RobotsCache(Base):
    __tablename__ = "robots_cache"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uid)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), unique=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    allowed: Mapped[bool] = mapped_column(Boolean)
    raw_hash: Mapped[str] = mapped_column(String(64))
