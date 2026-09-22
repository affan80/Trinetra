from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.db.models import EntityType, KeywordKind, Priority, WatchlistStatus

SOURCE_CLASSES = {"NEWS", "GOVERNMENT", "REPORT", "PUBLIC_SOCIAL", "BLOG", "FORUM", "PUBLIC_DATABASE", "IMAGE", "VIDEO", "AUDIO", "DOCUMENT"}
ALERT_TYPES = {"NEW_EVENT", "ACTIVITY_SPIKE", "NEW_ENTITY", "MEDIA_REUSE", "STRONG_CONTRADICTION", "HIGH_CONFIDENCE_CORROBORATION", "GEO_CHANGE", "SOURCE_CREDIBILITY_CHANGE"}

class Alias(BaseModel): value: str = Field(min_length=1, max_length=255)
class EntityIn(BaseModel): name: str = Field(min_length=1, max_length=255); type: EntityType; aliases: list[str] = []
class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=255); country: str = ""; region: str = ""; city: str = ""; latitude: float | None = Field(default=None, ge=-90, le=90); longitude: float | None = Field(default=None, ge=-180, le=180); location_type: str = "REGION"; precision: str = "REGIONAL"
class AlertRuleIn(BaseModel):
    type: str; enabled: bool = True; threshold: float | None = Field(default=None, ge=0, le=1); config: dict = {}
    @field_validator("type")
    @classmethod
    def valid_type(cls, v):
        if v not in ALERT_TYPES: raise ValueError("unsupported alert rule")
        return v
class WatchlistIn(BaseModel):
    name: str = Field(min_length=1, max_length=200); description: str = ""; objective: str = ""; priority: Priority = Priority.MEDIUM; subjects: list[str] = []; entities: list[EntityIn] = []; keywords: list[str] = []; exclude_keywords: list[str] = []; locations: list[LocationIn] = []; languages: list[str] = ["en"]; source_classes: list[str] = []; collection_policy: dict = {}; alert_rules: list[AlertRuleIn] = []
    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, v): return " ".join(str(v).split())
    @field_validator("languages")
    @classmethod
    def valid_languages(cls, values):
        if any(len(v) != 2 or not v.isalpha() or v != v.lower() for v in values): raise ValueError("languages must be lowercase ISO-style 2-letter codes")
        return list(dict.fromkeys(values))
    @field_validator("source_classes")
    @classmethod
    def valid_sources(cls, values):
        bad = set(values) - SOURCE_CLASSES
        if bad: raise ValueError(f"unsupported source class: {', '.join(sorted(bad))}")
        return list(dict.fromkeys(values))
    @field_validator("collection_policy")
    @classmethod
    def valid_policy(cls, value):
        interval = value.get("refresh_interval_minutes", 15)
        if not isinstance(interval, int) or interval < 1: raise ValueError("refresh interval must be positive")
        return {"refresh_interval_minutes": interval}
class WatchlistPatch(WatchlistIn): pass
class WatchlistOut(BaseModel): model_config = ConfigDict(from_attributes=True); id: str; name: str; description: str; objective: str; priority: Priority; status: WatchlistStatus; refresh_interval_minutes: int
class LoginIn(BaseModel): email: str; password: str = Field(min_length=8)
class RegisterIn(LoginIn): role: str = "ANALYST"
