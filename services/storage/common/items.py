from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from scrapy import Field as ScrapyField
from scrapy import Item


class NewsItem(Item):
    """Canonical Scrapy output for news, RSS, and public social records."""

    source_name = ScrapyField()
    source_type = ScrapyField()
    url = ScrapyField()
    title = ScrapyField()
    text = ScrapyField()
    author = ScrapyField()
    published_at = ScrapyField()
    country_tags = ScrapyField()
    topic_tags = ScrapyField()
    metadata = ScrapyField()


class BlogItem(NewsItem):
    """Blog output uses the same stable envelope as news output."""


class ImageItem(Item):
    """Canonical Scrapy output for image observations."""

    source_name = ScrapyField()
    source_type = ScrapyField()
    page_url = ScrapyField()
    image_url = ScrapyField()
    image_urls = ScrapyField()
    images = ScrapyField()
    title = ScrapyField()
    alt = ScrapyField()
    caption = ScrapyField()
    metadata = ScrapyField()

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
    media: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
