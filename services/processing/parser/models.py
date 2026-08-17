from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class BaseItemModel(BaseModel):
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NewsItemModel(BaseItemModel):
    url: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    country_tags: List[str] = Field(default_factory=list)
    topic_tags: List[str] = Field(default_factory=list)

class BlogItemModel(NewsItemModel):
    pass

class ImageItemModel(BaseItemModel):
    page_url: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)
    images: List[Dict[str, Any]] = Field(default_factory=list)
    title: Optional[str] = None
    alt: Optional[str] = None
    caption: Optional[str] = None
