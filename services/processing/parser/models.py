from typing import Any

from pydantic import BaseModel, Field


class BaseItemModel(BaseModel):
    source_name: str | None = None
    source_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class NewsItemModel(BaseItemModel):
    url: str | None = None
    title: str | None = None
    text: str | None = None
    author: str | None = None
    published_at: str | None = None
    country_tags: list[str] = Field(default_factory=list)
    topic_tags: list[str] = Field(default_factory=list)

class BlogItemModel(NewsItemModel):
    pass

class ImageItemModel(BaseItemModel):
    page_url: str | None = None
    image_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)
    title: str | None = None
    alt: str | None = None
    caption: str | None = None
