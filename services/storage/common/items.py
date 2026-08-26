from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceInfo(BaseModel):
    url: str
    domain: str
    type: str

class ContentInfo(BaseModel):
    title: str | None = None
    text: str | None = None
    language: str | None = None

class Metadata(BaseModel):
    author: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)

class UnifiedDocument(BaseModel):
    document_id: str
    source: SourceInfo
    content: ContentInfo
    metadata: Metadata
    media: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
