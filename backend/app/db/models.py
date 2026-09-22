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
