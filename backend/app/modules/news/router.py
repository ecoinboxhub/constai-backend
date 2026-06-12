from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.core import NewsArticle
from app.modules.news.schemas import (
    NewsArticleCreate,
    NewsArticleUpdate,
    NewsArticleResponse,
    NewsArticleListResponse,
)
from app.core.security import decode_token

router = APIRouter()


def _article_to_response(a: NewsArticle) -> NewsArticleResponse:
    return NewsArticleResponse(
        id=a.id,
        title=a.title,
        slug=a.slug,
        excerpt=a.excerpt,
        content=a.content,
        source=a.source,
        source_url=a.source_url,
        cover_image=a.cover_image,
        category=a.category,
        published=a.published,
        published_at=a.published_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.get("/articles", response_model=NewsArticleListResponse)
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = select(NewsArticle).where(NewsArticle.published == True)
    if category:
        query = query.where(NewsArticle.category == category)
    query = query.order_by(NewsArticle.published_at.desc()).offset(skip).limit(limit)
    articles = db.execute(query).scalars().all()
    total = db.execute(select(func.count(NewsArticle.id)).where(NewsArticle.published == True)).scalar() or 0
    return NewsArticleListResponse(
        articles=[_article_to_response(a) for a in articles],
        total=total,
    )


@router.get("/articles/{slug}", response_model=NewsArticleResponse)
def get_article(slug: str, db: Session = Depends(get_db)):
    article = db.execute(select(NewsArticle).where(NewsArticle.slug == slug)).scalar_one_or_none()
    if not article or not article.published:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_response(article)


@router.post("/articles", response_model=NewsArticleResponse)
def create_article(
    payload: NewsArticleCreate,
    db: Session = Depends(get_db),
    _token: dict = Depends(decode_token),
):
    existing = db.execute(select(NewsArticle).where(NewsArticle.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    article = NewsArticle(
        title=payload.title,
        slug=payload.slug,
        excerpt=payload.excerpt,
        content=payload.content,
        source=payload.source,
        source_url=payload.source_url,
        cover_image=payload.cover_image,
        category=payload.category,
        published=payload.published,
        published_at=datetime.now(UTC) if payload.published else None,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return _article_to_response(article)


@router.put("/articles/{article_id}", response_model=NewsArticleResponse)
def update_article(
    article_id: int,
    payload: NewsArticleUpdate,
    db: Session = Depends(get_db),
    _token: dict = Depends(decode_token),
):
    article = db.get(NewsArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)
    if "published" in update_data and update_data["published"] and not article.published_at:
        article.published_at = datetime.now(UTC)
    db.commit()
    db.refresh(article)
    return _article_to_response(article)


@router.delete("/articles/{article_id}")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _token: dict = Depends(decode_token),
):
    article = db.get(NewsArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"message": "Article deleted"}
