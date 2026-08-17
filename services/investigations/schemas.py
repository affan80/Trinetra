"""Typed contracts between the analyst interface, agents, and collectors.

These models intentionally keep untrusted planner output away from runtime
configuration.  A planner may only return a validated :class:`CollectionPlan`.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InvestigationStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class SourceType(str, Enum):
    WEB = "web"
    NEWS = "news"
    OFFICIAL = "official"
    DOCUMENT = "document"
    SOCIAL = "social"
    IMAGE = "image"
    VIDEO = "video"


class InputKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    PDF = "pdf"
    DOCUMENT = "document"
    TEXT = "text"
    URL = "url"
    SCREENSHOT = "screenshot"
    SOCIAL_URL = "social_url"


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    objective: str = Field(min_length=3, max_length=2_000)
    target: str = Field(min_length=2, max_length=300)
    source_types: set[SourceType] = Field(
        default_factory=lambda: {SourceType.WEB, SourceType.NEWS, SourceType.OFFICIAL}
    )
    time_range_label: str = Field(default="Last 30 days", max_length=100)


class TextInputRequest(BaseModel):
    title: str = Field(default="Multimodal OSINT investigation", min_length=3, max_length=200)
    target: str = Field(default="Analyst-provided input", min_length=2, max_length=300)
    objective: str = Field(default="Extract observable information and identify evidence gaps.", min_length=3, max_length=2_000)
    text: str = Field(min_length=1, max_length=100_000)


class UrlInputRequest(BaseModel):
    title: str = Field(default="URL investigation", min_length=3, max_length=200)
    target: str = Field(default="Public URL", min_length=2, max_length=300)
    objective: str = Field(default="Extract observable information and plan permitted public-source collection.", min_length=3, max_length=2_000)
    url: str = Field(min_length=8, max_length=4_096)


class Investigation(InvestigationCreate):
    id: str
    status: InvestigationStatus = InvestigationStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)


class CollectionPlan(BaseModel):
    target_entities: list[str]
    topics: list[str]
    locations: list[str] = Field(default_factory=list)
    time_range: dict[str, str]
    required_sources: list[SourceType]
    research_questions: list[str]


class NormalizedItem(BaseModel):
    """The only collector output accepted by the evidence layer."""

    source_type: SourceType
    title: str = Field(min_length=1)
    url: str
    text: str = Field(min_length=1)
    publisher: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str = "en"
    raw: bytes | None = Field(default=None, exclude=True)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Provenance(BaseModel):
    url: str
    source_type: SourceType
    collected_at: datetime = Field(default_factory=utc_now)
    published_at: datetime | None = None
    collector: str
    content_hash: str
    raw_path: str | None = None


class Evidence(BaseModel):
    evidence_id: str
    source_id: str
    document_id: str
    type: str = "text"
    content: str
    location: dict[str, int | str | None] = Field(default_factory=dict)
    provenance: Provenance
    relationships: dict[str, list[str]] = Field(
        default_factory=lambda: {"supports_claims": [], "contradicts_claims": []}
    )


class Entity(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    evidence_ids: list[str]


class Claim(BaseModel):
    claim_id: str
    text: str
    evidence_ids: list[str]
    status: str = "unresolved"
    model_assessed_confidence: float | None = None


class Verification(BaseModel):
    claim_id: str
    status: str
    model_assessed_confidence: float
    supporting_evidence: list[str]
    contradicting_evidence: list[str] = Field(default_factory=list)


class AgentActivity(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    agent: str
    message: str


class Report(BaseModel):
    investigation_id: str
    executive_summary: str
    key_findings: list[str]
    conflicts: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class MediaArtifact(BaseModel):
    artifact_id: str
    investigation_id: str
    input_kind: InputKind
    filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    perceptual_hash: str | None = None
    dimensions: tuple[int, int] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    extracted_text: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    search_hypotheses: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    original_path: str
    created_at: datetime = Field(default_factory=utc_now)
