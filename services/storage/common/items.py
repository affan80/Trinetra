from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SourceInfo(BaseModel):
    url: str
    domain: str
    type: str

class ContentInfo(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    language: Optional[str] = None

class Metadata(BaseModel):
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)

class UnifiedDocument(BaseModel):
    document_id: str
    source: SourceInfo
    content: ContentInfo
    metadata: Metadata
    media: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    locations: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []
    relationships: List[Dict[str, Any]] = []
