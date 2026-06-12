from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsArticleCreate(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    cover_image: Optional[str] = None
    category: Optional[str] = None
    published: bool = True


class NewsArticleUpdate(BaseModel):
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    cover_image: Optional[str] = None
    category: Optional[str] = None
    published: Optional[bool] = None


class NewsArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    source: Optional[str] = None
    source_url: Optional[str] = None
    cover_image: Optional[str] = None
    category: Optional[str] = None
    published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NewsArticleListResponse(BaseModel):
    articles: list[NewsArticleResponse]
    total: int
