from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BlogArticleCreate(BaseModel):
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[str] = None
    published: bool = True


class BlogArticleUpdate(BaseModel):
    title: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[str] = None
    published: Optional[bool] = None


class BlogArticleResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str] = None
    content: str
    author: Optional[str] = None
    cover_image: Optional[str] = None
    tags: Optional[str] = None
    published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlogArticleListResponse(BaseModel):
    articles: list[BlogArticleResponse]
    total: int
