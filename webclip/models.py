from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl


class BlockType(StrEnum):
    paragraph = "paragraph"
    heading = "heading"
    list = "list"
    quote = "quote"
    image = "image"
    code = "code"
    table = "table"
    html = "html"


class Person(BaseModel):
    name: str
    profile_url: HttpUrl | None = None


class Metadata(BaseModel):
    site: str
    title: str
    source_url: HttpUrl
    author: Person | None = None
    published_at: datetime | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContentBlock(BaseModel):
    type: BlockType
    text: str | None = None
    level: int | None = None
    url: HttpUrl | None = None
    caption: str | None = None


class Comment(BaseModel):
    comment_id: str
    parent_id: str | None = None
    author: Person | None = None
    created_at: datetime | None = None
    score: int | None = None
    body: list[ContentBlock] = Field(default_factory=list)


class Asset(BaseModel):
    source_url: HttpUrl
    local_path: str | None = None
    mime: str | None = None
    sha256: str | None = None


class ExtractionMetadata(BaseModel):
    adapter_name: str
    fetcher_name: str
    extracted_at: datetime


class Document(BaseModel):
    doc_id: str
    slug: str
    metadata: Metadata
    content: list[ContentBlock] = Field(default_factory=list)
    comments: list[Comment] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    extraction: ExtractionMetadata
